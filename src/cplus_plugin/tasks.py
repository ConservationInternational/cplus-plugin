# coding=utf-8
"""
 Plugin tasks related to the scenario analysis

"""

import math
import os
import uuid

import datetime

from pathlib import Path

from qgis.PyQt import QtCore, QtGui

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsColorRampShader,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeedback,
    QgsGeometry,
    QgsPalettedRasterRenderer,
    QgsProject,
    QgsProcessing,
    QgsProcessingAlgRunnerTask,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsRasterMinMaxOrigin,
    QgsRasterShader,
    QgsRectangle,
    QgsSingleBandPseudoColorRenderer,
    QgsStyle,
    QgsTask,
    QgsVectorLayer,
    QgsWkbTypes,
)

from qgis import processing

from .conf import settings_manager, Settings

from .resources import *

from .models.helpers import clone_activity

from .models.base import ScenarioResult, SpatialExtent

from .utils import (
    align_rasters,
    clean_filename,
    open_documentation,
    tr,
    log,
    FileUtils,
)

from .definitions.defaults import (
    SCENARIO_OUTPUT_FILE_NAME,
)

from qgis.core import QgsTask


class ScenarioAnalysisTask(QgsTask):
    """Prepares and runs the scenario analysis"""

    status_message_changed = QtCore.pyqtSignal(str)
    info_message_changed = QtCore.pyqtSignal(str, int)

    custom_progress_changed = QtCore.pyqtSignal(float)

    def __init__(
        self,
        analysis_scenario_name,
        analysis_scenario_description,
        analysis_activities,
        analysis_priority_layers_groups,
        analysis_extent,
        scenario,
    ):
        super().__init__()
        self.analysis_scenario_name = analysis_scenario_name
        self.analysis_scenario_description = analysis_scenario_description

        self.analysis_activities = analysis_activities
        self.analysis_priority_layers_groups = analysis_priority_layers_groups
        self.analysis_extent = analysis_extent
        self.analysis_extent_string = None

        self.analysis_weighted_activities = []
        self.scenario_result = None
        self.scenario_directory = None

        self.success = True
        self.output = None
        self.error = None
        self.status_message = None

        self.info_message = None

        self.processing_cancelled = False
        self.feedback = QgsProcessingFeedback()
        self.processing_context = QgsProcessingContext()

        self.scenario = scenario

    def get_settings_value(self, name: str, default=None, setting_type=None):
        return settings_manager.get_value(name, default, setting_type)

    def get_scenario_directory(self):
        base_dir = self.get_settings_value(Settings.BASE_DIR)
        return os.path.join(
            f"{base_dir}",
            "scenario_" f'{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}',
        )

    def get_priority_layer(self, identifier):
        return settings_manager.get_priority_layer(identifier)

    def get_activity(self, activity_uuid):
        return settings_manager.get_activity(activity_uuid)

    def get_priority_layers(self):
        return settings_manager.get_priority_layers()

    def cancel_task(self, exception=None):
        self.cancel()

    def log_message(
        self,
        message: str,
        name: str = "qgis_cplus",
        info: bool = True,
        notify: bool = True,
    ):
        log(message, name=name, info=info, notify=notify)

    def run(self):
        """Runs the main scenario analysis task operations"""

        self.scenario_directory = self.get_scenario_directory()

        FileUtils.create_new_dir(self.scenario_directory)

        selected_pathway = None
        pathway_found = False

        for activity in self.analysis_activities:
            if pathway_found:
                break
            for pathway in activity.pathways:
                if pathway is not None:
                    pathway_found = True
                    selected_pathway = pathway
                    break

        target_layer = QgsRasterLayer(selected_pathway.path, selected_pathway.name)

        dest_crs = (
            target_layer.crs()
            if selected_pathway and selected_pathway.path
            else QgsCoordinateReferenceSystem("EPSG:4326")
        )

        processing_extent = QgsRectangle(
            float(self.analysis_extent.bbox[0]),
            float(self.analysis_extent.bbox[2]),
            float(self.analysis_extent.bbox[1]),
            float(self.analysis_extent.bbox[3]),
        )

        snapped_extent = self.align_extent(target_layer, processing_extent)

        extent_string = (
            f"{snapped_extent.xMinimum()},{snapped_extent.xMaximum()},"
            f"{snapped_extent.yMinimum()},{snapped_extent.yMaximum()}"
            f" [{dest_crs.authid()}]"
        )

        self.log_message(
            "Original area of interest extent: "
            f"{processing_extent.asWktPolygon()} \n"
        )
        self.log_message(
            "Snapped area of interest extent " f"{snapped_extent.asWktPolygon()} \n"
        )
        # Run pathways layers snapping using a specified reference layer

        snapping_enabled = self.get_settings_value(
            Settings.SNAPPING_ENABLED, default=False, setting_type=bool
        )
        reference_layer = self.get_settings_value(Settings.SNAP_LAYER, default="")
        reference_layer_path = Path(reference_layer)
        if (
            snapping_enabled
            and os.path.exists(reference_layer)
            and reference_layer_path.is_file()
        ):
            self.snap_analysis_data(
                self.analysis_activities,
                self.analysis_priority_layers_groups,
                extent_string,
            )

        # Preparing all the pathways by adding them together with
        # their carbon layers before creating
        # their respective activities.

        save_output = settings_manager.get_value(
            Settings.NCS_WITH_CARBON, default=True, setting_type=bool
        )

        self.run_pathways_analysis(
            self.analysis_activities,
            self.analysis_priority_layers_groups,
            extent_string,
            temporary_output=not save_output,
        )

        # Normalizing all the activities pathways using the carbon coefficient and
        # the pathway suitability index

        self.run_pathways_normalization(
            self.analysis_activities,
            self.analysis_priority_layers_groups,
            extent_string,
        )

        # Creating activities from the normalized pathways

        save_output = settings_manager.get_value(
            Settings.LANDUSE_PROJECT, default=True, setting_type=bool
        )

        self.run_activities_analysis(
            self.analysis_activities,
            self.analysis_priority_layers_groups,
            extent_string,
            temporary_output=not save_output,
        )

        # Run masking of the activities layers

        masking_layers_paths = settings_manager.get_value(
            Settings.MASK_LAYERS_PATHS, default=None
        )
        masking_layers = masking_layers_paths.split(",") if masking_layers_paths else []

        masking_layers.remove("") if "" in masking_layers else None

        if masking_layers:
            self.run_activities_masking(
                self.analysis_activities,
                masking_layers,
                extent_string,
            )

        # Run sieve function on the created models if user has enabled it

        sieve_enabled = self.get_settings_value(Settings.SIEVE_ENABLED, default=False)

        if sieve_enabled:
            self.run_activities_sieve(
                self.analysis_activities,
                self.analysis_priority_layers_groups,
                extent_string,
            )

        # After creating activities, we normalize them using the same coefficients
        # used in normalizing their respective pathways.

        save_output = settings_manager.get_value(
            Settings.LANDUSE_NORMALIZED, default=True, setting_type=bool
        )

        self.run_activities_normalization(
            self.analysis_activities,
            self.analysis_priority_layers_groups,
            extent_string,
            temporary_output=not save_output,
        )

        # Weighting the activities with their corresponding priority weighting layers
        save_output = settings_manager.get_value(
            Settings.LANDUSE_WEIGHTED, default=True, setting_type=bool
        )
        weighted_activities, result = self.run_activities_weighting(
            self.analysis_activities,
            self.analysis_priority_layers_groups,
            extent_string,
            temporary_output=not save_output,
        )

        self.analysis_weighted_activities = weighted_activities
        self.scenario.weighted_activities = weighted_activities

        # Post weighting analysis
        self.run_activities_cleaning(
            weighted_activities, extent_string, temporary_output=not save_output
        )

        # The highest position tool analysis
        save_output = settings_manager.get_value(
            Settings.HIGHEST_POSITION, default=True, setting_type=bool
        )
        self.run_highest_position_analysis(temporary_output=not save_output)

        return True

    def finished(self, result: bool):
        """Calls the handler responsible for doing post analysis workflow.

        :param result: Whether the run() operation finished successfully
        :type result: bool
        """
        if result:
            self.log_message("Finished from the main task \n")
        else:
            self.log_message(f"Error from task scenario task {self.error}")

    def set_status_message(self, message):
        self.status_message = message
        self.status_message_changed.emit(self.status_message)

    def set_info_message(self, message, level=Qgis.Info):
        self.info_message = message
        self.info_message_changed.emit(self.info_message, level)

    def set_custom_progress(self, value):
        self.custom_progress = value
        self.custom_progress_changed.emit(self.custom_progress)

    def update_progress(self, value):
        """Sets the value of the task progress

        :param value: Value to be set on the progress bar
        :type value: float
        """
        if not self.processing_cancelled:
            self.set_custom_progress(value)
        else:
            self.feedback = QgsProcessingFeedback()
            self.processing_context = QgsProcessingContext()

    def align_extent(self, raster_layer, target_extent):
        """Snaps the passed extent to the activities pathway layer pixel bounds

        :param raster_layer: The target layer that the passed extent will be
        aligned with
        :type raster_layer: QgsRasterLayer

        :param target_extent: Spatial extent that will be used a target extent when
        doing alignment.
        :type target_extent: QgsRectangle
        """

        try:
            raster_extent = raster_layer.extent()

            x_res = raster_layer.rasterUnitsPerPixelX()
            y_res = raster_layer.rasterUnitsPerPixelY()

            left = raster_extent.xMinimum() + x_res * math.floor(
                (target_extent.xMinimum() - raster_extent.xMinimum()) / x_res
            )
            right = raster_extent.xMinimum() + x_res * math.ceil(
                (target_extent.xMaximum() - raster_extent.xMinimum()) / x_res
            )
            bottom = raster_extent.yMinimum() + y_res * math.floor(
                (target_extent.yMinimum() - raster_extent.yMinimum()) / y_res
            )
            top = raster_extent.yMaximum() - y_res * math.floor(
                (raster_extent.yMaximum() - target_extent.yMaximum()) / y_res
            )

            return QgsRectangle(left, bottom, right, top)

        except Exception as e:
            self.log_message(
                tr(
                    f"Problem snapping area of "
                    f"interest extent, using the original extent,"
                    f"{str(e)}"
                )
            )

        return target_extent

    def replace_nodata(self, layer_path, output_path, nodata_value):
        """Adds nodata value info into the layer available
        in the passed layer_path and save the layer in the passed output_path
        path.

        The addition will replace any current nodata value available in
        the input layer.

        :param layer_path: Input layer path
        :type layer_path: str

        :param output_path: Output layer path
        :type output_path: str

        :param nodata_value: Nodata value to be used
        :type output_path: int

        :returns: If the process was successful
        :rtype: bool

        """
        self.feedback = QgsProcessingFeedback()
        self.feedback.progressChanged.connect(self.update_progress)

        alg_params = {
            "COPY_SUBDATASETS": False,
            "DATA_TYPE": 6,  # Float32
            "EXTRA": "",
            "INPUT": layer_path,
            "NODATA": None,
            "OPTIONS": "",
            "TARGET_CRS": None,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        translate_output = processing.run(
            "gdal:translate",
            alg_params,
            context=self.processing_context,
            feedback=self.feedback,
            is_child_algorithm=True,
        )

        alg_params = {
            "DATA_TYPE": 0,  # Use Input Layer Data Type
            "EXTRA": "",
            "INPUT": translate_output["OUTPUT"],
            "MULTITHREADING": False,
            "NODATA": -9999,
            "OPTIONS": "",
            "RESAMPLING": 0,  # Nearest Neighbour
            "SOURCE_CRS": None,
            "TARGET_CRS": None,
            "TARGET_EXTENT": None,
            "TARGET_EXTENT_CRS": None,
            "TARGET_RESOLUTION": None,
            "OUTPUT": output_path,
        }
        outputs = processing.run(
            "gdal:warpreproject",
            alg_params,
            context=self.processing_context,
            feedback=self.feedback,
            is_child_algorithm=True,
        )

        return outputs is not None

    def run_pathways_analysis(
        self, activities, priority_layers_groups, extent, temporary_output=False
    ):
        """Runs the required activity pathways analysis on the passed
         activities. The analysis involves adding the pathways
         carbon layers into the pathway layer.

         If the pathway layer has more than one carbon layer, the resulting
         weighted pathway will contain the sum of the pathway layer values
         with the average of the pathway carbon layers values.

        :param activities: List of the selected activities
        :type activities: typing.List[Activity]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: The selected extent from user
        :type extent: SpatialExtent

        :param temporary_output: Whether to save the processing outputs as temporary
        files
        :type temporary_output: bool
        """
        if self.processing_cancelled:
            return False

        self.set_status_message(tr("Adding activity pathways with carbon layers"))

        pathways = []
        activities_paths = []

        try:
            for activity in activities:
                if not activity.pathways and (
                    activity.path is None or activity.path is ""
                ):
                    self.set_info_message(
                        tr(
                            f"No defined activity pathways or an"
                            f" activity layer for the activity {activity.name}"
                        ),
                        level=Qgis.Critical,
                    )
                    self.log_message(
                        f"No defined activity pathways or a "
                        f"activity layer for the activity {activity.name}"
                    )
                    return False

                for pathway in activity.pathways:
                    if not (pathway in pathways):
                        pathways.append(pathway)

                if activity.path is not None and activity.path is not "":
                    activities_paths.append(activity.path)

            if not pathways and len(activities_paths) > 0:
                self.run_pathways_normalization(
                    activities, priority_layers_groups, extent
                )
                return

            suitability_index = float(
                self.get_settings_value(Settings.PATHWAY_SUITABILITY_INDEX, default=0)
            )

            carbon_coefficient = float(
                self.get_settings_value(Settings.CARBON_COEFFICIENT, default=0.0)
            )

            for pathway in pathways:
                basenames = []
                layers = []
                path_basename = Path(pathway.path).stem
                layers.append(pathway.path)

                file_name = clean_filename(pathway.name.replace(" ", "_"))

                if suitability_index > 0:
                    basenames.append(f'{suitability_index} * "{path_basename}@1"')
                else:
                    basenames.append(f'"{path_basename}@1"')

                carbon_names = []

                if len(pathway.carbon_paths) <= 0:
                    continue

                new_carbon_directory = os.path.join(
                    self.scenario_directory, "pathways_carbon_layers"
                )

                FileUtils.create_new_dir(new_carbon_directory)

                output_file = os.path.join(
                    new_carbon_directory, f"{file_name}_{str(uuid.uuid4())[:4]}.tif"
                )

                for carbon_path in pathway.carbon_paths:
                    carbon_full_path = Path(carbon_path)
                    if not carbon_full_path.exists():
                        continue
                    layers.append(carbon_path)
                    carbon_names.append(f'"{carbon_full_path.stem}@1"')

                if len(carbon_names) == 1 and carbon_coefficient > 0:
                    basenames.append(f"{carbon_coefficient} * ({carbon_names[0]})")

                # Setting up calculation to use carbon layers average when
                # a pathway has more than one carbon layer.
                if len(carbon_names) > 1 and carbon_coefficient > 0:
                    basenames.append(
                        f"{carbon_coefficient} * ("
                        f'({" + ".join(carbon_names)}) / '
                        f"{len(pathway.carbon_paths)})"
                    )
                expression = " + ".join(basenames)

                if carbon_coefficient <= 0 and suitability_index <= 0:
                    self.run_pathways_normalization(
                        activities, priority_layers_groups, extent
                    )
                    return

                output = (
                    QgsProcessing.TEMPORARY_OUTPUT if temporary_output else output_file
                )

                # Actual processing calculation
                alg_params = {
                    "CELLSIZE": 0,
                    "CRS": None,
                    "EXPRESSION": expression,
                    "EXTENT": extent,
                    "LAYERS": layers,
                    "OUTPUT": output,
                }

                self.log_message(
                    f"Used parameters for combining pathways"
                    f" and carbon layers generation: {alg_params} \n"
                )

                self.feedback = QgsProcessingFeedback()

                self.feedback.progressChanged.connect(self.update_progress)

                if self.processing_cancelled:
                    return False

                results = processing.run(
                    "qgis:rastercalculator",
                    alg_params,
                    context=self.processing_context,
                    feedback=self.feedback,
                )

                pathway.path = results["OUTPUT"]
        except Exception as e:
            self.log_message(f"Problem running pathway analysis,  {e}")
            self.error = e
            self.cancel()

        return True

    def snap_analysis_data(self, activities, priority_layers_groups, extent):
        """Snaps the passed activities pathways, carbon layers and priority layers
         to align with the reference layer set on the settings
        manager.

        :param activities: List of the selected activities
        :type activities: typing.List[Activity]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: The selected extent from user
        :type extent: list
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.set_status_message(
            tr(
                "Snapping the selected activity pathways, "
                "carbon layers and priority layers"
            )
        )

        pathways = []

        try:
            for activity in activities:
                if not activity.pathways and (
                    activity.path is None or activity.path is ""
                ):
                    self.set_info_message(
                        tr(
                            f"No defined activity pathways or a"
                            f" activity layer for the activity {activity.name}"
                        ),
                        level=Qgis.Critical,
                    )
                    self.log_message(
                        f"No defined activity pathways or a "
                        f"activity layer for the activity {activity.name}"
                    )
                    return False

                for pathway in activity.pathways:
                    if not (pathway in pathways):
                        pathways.append(pathway)

            reference_layer_path = self.get_settings_value(Settings.SNAP_LAYER)
            rescale_values = self.get_settings_value(
                Settings.RESCALE_VALUES, default=False, setting_type=bool
            )

            resampling_method = self.get_settings_value(
                Settings.RESAMPLING_METHOD, default=0
            )

            if pathways is not None and len(pathways) > 0:
                snapped_pathways_directory = os.path.join(
                    self.scenario_directory, "pathways"
                )

                FileUtils.create_new_dir(snapped_pathways_directory)

                for pathway in pathways:
                    pathway_layer = QgsRasterLayer(pathway.path, pathway.name)
                    nodata_value = pathway_layer.dataProvider().sourceNoDataValue(1)

                    if self.processing_cancelled:
                        return False

                    # carbon layer snapping

                    self.log_message(f"Snapping carbon layers from {pathway.name} pathway")

                    if (
                        pathway.carbon_paths is not None
                        and len(pathway.carbon_paths) > 0
                    ):
                        snapped_carbon_directory = os.path.join(
                            self.scenario_directory, "carbon_layers"
                        )

                        FileUtils.create_new_dir(snapped_carbon_directory)

                        snapped_carbon_paths = []

                        for carbon_path in pathway.carbon_paths:
                            carbon_layer = QgsRasterLayer(
                                carbon_path, f"{str(uuid.uuid4())[:4]}"
                            )
                            nodata_value_carbon = (
                                carbon_layer.dataProvider().sourceNoDataValue(1)
                            )

                            carbon_output_path = self.snap_layer(
                                carbon_path,
                                reference_layer_path,
                                extent,
                                snapped_carbon_directory,
                                rescale_values,
                                resampling_method,
                                nodata_value_carbon,
                            )

                            if carbon_output_path:
                                snapped_carbon_paths.append(carbon_output_path)
                            else:
                                snapped_carbon_paths.append(carbon_path)

                        pathway.carbon_paths = snapped_carbon_paths

                    self.log_message(f"Snapping {pathway.name} pathway layer \n")

                    # Pathway snapping

                    output_path = self.snap_layer(
                        pathway.path,
                        reference_layer_path,
                        extent,
                        snapped_pathways_directory,
                        rescale_values,
                        resampling_method,
                        nodata_value,
                    )
                    if output_path:
                        pathway.path = output_path

            for activity in activities:
                self.log_message(
                    f"Snapping {len(activity.priority_layers)} "
                    f"priority weighting layers from activity {activity.name} with layers\n"
                )

                if (
                    activity.priority_layers is not None
                    and len(activity.priority_layers) > 0
                ):
                    snapped_priority_directory = os.path.join(
                        self.scenario_directory, "priority_layers"
                    )

                    FileUtils.create_new_dir(snapped_priority_directory)

                    priority_layers = []
                    for priority_layer in activity.priority_layers:
                        if priority_layer is None:
                            continue

                        priority_layer_settings = settings_manager.get_priority_layer(
                            priority_layer.get("uuid")
                        )
                        if priority_layer_settings is None:
                            continue

                        priority_layer_path = priority_layer_settings.get("path")

                        if not Path(priority_layer_path).exists():
                            priority_layers.append(priority_layer)
                            continue

                        layer = QgsRasterLayer(
                            priority_layer_path, f"{str(uuid.uuid4())[:4]}"
                        )
                        nodata_value_priority = layer.dataProvider().sourceNoDataValue(
                            1
                        )

                        priority_output_path = self.snap_layer(
                            priority_layer_path,
                            reference_layer_path,
                            extent,
                            snapped_priority_directory,
                            rescale_values,
                            resampling_method,
                            nodata_value_priority,
                        )

                        if priority_output_path:
                            priority_layer["path"] = priority_output_path

                        priority_layers.append(priority_layer)

                    activity.priority_layers = priority_layers

        except Exception as e:
            self.log_message(f"Problem snapping layers, {e} \n")
            self.error = e
            self.cancel_task()
            return False

        return True

    def snap_layer(
        self,
        input_path,
        reference_path,
        extent,
        directory,
        rescale_values,
        resampling_method,
        nodata_value,
    ):
        """Snaps the passed input layer using the reference layer and updates
        the snap output no data value to be the same as the original input layer
        no data value.

        :param input_path: Input layer source
        :type input_path: str

        :param reference_path: Reference layer source
        :type reference_path: str

        :param extent: Clip extent
        :type extent: list

        :param directory: Absolute path of the output directory for the snapped
        layers
        :type directory: str

        :param rescale_values: Whether to rescale pixel values
        :type rescale_values: bool

        :param resample_method: Method to use when resampling
        :type resample_method: QgsAlignRaster.ResampleAlg

        :param nodata_value: Original no data value of the input layer
        :type nodata_value: float

        """

        input_result_path, reference_result_path = align_rasters(
            input_path,
            reference_path,
            extent,
            directory,
            rescale_values,
            resampling_method,
        )

        if input_result_path is not None:
            result_path = Path(input_result_path)

            directory = result_path.parent
            name = result_path.stem

            output_path = os.path.join(directory, f"{name}_final.tif")

            self.replace_nodata(input_result_path, output_path, nodata_value)

        return output_path

    def run_pathways_normalization(
        self, activities, priority_layers_groups, extent, temporary_output=False
    ):
        """Runs the normalization on the activities pathways layers,
        adjusting band values measured on different scale, the resulting scale
        is computed using the below formula
        Normalized_Pathway = (Carbon coefficient + Suitability index) * (
                            (activity layer value) - (activity band minimum value)) /
                            (activity band maximum value - activity band minimum value))

        If the carbon coefficient and suitability index are both zero then
        the computation won't take them into account in the normalization
        calculation.

        :param activities: List of the analyzed activities
        :type activities: typing.List[Activity]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: selected extent from user
        :type extent: str

        :param temporary_output: Whether to save the processing outputs as temporary
        files
        :type temporary_output: bool
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.set_status_message(tr("Normalization of pathways"))

        pathways = []
        activities_paths = []

        try:
            for activity in activities:
                if not activity.pathways and (
                    activity.path is None or activity.path is ""
                ):
                    self.set_info_message(
                        tr(
                            f"No defined activity pathways or an"
                            f" activity layer for the activity {activity.name}"
                        ),
                        level=Qgis.Critical,
                    )
                    self.log_message(
                        f"No defined activity pathways or an "
                        f"activity layer for the activity {activity.name}"
                    )

                    return False

                for pathway in activity.pathways:
                    if not (pathway in pathways):
                        pathways.append(pathway)

                if activity.path is not None and activity.path is not "":
                    activities_paths.append(activity.path)

            if not pathways and len(activities_paths) > 0:
                self.run_activities_analysis(activities, priority_layers_groups, extent)

                return

            carbon_coefficient = float(
                self.get_settings_value(Settings.CARBON_COEFFICIENT, default=0.0)
            )

            suitability_index = float(
                self.get_settings_value(Settings.PATHWAY_SUITABILITY_INDEX, default=0)
            )

            normalization_index = carbon_coefficient + suitability_index

            for pathway in pathways:
                layers = []
                normalized_pathways_directory = os.path.join(
                    self.scenario_directory, "normalized_pathways"
                )
                FileUtils.create_new_dir(normalized_pathways_directory)
                file_name = clean_filename(pathway.name.replace(" ", "_"))

                output_file = os.path.join(
                    normalized_pathways_directory,
                    f"{file_name}_{str(uuid.uuid4())[:4]}.tif",
                )

                pathway_layer = QgsRasterLayer(pathway.path, pathway.name)
                provider = pathway_layer.dataProvider()
                band_statistics = provider.bandStatistics(1)

                min_value = band_statistics.minimumValue
                max_value = band_statistics.maximumValue

                layer_name = Path(pathway.path).stem

                layers.append(pathway.path)

                self.log_message(
                    f"Found minimum {min_value} and "
                    f"maximum {max_value} for pathway "
                    f" \n"
                )

                if max_value < min_value:
                    raise Exception(
                        tr(
                            f"Pathway contains "
                            f"invalid minimum and maxmum band values"
                        )
                    )

                if normalization_index > 0:
                    expression = (
                        f" {normalization_index} * "
                        f'("{layer_name}@1" - {min_value}) /'
                        f" ({max_value} - {min_value})"
                    )
                else:
                    expression = (
                        f'("{layer_name}@1" - {min_value}) /'
                        f" ({max_value} - {min_value})"
                    )

                output = (
                    QgsProcessing.TEMPORARY_OUTPUT if temporary_output else output_file
                )

                # Actual processing calculation
                alg_params = {
                    "CELLSIZE": 0,
                    "CRS": None,
                    "EXPRESSION": expression,
                    "EXTENT": extent,
                    "LAYERS": layers,
                    "OUTPUT": output,
                }

                self.log_message(
                    f"Used parameters for normalization of the pathways: {alg_params} \n"
                )

                self.feedback = QgsProcessingFeedback()

                self.feedback.progressChanged.connect(self.update_progress)

                if self.processing_cancelled:
                    return False

                results = processing.run(
                    "qgis:rastercalculator",
                    alg_params,
                    context=self.processing_context,
                    feedback=self.feedback,
                )

                # self.replace_nodata(results["OUTPUT"], output_file, -9999)

                pathway.path = results["OUTPUT"]

        except Exception as e:
            self.log_message(f"Problem normalizing pathways layers, {e} \n")
            self.error = e
            self.cancel_task()
            return False

        return True

    def run_activities_analysis(
        self, activities, priority_layers_groups, extent, temporary_output=False
    ):
        """Runs the required activity analysis on the passed
        activities.

        :param activities: List of the selected activities
        :type activities: typing.List[Activity]

        :param priority_layers_groups: Used priority layers
        groups and their values
        :type priority_layers_groups: dict

        :param extent: selected extent from user
        :type extent: SpatialExtent

        :param temporary_output: Whether to save the processing outputs as temporary
        files
        :type temporary_output: bool
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.set_status_message(tr("Creating activity layers from pathways"))

        try:
            for activity in activities:
                activities_directory = os.path.join(
                    self.scenario_directory, "activities"
                )
                FileUtils.create_new_dir(activities_directory)
                file_name = clean_filename(activity.name.replace(" ", "_"))

                layers = []
                if not activity.pathways and (
                    activity.path is None and activity.path is ""
                ):
                    self.set_info_message(
                        tr(
                            f"No defined activity pathways or a"
                            f" activity layer for the activity {activity.name}"
                        ),
                        level=Qgis.Critical,
                    )
                    self.log_message(
                        f"No defined activity pathways or an "
                        f"activity layer for the activity {activity.name}"
                    )

                    return False

                output_file = os.path.join(
                    activities_directory, f"{file_name}_{str(uuid.uuid4())[:4]}.tif"
                )

                # Due to the activities base class
                # activity only one of the following blocks will be executed,
                # the activity either contain a path or
                # pathways

                if activity.path is not None and activity.path is not "":
                    layers = [activity.path]

                for pathway in activity.pathways:
                    layers.append(pathway.path)

                output = (
                    QgsProcessing.TEMPORARY_OUTPUT if temporary_output else output_file
                )

                # Actual processing calculation

                alg_params = {
                    "IGNORE_NODATA": True,
                    "INPUT": layers,
                    "EXTENT": extent,
                    "OUTPUT_NODATA_VALUE": -9999,
                    "REFERENCE_LAYER": layers[0] if len(layers) > 0 else None,
                    "STATISTIC": 0,  # Sum
                    "OUTPUT": output,
                }

                self.log_message(f"Used parameters for " f"activities generation: {alg_params} \n")

                feedback = QgsProcessingFeedback()

                feedback.progressChanged.connect(self.update_progress)

                if self.processing_cancelled:
                    return False

                results = processing.run(
                    "native:cellstatistics",
                    alg_params,
                    context=self.processing_context,
                    feedback=self.feedback,
                )
                activity.path = results["OUTPUT"]

        except Exception as e:
            self.log_message(f"Problem creating activity layers, {e}")
            self.error = e
            self.cancel_task()
            return False

        return True

    def run_activities_masking(
        self, activities, masking_layers, extent, temporary_output=False
    ):
        """Applies the mask layers into the passed activities

        :param activities: List of the selected activities
        :type activities: typing.List[Activity]

        :param masking_layers: Paths to the mask layers to be used
        :type masking_layers: dict

        :param extent: selected extent from user
        :type extent: str

        :param temporary_output: Whether to save the processing outputs as temporary
        files
        :type temporary_output: bool
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.set_status_message(tr("Masking activities using the saved masked layers"))

        try:
            for mask_layer_path in masking_layers:
                mask_layer = QgsVectorLayer(mask_layer_path, "mask", "ogr")

                if not mask_layer.isValid():
                    log(
                        f"Skipping activities masking "
                        f"using layer {mask_layer_path}, not a valid layer."
                    )
                    continue

                if Qgis.versionInt() < 33000:
                    layer_check = mask_layer.geometryType() == QgsWkbTypes.Polygon
                else:
                    layer_check = mask_layer.geometryType() == Qgis.GeometryType.Polygon

                if not layer_check:
                    self.log_message(
                        f"Skipping activities masking "
                        f"using layer {mask_layer_path}, not a polygon layer."
                    )
                    continue

                for activity in activities:
                    if activity.path is None or activity.path is "":
                        if not self.processing_cancelled:
                            self.set_info_message(
                                tr(
                                    f"Problem when masking activities, "
                                    f"there is no map layer for the activity {activity.name}"
                                ),
                                level=Qgis.Critical,
                            )
                            self.log_message(
                                f"Problem when masking activities, "
                                f"there is no map layer for the activity {activity.name}"
                            )
                        else:
                            # If the user cancelled the processing
                            self.set_info_message(
                                tr(f"Processing has been cancelled by the user."),
                                level=Qgis.Critical,
                            )
                            self.log_message(f"Processing has been cancelled by the user.")

                        return False

                    masked_activities_directory = os.path.join(
                        self.scenario_directory, "masked_activities"
                    )
                    FileUtils.create_new_dir(masked_activities_directory)
                    file_name = clean_filename(activity.name.replace(" ", "_"))

                    output_file = os.path.join(
                        masked_activities_directory,
                        f"{file_name}_{str(uuid.uuid4())[:4]}.tif",
                    )

                    output = (
                        QgsProcessing.TEMPORARY_OUTPUT
                        if temporary_output
                        else output_file
                    )

                    activity_layer = QgsRasterLayer(activity.path, "activity_layer")

                    # Actual processing calculation
                    alg_params = {
                        "INPUT": activity.path,
                        "MASK": mask_layer,
                        "SOURCE_CRS": activity_layer.crs(),
                        "DESTINATION_CRS": activity_layer.crs(),
                        "TARGET_EXTENT": extent,
                        "OUTPUT": output,
                        "NO_DATA": -9999,
                    }

                    self.log_message(f"Used parameters for masking the activities: {alg_params} \n")

                    feedback = QgsProcessingFeedback()

                    feedback.progressChanged.connect(self.update_progress)

                    if self.processing_cancelled:
                        return False

                    results = processing.run(
                        "gdal:cliprasterbymasklayer",
                        alg_params,
                        context=self.processing_context,
                        feedback=self.feedback,
                    )
                    activity.path = results["OUTPUT"]

        except Exception as e:
            log(f"Problem masking activities layers, {e} \n")
            self.error = e
            self.cancel()
            return False

        return True

    def run_activities_sieve(
        self, models, priority_layers_groups, extent, temporary_output=False
    ):
        """Runs the sieve functionality analysis on the passed models layers,
        removing the models layer polygons that are smaller than the provided
        threshold size (in pixels) and replaces them with the pixel value of
        the largest neighbour polygon.

        :param models: List of the analyzed implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: Selected area of interest extent
        :type extent: str

        :param temporary_output: Whether to save the processing outputs as temporary
        files
        :type temporary_output: bool
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.set_status_message(
            tr("Applying sieve function to the implementation models")
        )

        try:
            for model in models:
                if model.path is None or model.path is "":
                    if not self.processing_cancelled:
                        self.set_info_message(
                            tr(
                                f"Problem when running sieve function on models, "
                                f"there is no map layer for the model {model.name}"
                            ),
                            level=Qgis.Critical,
                        )
                        self.log_message(
                            f"Problem when running sieve function on models, "
                            f"there is no map layer for the model {model.name}"
                        )
                    else:
                        # If the user cancelled the processing
                        self.set_info_message(
                            tr(f"Processing has been cancelled by the user."),
                            level=Qgis.Critical,
                        )
                        self.log_message(f"Processing has been cancelled by the user.")

                    return False

                sieved_ims_directory = os.path.join(
                    self.scenario_directory, "sieved_ims"
                )
                FileUtils.create_new_dir(sieved_ims_directory)
                file_name = clean_filename(model.name.replace(" ", "_"))

                output_file = os.path.join(
                    sieved_ims_directory, f"{file_name}_{str(uuid.uuid4())[:4]}.tif"
                )

                threshold_value = float(
                    self.get_settings_value(Settings.SIEVE_THRESHOLD, default=10.0)
                )

                mask_layer = self.get_settings_value(
                    Settings.SIEVE_MASK_PATH, default=""
                )

                output = (
                    QgsProcessing.TEMPORARY_OUTPUT if temporary_output else output_file
                )

                # Actual processing calculation
                alg_params = {
                    "INPUT": model.path,
                    "THRESHOLD": threshold_value,
                    "MASK_LAYER": mask_layer,
                    "OUTPUT": output,
                }

                self.log_message(
                    f"Used parameters for running sieve function to the models: {alg_params} \n"
                )

                feedback = QgsProcessingFeedback()

                feedback.progressChanged.connect(self.update_progress)

                if self.processing_cancelled:
                    return False

                results = processing.run(
                    "gdal:sieve",
                    alg_params,
                    context=self.processing_context,
                    feedback=self.feedback,
                )
                model.path = results["OUTPUT"]

        except Exception as e:
            self.log_message(f"Problem running sieve function on models layers, {e} \n")
            self.error = e
            self.cancel_task()
            return False

        return True

    def run_activities_normalization(
        self, activities, priority_layers_groups, extent, temporary_output=False
    ):
        """Runs the normalization analysis on the activities' layers,
        adjusting band values measured on different scale, the resulting scale
        is computed using the below formula
        Normalized_activity = (Carbon coefficient + Suitability index) * (
                            (Activity layer value) - (Activity band minimum value)) /
                            (Activity band maximum value - Activity band minimum value))

        If the carbon coefficient and suitability index are both zero then
        the computation won't take them into account in the normalization
        calculation.

        :param activities: List of the analyzed activities
        :type activities: typing.List[Activity]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: Selected area of interest extent
        :type extent: str

        :param temporary_output: Whether to save the processing outputs as temporary
        files
        :type temporary_output: bool
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.set_status_message(tr("Normalization of the activities"))

        try:
            for activity in activities:
                if activity.path is None or activity.path is "":
                    if not self.processing_cancelled:
                        self.set_info_message(
                            tr(
                                f"Problem when running activities normalization, "
                                f"there is no map layer for the activity {activity.name}"
                            ),
                            level=Qgis.Critical,
                        )
                        self.log_message(
                            f"Problem when running activities normalization, "
                            f"there is no map layer for the activity {activity.name}"
                        )
                    else:
                        # If the user cancelled the processing
                        self.set_info_message(
                            tr(f"Processing has been cancelled by the user."),
                            level=Qgis.Critical,
                        )
                        self.log_message(f"Processing has been cancelled by the user.")

                    return False

                layers = []
                normalized_activities_directory = os.path.join(
                    self.scenario_directory, "normalized_activities"
                )
                FileUtils.create_new_dir(normalized_activities_directory)
                file_name = clean_filename(activity.name.replace(" ", "_"))

                output_file = os.path.join(
                    normalized_activities_directory,
                    f"{file_name}_{str(uuid.uuid4())[:4]}.tif",
                )

                activity_layer = QgsRasterLayer(activity.path, activity.name)
                provider = activity_layer.dataProvider()
                band_statistics = provider.bandStatistics(1)

                min_value = band_statistics.minimumValue
                max_value = band_statistics.maximumValue

                self.log_message(
                    f"Found minimum {min_value} and "
                    f"maximum {max_value} for activity {activity.name} \n"
                )

                layer_name = Path(activity.path).stem

                layers.append(activity.path)

                carbon_coefficient = float(
                    self.get_settings_value(Settings.CARBON_COEFFICIENT, default=0.0)
                )

                suitability_index = float(
                    self.get_settings_value(
                        Settings.PATHWAY_SUITABILITY_INDEX, default=0
                    )
                )

                normalization_index = carbon_coefficient + suitability_index

                if normalization_index > 0:
                    expression = (
                        f" {normalization_index} * "
                        f'("{layer_name}@1" - {min_value}) /'
                        f" ({max_value} - {min_value})"
                    )

                else:
                    expression = (
                        f'("{layer_name}@1" - {min_value}) /'
                        f" ({max_value} - {min_value})"
                    )

                output = (
                    QgsProcessing.TEMPORARY_OUTPUT if temporary_output else output_file
                )

                # Actual processing calculation
                alg_params = {
                    "CELLSIZE": 0,
                    "CRS": None,
                    "EXPRESSION": expression,
                    "EXTENT": extent,
                    "LAYERS": layers,
                    "OUTPUT": output,
                }

                self.log_message(
                    f"Used parameters for normalization of the activities: {alg_params} \n"
                )

                feedback = QgsProcessingFeedback()

                feedback.progressChanged.connect(self.update_progress)

                if self.processing_cancelled:
                    return False

                results = processing.run(
                    "qgis:rastercalculator",
                    alg_params,
                    context=self.processing_context,
                    feedback=self.feedback,
                )
                activity.path = results["OUTPUT"]

        except Exception as e:
            self.log_message(f"Problem normalizing activity layers, {e} \n")
            self.error = e
            self.cancel_task()
            return False

        return True

    def run_activities_weighting(
        self, activities, priority_layers_groups, extent, temporary_output=False
    ):
        """Runs weighting analysis on the passed activities using
        the corresponding activities weighting analysis.

        :param activities: List of the selected activities
        :type activities: typing.List[Activity]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: selected extent from user
        :type extent: str

        :param temporary_output: Whether to save the processing outputs as temporary
        files
        :type temporary_output: bool
        """

        if self.processing_cancelled:
            return [], False

        self.set_status_message(tr(f"Weighting activities"))

        weighted_activities = []

        try:
            for original_activity in activities:
                activity = clone_activity(original_activity)

                if activity.path is None or activity.path is "":
                    self.set_info_message(
                        tr(
                            f"Problem when running activities weighting, "
                            f"there is no map layer for the activity {activity.name}"
                        ),
                        level=Qgis.Critical,
                    )
                    self.log_message(
                        f"Problem when running activities normalization, "
                        f"there is no map layer for the activity {activity.name}"
                    )

                    return [], False

                basenames = []
                layers = []

                layers.append(activity.path)
                basenames.append(f'"{Path(activity.path).stem}@1"')

                if not any(priority_layers_groups):
                    self.log_message(
                        f"There are no defined priority layers in groups,"
                        f" skipping activities weighting step."
                    )
                    self.run_activities_cleaning(
                        extent, temporary_output=temporary_output
                    )
                    return

                if activity.priority_layers is None or activity.priority_layers is []:
                    self.log_message(
                        f"There are no associated "
                        f"priority weighting layers for activity {activity.name}"
                    )
                    continue

                settings_activity = self.get_activity(str(activity.uuid))

                for layer in settings_activity.priority_layers:
                    if layer is None:
                        continue

                    settings_layer = self.get_priority_layer(layer.get("uuid"))
                    if settings_layer is None:
                        continue

                    pwl = settings_layer.get("path")

                    missing_pwl_message = (
                        f"Path {pwl} for priority "
                        f"weighting layer {layer.get('name')} "
                        f"doesn't exist, skipping the layer "
                        f"from the activity {activity.name} weighting."
                    )
                    if pwl is None:
                        self.log_message(missing_pwl_message)
                        continue

                    pwl_path = Path(pwl)

                    if not pwl_path.exists():
                        log(missing_pwl_message)
                        continue

                    path_basename = pwl_path.stem

                    for priority_layer in self.get_priority_layers():
                        if priority_layer.get("name") == layer.get("name"):
                            for group in priority_layer.get("groups", []):
                                value = group.get("value")
                                coefficient = float(value)
                                if coefficient > 0:
                                    if pwl not in layers:
                                        layers.append(pwl)
                                    basenames.append(
                                        f'({coefficient}*"{path_basename}@1")'
                                    )

                if basenames is []:
                    return [], True

                weighted_activities_directory = os.path.join(
                    self.scenario_directory, "weighted_activities"
                )

                FileUtils.create_new_dir(weighted_activities_directory)

                file_name = clean_filename(activity.name.replace(" ", "_"))
                output_file = os.path.join(
                    weighted_activities_directory,
                    f"{file_name}_{str(uuid.uuid4())[:4]}.tif",
                )
                expression = " + ".join(basenames)

                output = (
                    QgsProcessing.TEMPORARY_OUTPUT if temporary_output else output_file
                )

                # Actual processing calculation
                alg_params = {
                    "CELLSIZE": 0,
                    "CRS": None,
                    "EXPRESSION": expression,
                    "EXTENT": extent,
                    "LAYERS": layers,
                    "OUTPUT": output,
                }

                self.log_message(
                    f" Used parameters for calculating weighting activities {alg_params} \n"
                )

                feedback = QgsProcessingFeedback()

                feedback.progressChanged.connect(self.update_progress)

                if self.processing_cancelled:
                    return [], False

                results = processing.run(
                    "qgis:rastercalculator",
                    alg_params,
                    context=self.processing_context,
                    feedback=self.feedback,
                )
                activity.path = results["OUTPUT"]

                weighted_activities.append(activity)

        except Exception as e:
            self.log_message(f"Problem weighting activities, {e}\n")
            self.error = e
            self.cancel_task()
            return None, False

        return weighted_activities, True

    def run_activities_cleaning(self, activities, extent=None, temporary_output=False):
        """Cleans the weighted activities replacing
        zero values with no-data as they are not statistical meaningful for the
        scenario analysis.

        :param extent: Selected extent from user
        :type extent: str
        """

        if self.processing_cancelled:
            return False

        self.set_status_message(tr("Updating weighted activity values"))

        try:
            for activity in activities:
                if activity.path is None or activity.path is "":
                    self.set_info_message(
                        tr(
                            f"Problem when running activity updates, "
                            f"there is no map layer for the activity {activity.name}"
                        ),
                        level=Qgis.Critical,
                    )
                    self.log_message(
                        f"Problem when running activity updates, "
                        f"there is no map layer for the activity {activity.name}"
                    )

                    return False

                layers = [activity.path]

                file_name = clean_filename(activity.name.replace(" ", "_"))

                output_file = os.path.join(
                    self.scenario_directory, "weighted_activities"
                )
                output_file = os.path.join(
                    output_file, f"{file_name}_{str(uuid.uuid4())[:4]}_cleaned.tif"
                )

                # Actual processing calculation
                # The aim is to convert pixels values to no data, that is why we are
                # using the sum operation with only one layer.

                output = (
                    QgsProcessing.TEMPORARY_OUTPUT if temporary_output else output_file
                )

                alg_params = {
                    "IGNORE_NODATA": True,
                    "INPUT": layers,
                    "EXTENT": extent,
                    "OUTPUT_NODATA_VALUE": 0,
                    "REFERENCE_LAYER": layers[0] if len(layers) > 0 else None,
                    "STATISTIC": 0,  # Sum
                    "OUTPUT": output,
                }

                self.log_message(
                    f"Used parameters for "
                    f"updates on the weighted activities: {alg_params} \n"
                )

                feedback = QgsProcessingFeedback()

                feedback.progressChanged.connect(self.update_progress)

                if self.processing_cancelled:
                    return False

                results = processing.run(
                    "native:cellstatistics",
                    alg_params,
                    context=self.processing_context,
                    feedback=self.feedback,
                )
                activity.path = results["OUTPUT"]

        except Exception as e:
            self.log_message(f"Problem cleaning activities, {e}")
            self.error = e
            self.cancel_task()
            return False

        return True

    def run_highest_position_analysis(self, temporary_output=False):
        """Runs the highest position analysis which is last step
        in scenario analysis. Uses the activities set by the current ongoing
        analysis.

        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return

        passed_extent_box = self.analysis_extent.bbox
        passed_extent = QgsRectangle(
            passed_extent_box[0],
            passed_extent_box[2],
            passed_extent_box[1],
            passed_extent_box[3],
        )

        self.scenario_result = ScenarioResult(
            scenario=self.scenario, scenario_directory=self.scenario_directory
        )

        try:
            layers = {}

            self.set_status_message(tr("Calculating the highest position"))

            for activity in self.analysis_weighted_activities:
                if activity.path is not None and activity.path is not "":
                    raster_layer = QgsRasterLayer(activity.path, activity.name)
                    layers[activity.name] = (
                        raster_layer if raster_layer is not None else None
                    )
                else:
                    for pathway in activity.pathways:
                        layers[activity.name] = QgsRasterLayer(pathway.path)

            source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            dest_crs = list(layers.values())[0].crs() if len(layers) > 0 else source_crs

            extent_string = (
                f"{passed_extent.xMinimum()},{passed_extent.xMaximum()},"
                f"{passed_extent.yMinimum()},{passed_extent.yMaximum()}"
                f" [{dest_crs.authid()}]"
            )

            output_file = os.path.join(
                self.scenario_directory,
                f"{SCENARIO_OUTPUT_FILE_NAME}_{str(self.scenario.uuid)[:4]}.tif",
            )

            # Preparing the input rasters for the highest position
            # analysis in a correct order

            activity_names = [
                activity.name for activity in self.analysis_weighted_activities
            ]
            all_activities = sorted(
                self.analysis_weighted_activities,
                key=lambda activity_instance: activity_instance.style_pixel_value,
            )
            for index, activity in enumerate(all_activities):
                activity.style_pixel_value = index + 1

            all_activity_names = [activity.name for activity in all_activities]
            sources = []

            for activity_name in all_activity_names:
                if activity_name in activity_names:
                    sources.append(layers[activity_name].source())

            self.log_message(f"Layers sources {[Path(source).stem for source in sources]}")

            output_file = (
                QgsProcessing.TEMPORARY_OUTPUT if temporary_output else output_file
            )

            alg_params = {
                "IGNORE_NODATA": True,
                "INPUT_RASTERS": sources,
                "EXTENT": extent_string,
                "OUTPUT_NODATA_VALUE": -9999,
                "REFERENCE_LAYER": list(layers.values())[0]
                if len(layers) >= 1
                else None,
                "OUTPUT": output_file,
            }

            self.log_message(f"Used parameters for highest position analysis {alg_params} \n")

            self.feedback = QgsProcessingFeedback()

            self.feedback.progressChanged.connect(self.update_progress)

            if self.processing_cancelled:
                return False

            self.output = processing.run(
                "native:highestpositioninrasterstack",
                alg_params,
                context=self.processing_context,
                feedback=self.feedback,
            )

        except Exception as err:
            self.log_message(
                tr(
                    "An error occurred when running task for "
                    'scenario analysis, error message "{}"'.format(str(err))
                )
            )
            self.error = err
            self.cancel_task()
            return False

        return True
