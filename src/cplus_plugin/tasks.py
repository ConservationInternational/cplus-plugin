import os
import uuid

from pathlib import Path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeedback,
    QgsGeometry,
    QgsProject,
    QgsProcessing,
    QgsProcessingAlgRunnerTask,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsRectangle,
    QgsTask,
    QgsWkbTypes,
    QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer,
    QgsRasterShader,
    QgsPalettedRasterRenderer,
    QgsStyle,
    QgsRasterMinMaxOrigin,
)

from qgis import processing

from .conf import settings_manager, Settings

from .resources import *

from .models.helpers import clone_implementation_model

from .models.base import Scenario, ScenarioResult, ScenarioState, SpatialExtent


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

    def __init__(
        self,
        analysis_scenario_name,
        analysis_scenario_description,
        analysis_implementation_models,
        analysis_priority_layers_groups,
        analysis_extent,
    ):
        super().__init__()
        self.analysis_scenario_name = analysis_scenario_name
        self.analysis_scenario_description = analysis_scenario_description

        self.analysis_implementation_models = analysis_implementation_models
        self.analysis_priority_layers_groups = analysis_priority_layers_groups
        self.analysis_extent = analysis_extent

        self.analysis_weighted_ims = []
        self.scenario_result = None
        self.success = True
        self.output = None
        self.error = None

        self.processing_cancelled = False

    def run(self):
        """Runs the main scenario analysis task operations"""

        # First we prepare all the pathways before adding them into
        # their respective models.
        self.run_pathways_analysis(
            self.analysis_implementation_models,
            self.analysis_priority_layers_groups,
            self.analysis_extent,
        )

        # Run pathways layers snapping using a specified reference layer
        self.snap_analyzed_pathways(
            self.analysis_implementation_models,
            self.analysis_priority_layers_groups,
            self.analysis_extent,
        )

        # Normalizing all the models pathways using the carbon coefficient and
        # the pathway suitability index

        self.run_pathways_normalization(
            self.analysis_implementation_models,
            self.analysis_priority_layers_groups,
            self.analysis_extent,
        )

        # Creating models from the normalized pathways

        self.run_models_analysis(
            self.analysis_implementation_models,
            self.analysis_priority_layers_groups,
            self.analysis_extent,
        )

        # After creating models, we normalize them using the same coefficients
        # used in normalizing their respective pathways.

        self.run_models_normalization(
            self.analysis_implementation_models,
            self.analysis_priority_layers_groups,
            self.analysis_extent,
        )

        # Weighting the models with their corresponding priority weighting layers
        weighted_models, result = self.run_models_weighting(
            self.analysis_implementation_models,
            self.analysis_priority_layers_groups,
            self.analysis_extent,
        )

        self.analysis_weighted_ims = weighted_models

        # Post weighting analysis
        self.run_models_cleaning(weighted_models, self.analysis_extent)

        # The highest position tool analysis

        self.run_highest_position_analysis()

        return True

    def finished(self, result: bool):
        """Calls the handler responsible for doing post analysis workflow.

        :param result: Whether the run() operation finished successfully
        :type result: bool
        """
        if result:
            pass
        else:
            log(self.error)

    def run_pathways_analysis(self, models, priority_layers_groups, extent):
        """Runs the required model pathways analysis on the passed
         implementation models. The analysis involves adding the pathways
         carbon layers into the pathway layer.

         If the pathway layer has more than one carbon layer, the resulting
         weighted pathway will contain the sum of the pathway layer values
         with the average of the pathway carbon layers values.

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: The selected extent from user
        :type extent: SpatialExtent
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.progress_dialog.analysis_finished_message = tr("Calculating carbon layers")
        self.progress_dialog.scenario_name = tr(f"models pathways")
        pathways = []
        models_paths = []

        for model in models:
            if not model.pathways and (model.path is None or model.path is ""):
                self.show_message(
                    tr(
                        f"No defined model pathways or a"
                        f" model layer for the model {model.name}"
                    ),
                    level=Qgis.Critical,
                )
                log(
                    f"No defined model pathways or a "
                    f"model layer for the model {model.name}"
                )
                return False

            for pathway in model.pathways:
                if not (pathway in pathways):
                    pathways.append(pathway)

            if model.path is not None and model.path is not "":
                models_paths.append(model.path)

        if not pathways and len(models_paths) > 0:
            self.run_pathways_normalization(models, priority_layers_groups, extent)
            return

        new_carbon_directory = f"{self.scenario_directory}/pathways_carbon_layers"

        suitability_index = float(
            settings_manager.get_value(Settings.PATHWAY_SUITABILITY_INDEX, default=0)
        )

        carbon_coefficient = float(
            settings_manager.get_value(Settings.CARBON_COEFFICIENT, default=0.0)
        )

        FileUtils.create_new_dir(new_carbon_directory)

        for pathway in pathways:
            basenames = []
            layers = []
            path_basename = Path(pathway.path).stem
            layers.append(pathway.path)

            file_name = clean_filename(pathway.name.replace(" ", "_"))

            output_file = (
                f"{new_carbon_directory}/{file_name}_{str(uuid.uuid4())[:4]}.tif"
            )

            if suitability_index > 0:
                basenames.append(f'{suitability_index} * "{path_basename}@1"')
            else:
                basenames.append(f'"{path_basename}@1"')

            carbon_names = []

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

            box = QgsRectangle(
                float(extent.bbox[0]),
                float(extent.bbox[2]),
                float(extent.bbox[1]),
                float(extent.bbox[3]),
            )

            source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            dest_crs = QgsRasterLayer(layers[0]).crs()
            transform = QgsCoordinateTransform(
                source_crs, dest_crs, QgsProject.instance()
            )
            transformed_extent = transform.transformBoundingBox(box)

            extent_string = (
                f"{transformed_extent.xMinimum()},{transformed_extent.xMaximum()},"
                f"{transformed_extent.yMinimum()},{transformed_extent.yMaximum()}"
                f" [{dest_crs.authid()}]"
            )

            if carbon_coefficient <= 0 and suitability_index <= 0:
                self.run_pathways_normalization(
                    models, priority_layers_groups, extent_string
                )
                return

            # Actual processing calculation
            alg_params = {
                "CELLSIZE": 0,
                "CRS": None,
                "EXPRESSION": expression,
                "EXTENT": extent_string,
                "LAYERS": layers,
                "OUTPUT": output_file,
            }

            log(
                f"Used parameters for combining pathways"
                f" and carbon layers generation: {alg_params} \n"
            )

            results = processing.run("qgis:rastercalculator", alg_params)

            pathway.path = results["OUTPUT"]

        return True

    def snap_analyzed_pathways(self, models, priority_layers_groups, extent):
        """Snaps the passed pathways layers to align with the reference layer set on the settings
        manager.

        :param pathways: List of all the available pathways
        :type pathways: list

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: The selected extent from user
        :type extent: list
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        pathways = []

        for model in models:
            if not model.pathways and (model.path is None or model.path is ""):
                self.show_message(
                    tr(
                        f"No defined model pathways or a"
                        f" model layer for the model {model.name}"
                    ),
                    level=Qgis.Critical,
                )
                log(
                    f"No defined model pathways or a "
                    f"model layer for the model {model.name}"
                )
                return False

            for pathway in model.pathways:
                if not (pathway in pathways):
                    pathways.append(pathway)

        reference_layer_path = settings_manager.get_value(Settings.SNAP_LAYER)
        rescale_values = settings_manager.get_value(
            Settings.RESCALE_VALUES, default=False, setting_type=bool
        )

        resampling_method = settings_manager.get_value(
            Settings.RESAMPLING_METHOD, default=0
        )

        for pathway in pathways:
            path = Path(pathway.path)
            directory = path.parent

            input_result_path, reference_result_path = align_rasters(
                pathway.path,
                reference_layer_path,
                extent,
                directory,
                rescale_values,
                resampling_method,
            )
            pathway.path = input_result_path

        return True

    def run_pathways_normalization(self, models, priority_layers_groups, extent):
        """Runs the normalization on the models pathways layers,
        adjusting band values measured on different scale, the resulting scale
        is computed using the below formula
        Normalized_Pathway = (Carbon coefficient + Suitability index) * (
                            (Model layer value) - (Model band minimum value)) /
                            (Model band maximum value - Model band minimum value))

        If the carbon coefficient and suitability index are both zero then
        the computation won't take them into account in the normalization
        calculation.

        :param models: List of the analyzed implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: selected extent from user
        :type extent: str
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.progress_dialog.analysis_finished_message = tr("Normalization")
        self.progress_dialog.scenario_name = tr("pathways")

        pathways = []
        models_paths = []

        for model in models:
            if not model.pathways and (model.path is None or model.path is ""):
                self.show_message(
                    tr(
                        f"No defined model pathways or a"
                        f" model layer for the model {model.name}"
                    ),
                    level=Qgis.Critical,
                )
                log(
                    f"No defined model pathways or a "
                    f"model layer for the model {model.name}"
                )

                return False

            for pathway in model.pathways:
                if not (pathway in pathways):
                    pathways.append(pathway)

            if model.path is not None and model.path is not "":
                models_paths.append(model.path)

        if not pathways and len(models_paths) > 0:
            self.run_models_analysis(models, priority_layers_groups, extent)

            return

        carbon_coefficient = float(
            settings_manager.get_value(Settings.CARBON_COEFFICIENT, default=0.0)
        )

        suitability_index = float(
            settings_manager.get_value(Settings.PATHWAY_SUITABILITY_INDEX, default=0)
        )

        normalization_index = carbon_coefficient + suitability_index

        for pathway in pathways:
            layers = []
            new_ims_directory = f"{self.scenario_directory}/normalized_pathways"
            FileUtils.create_new_dir(new_ims_directory)
            file_name = clean_filename(pathway.name.replace(" ", "_"))

            output_file = f"{new_ims_directory}/{file_name}_{str(uuid.uuid4())[:4]}.tif"

            pathway_layer = QgsRasterLayer(pathway.path, pathway.name)
            provider = pathway_layer.dataProvider()
            band_statistics = provider.bandStatistics(1)

            min_value = band_statistics.minimumValue
            max_value = band_statistics.maximumValue

            layer_name = Path(pathway.path).stem

            layers.append(pathway.path)

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

            # Actual processing calculation
            alg_params = {
                "CELLSIZE": 0,
                "CRS": None,
                "EXPRESSION": expression,
                "EXTENT": extent,
                "LAYERS": layers,
                "OUTPUT": output_file,
            }

            log(f"Used parameters for normalization of the pathways: {alg_params} \n")

            results = processing.run("qgis:rastercalculator", alg_params)

            pathway.path = results["OUTPUT"]

        return True

    def run_models_analysis(self, models, priority_layers_groups, extent):
        """Runs the required model analysis on the passed
        implementation models.

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers
        groups and their values
        :type priority_layers_groups: dict

        :param extent: selected extent from user
        :type extent: SpatialExtent
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.progress_dialog.analysis_finished_message = tr("Processing calculations")
        self.progress_dialog.scenario_name = tr("implementation models")

        for model in models:
            new_ims_directory = f"{self.scenario_directory}/implementation_models"
            FileUtils.create_new_dir(new_ims_directory)
            file_name = clean_filename(model.name.replace(" ", "_"))

            layers = []
            if not model.pathways and (model.path is None and model.path is ""):
                self.show_message(
                    tr(
                        f"No defined model pathways or a"
                        f" model layer for the model {model.name}"
                    ),
                    level=Qgis.Critical,
                )
                log(
                    f"No defined model pathways or a "
                    f"model layer for the model {model.name}"
                )

                return False

            output_file = f"{new_ims_directory}/{file_name}_{str(uuid.uuid4())[:4]}.tif"

            # Due to the implementation models base class
            # model only one of the following blocks will be executed,
            # the implementation model either contain a path or
            # pathways

            if model.path is not None and model.path is not "":
                layers = [model.path]

            for pathway in model.pathways:
                layers.append(pathway.path)

            # Actual processing calculation

            alg_params = {
                "IGNORE_NODATA": True,
                "INPUT": layers,
                "EXTENT": extent,
                "OUTPUT_NODATA_VALUE": -9999,
                "REFERENCE_LAYER": layers[0] if len(layers) > 0 else None,
                "STATISTIC": 0,  # Sum
                "OUTPUT": output_file,
            }

            log(
                f"Used parameters for "
                f"implementation models generation: {alg_params} \n"
            )

            results = processing.run("native:cellstatistics", alg_params)
            model.path = results["OUTPUT"]

        return True

    def run_models_normalization(self, models, priority_layers_groups, extent):
        """Runs the normalization analysis on the models layers,
        adjusting band values measured on different scale, the resulting scale
        is computed using the below formula
        Normalized_Model = (Carbon coefficient + Suitability index) * (
                            (Model layer value) - (Model band minimum value)) /
                            (Model band maximum value - Model band minimum value))

        If the carbon coefficient and suitability index are both zero then
        the computation won't take them into account in the normalization
        calculation.

        :param models: List of the analyzed implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: selected extent from user
        :type extent: str
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return False

        self.progress_dialog.analysis_finished_message = tr("Normalization")
        self.progress_dialog.scenario_name = tr("implementation models")

        for model in models:
            if model.path is None or model.path is "":
                if not self.processing_cancelled:
                    self.show_message(
                        tr(
                            f"Problem when running models normalization, "
                            f"there is no map layer for the model {model.name}"
                        ),
                        level=Qgis.Critical,
                    )
                    log(
                        f"Problem when running models normalization, "
                        f"there is no map layer for the model {model.name}"
                    )
                else:
                    # If the user cancelled the processing
                    self.show_message(
                        tr(f"Processing has been cancelled by the user."),
                        level=Qgis.Critical,
                    )
                    log(f"Processing has been cancelled by the user.")

                return False

            layers = []
            new_ims_directory = f"{self.scenario_directory}/normalized_ims"
            FileUtils.create_new_dir(new_ims_directory)
            file_name = clean_filename(model.name.replace(" ", "_"))

            output_file = f"{new_ims_directory}/{file_name}_{str(uuid.uuid4())[:4]}.tif"

            model_layer = QgsRasterLayer(model.path, model.name)
            provider = model_layer.dataProvider()
            band_statistics = provider.bandStatistics(1)

            min_value = band_statistics.minimumValue
            max_value = band_statistics.maximumValue

            layer_name = Path(model.path).stem

            layers.append(model.path)

            carbon_coefficient = float(
                settings_manager.get_value(Settings.CARBON_COEFFICIENT, default=0.0)
            )

            suitability_index = float(
                settings_manager.get_value(
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

            # Actual processing calculation
            alg_params = {
                "CELLSIZE": 0,
                "CRS": None,
                "EXPRESSION": expression,
                "EXTENT": extent,
                "LAYERS": layers,
                "OUTPUT": output_file,
            }

            log(f"Used parameters for normalization of the models: {alg_params} \n")

            results = processing.run("qgis:rastercalculator", alg_params)
            model.path = results["OUTPUT"]

        return True

    def run_models_weighting(self, models, priority_layers_groups, extent):
        """Runs weighting analysis on the passed implementation models using
        the corresponding models weighting analysis.

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: selected extent from user
        :type extent: str
        """

        self.progress_dialog.analysis_finished_message = tr(f"Weighting")

        self.progress_dialog.scenario_name = tr(f"implementation models")

        weighted_models = []

        for original_model in models:
            model = clone_implementation_model(original_model)

            if model.path is None or model.path is "":
                self.show_message(
                    tr(
                        f"Problem when running models weighting, "
                        f"there is no map layer for the model {model.name}"
                    ),
                    level=Qgis.Critical,
                )
                log(
                    f"Problem when running models normalization, "
                    f"there is no map layer for the model {model.name}"
                )

                return False

            basenames = []
            layers = []

            layers.append(model.path)
            basenames.append(f'"{Path(model.path).stem}@1"')

            if not any(priority_layers_groups):
                log(
                    f"There are no defined priority layers in groups,"
                    f" skipping models weighting step."
                )
                self.run_models_cleaning(extent)
                return

            if model.priority_layers is None or model.priority_layers is []:
                log(
                    f"There are no associated "
                    f"priority weighting layers for model {model.name}"
                )
                continue

            settings_model = settings_manager.get_implementation_model(str(model.uuid))

            for layer in settings_model.priority_layers:
                if layer is None:
                    continue

                settings_layer = settings_manager.get_priority_layer(layer.get("uuid"))
                if settings_layer is None:
                    continue

                pwl = settings_layer.get("path")

                missing_pwl_message = (
                    f"Path {pwl} for priority "
                    f"weighting layer {layer.get('name')} "
                    f"doesn't exist, skipping the layer "
                    f"from the model {model.name} weighting."
                )
                if pwl is None:
                    log(missing_pwl_message)
                    continue

                pwl_path = Path(pwl)

                if not pwl_path.exists():
                    log(missing_pwl_message)
                    continue

                path_basename = pwl_path.stem

                for priority_layer in settings_manager.get_priority_layers():
                    if priority_layer.get("name") == layer.get("name"):
                        for group in priority_layer.get("groups", []):
                            value = group.get("value")
                            coefficient = float(value)
                            if coefficient > 0:
                                if pwl not in layers:
                                    layers.append(pwl)
                                basenames.append(f'({coefficient}*"{path_basename}@1")')

            if basenames is []:
                return True

            new_ims_directory = f"{self.scenario_directory}/weighted_ims"

            FileUtils.create_new_dir(new_ims_directory)

            file_name = clean_filename(model.name.replace(" ", "_"))
            output_file = f"{new_ims_directory}/{file_name}_{str(uuid.uuid4())[:4]}.tif"
            expression = " + ".join(basenames)

            # Actual processing calculation
            alg_params = {
                "CELLSIZE": 0,
                "CRS": None,
                "EXPRESSION": expression,
                "EXTENT": extent,
                "LAYERS": layers,
                "OUTPUT": output_file,
            }

            log(f" Used parameters for calculating weighting models {alg_params} \n")

            results = processing.run("qgis:rastercalculator", alg_params)
            model.path = results["OUTPUT"]

            weighted_models.append(model)

        return weighted_models, True

    def run_models_cleaning(self, models, extent=None):
        """Cleans the weighted implementation models replacing
        zero values with no-data as they are not statistical meaningful for the
        scenario analysis.

        :param extent: Selected extent from user
        :type extent: str
        """

        self.progress_dialog.analysis_finished_message = tr(f"Updating")

        self.progress_dialog.scenario_name = tr(f"implementation models")

        for model in models:
            if model.path is None or model.path is "":
                self.show_message(
                    tr(
                        f"Problem when running models updates, "
                        f"there is no map layer for the model {model.name}"
                    ),
                    level=Qgis.Critical,
                )
                log(
                    f"Problem when running models updates, "
                    f"there is no map layer for the model {model.name}"
                )

                return False

            layers = [model.path]

            file_name = clean_filename(model.name.replace(" ", "_"))

            output_file = os.path.join(self.scenario_directory, "weighted_ims")
            output_file = os.path.join(
                output_file, f"{file_name}_{str(uuid.uuid4())[:4]}_cleaned.tif"
            )

            # Actual processing calculation
            # The aim is to convert pixels values to no data, that is why we are
            # using the sum operation with only one layer.

            alg_params = {
                "IGNORE_NODATA": True,
                "INPUT": layers,
                "EXTENT": extent,
                "OUTPUT_NODATA_VALUE": 0,
                "REFERENCE_LAYER": layers[0] if len(layers) > 0 else None,
                "STATISTIC": 0,  # Sum
                "OUTPUT": output_file,
            }

            log(
                f"Used parameters for "
                f"updates on the weighted implementation models: {alg_params} \n"
            )

            results = processing.run("native:cellstatistics", alg_params)
            model.path = results["OUTPUT"]

        return True

    def run_highest_position_analysis(self):
        """Runs the highest position analysis which is last step
        in scenario analysis. Uses the models set by the current ongoing
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

        scenario = Scenario(
            uuid=uuid.uuid4(),
            name=self.analysis_scenario_name,
            description=self.analysis_scenario_description,
            extent=self.analysis_extent,
            models=self.analysis_implementation_models,
            priority_layer_groups=self.analysis_priority_layers_groups,
        )

        self.scenario_result = ScenarioResult(
            scenario=scenario,
        )

        try:
            layers = {}

            self.progress_dialog.progress_bar.setMinimum(0)
            self.progress_dialog.progress_bar.setMaximum(100)
            self.progress_dialog.progress_bar.setValue(0)
            self.progress_dialog.analysis_finished_message = tr("Analysis finished")
            self.progress_dialog.scenario_name = tr(f"<b>{scenario.name}</b>")
            self.progress_dialog.scenario_id = str(scenario.uuid)
            self.progress_dialog.change_status_message(
                tr("Calculating the highest position")
            )

            self.position_feedback.progressChanged.connect(self.update_progress_bar)

            for model in self.analysis_weighted_ims:
                if model.path is not None and model.path is not "":
                    raster_layer = QgsRasterLayer(model.path, model.name)
                    layers[model.name] = (
                        raster_layer if raster_layer is not None else None
                    )
                else:
                    for pathway in model.pathways:
                        layers[model.name] = QgsRasterLayer(pathway.path)

            source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            dest_crs = list(layers.values())[0].crs() if len(layers) > 0 else source_crs
            transform = QgsCoordinateTransform(
                source_crs, dest_crs, QgsProject.instance()
            )
            transformed_extent = transform.transformBoundingBox(passed_extent)

            extent_string = (
                f"{transformed_extent.xMinimum()},{transformed_extent.xMaximum()},"
                f"{transformed_extent.yMinimum()},{transformed_extent.yMaximum()}"
                f" [{dest_crs.authid()}]"
            )

            output_file = (
                f"{self.scenario_directory}/"
                f"{SCENARIO_OUTPUT_FILE_NAME}_{str(scenario.uuid)[:4]}.tif"
            )

            # Preparing the input rasters for the highest position
            # analysis in a correct order

            models_names = [model.name for model in self.analysis_weighted_ims]
            all_models = sorted(
                self.analysis_weighted_ims,
                key=lambda model_instance: model_instance.style_pixel_value,
            )
            for index, model in enumerate(all_models):
                model.style_pixel_value = index + 1

            all_models_names = [model.name for model in all_models]
            sources = []

            for model_name in all_models_names:
                if model_name in models_names:
                    sources.append(layers[model_name].source())

            log(f"Layers sources {[Path(source).stem for source in sources]}")

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

            log(f"Used parameters for highest position analysis {alg_params} \n")

            self.output = processing.run(
                "native:highestpositioninrasterstack", alg_params
            )

        except Exception as err:
            self.show_message(
                tr(
                    "An error occurred when running analysis task, "
                    "check logs for more information"
                ),
                level=Qgis.Info,
            )
            log(
                tr(
                    "An error occurred when running task for "
                    'scenario analysis, error message "{}"'.format(str(err))
                )
            )

        return True
