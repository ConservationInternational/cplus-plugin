import uuid

from functools import partial

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

from ..conf import settings_manager, Settings

from ..resources import *

from ..utils import (
    align_rasters,
    clean_filename,
    open_documentation,
    tr,
    log,
    FileUtils,
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
        self.error = None

    def run(self):
        """Runs the main scenario analysis task operations"""

        # First we prepare all the pathways before adding them into
        # their respective models.
        self.run_pathways_analysis(
            self.analysis_implementation_models,
            self.analysis_priority_layers_groups,
            self.analysis_extent,
        )

        return True

    def finished(self, result: bool):
        """Calls the handler responsible for adding the
         layer into QGIS project.

        :param result: Whether the run() operation finished successfully
        :type result: bool
        """
        if result and self.layer:
            log(f"Fetched layer with URI " f"{self.layer_uri} ")
            # Due to the way QGIS is handling layers sharing between tasks and
            # the main thread, sending the layer to the main thread
            # without cloning it can lead to unpredicted crashes,
            # hence we clone the layer before storing it, so it can
            # be used in the main thread.
            self.layer = self.layer.clone()
        else:
            provider_error = (
                tr("error {}").format(self.layer.dataProvider().error())
                if self.layer and self.layer.dataProvider()
                else None
            )
            self.error = tr(
                f"Couldn't load layer " f"{self.layer_uri}," f"{provider_error}"
            )
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

        models_function = partial(
            self.run_pathways_normalization, models, priority_layers_groups, extent
        )
        main_task = QgsTask.fromFunction(
            "Main task for running pathways combination with carbon layers",
            self.main_task,
            on_finished=models_function,
        )

        main_task.taskCompleted.connect(models_function)

        previous_sub_tasks = []

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
                main_task.cancel()
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

        base_dir = settings_manager.get_value(Settings.BASE_DIR)

        FileUtils.create_new_dir(new_carbon_directory)
        pathway_count = 0

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
            analysis_done = partial(
                self.pathways_analysis_done,
                pathway_count,
                models,
                extent_string,
                priority_layers_groups,
                pathways,
                pathway,
                (pathway_count == len(pathways) - 1),
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

            alg = QgsApplication.processingRegistry().algorithmById(
                "qgis:rastercalculator"
            )

            self.task = QgsProcessingAlgRunnerTask(
                alg, alg_params, self.processing_context, self.position_feedback
            )
            self.position_feedback.progressChanged.connect(self.update_progress_bar)

            main_task.addSubTask(
                self.task, previous_sub_tasks, QgsTask.ParentDependsOnSubTask
            )
            previous_sub_tasks.append(self.task)
            self.task.executed.connect(analysis_done)

            pathway_count = pathway_count + 1

        QgsApplication.taskManager().addTask(main_task)
