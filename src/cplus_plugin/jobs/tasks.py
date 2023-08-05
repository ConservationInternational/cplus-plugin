import os

from qgis.core import (
    QgsApplication,
    QgsTask,
    QgsProcessingAlgRunnerTask,
    QgsRasterLayer,
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingFeedback,
)
from ..utils import log, tr


class LayerCalculatorTask(QgsTask):
    """Prepares implementation model layer"""

    def __init__(self, model, extent):
        super().__init__()
        self.model = model
        self.extent = extent
        self.error = None

    def run(self):
        """Operates the main layers loading logic"""
        if not self.model.pathways:
            return False

        basenames = []
        layers = []

        for pathway in self.model.pathways:
            path_basename = os.path.basename(pathway.path)
            layers.append(QgsRasterLayer(pathway.path, path_basename))
            basenames.append(f"{path_basename}@1")
        expression = " + ".join(basenames)

        feedback = QgsProcessingFeedback()
        context = QgsProcessingContext()

        # Actual processing calculation
        alg_params = {
            "CELLSIZE": 0,
            "CRS": None,
            "EXPRESSION": expression,
            "EXTENT": self.extent,
            "LAYERS": layers,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }

        log(f"in the task running the alg {self.model.name}")

        alg = QgsApplication.processingRegistry().algorithmById("qgis:rastercalculator")

        self.task = QgsProcessingAlgRunnerTask(
            alg,
            alg_params,
            context,
            feedback,
        )

        self.task.executed.connect(self.post_analysis)
        QgsApplication.taskManager().addTask(self.task)

        return True

    def finished(self, result: bool):
        """Calls the handler responsible for adding the
         layer into QGIS project.

        :param result: Whether the run() operation finished successfully
        :type result: bool
        """
        if result and self.layer:
            log(f"Fetched layer with URI " f"{self.moder.name} ")
            # Due to the way QGIS is handling layers sharing between tasks and
            # the main thread, sending the layer to the main thread
            # without cloning it can lead to unpredicted crashes,
            # hence we clone the layer before storing it, so it can
            # be used in the main thread.
            self.model.layer = self.model.layer.clone()
        else:
            provider_error = (
                tr("error {}").format(self.model.layer.dataProvider().error())
                if self.layer and self.model.layer.dataProvider()
                else None
            )
            self.error = tr(
                f"Couldn't load layer " f"{self.model.name}," f"{provider_error}"
            )
            log(self.error)

    def post_analysis(self, success, outputs):
        if outputs["OUTPUT"]:
            self.model.layer = QgsRasterLayer(outputs["OUTPUT"])
            log(f"Fetched layer with URI " f"{self.moder.name} ")
            # Due to the way QGIS is handling layers sharing between tasks and
            # the main thread, sending the layer to the main thread
            # without cloning it can lead to unpredicted crashes,
            # hence we clone the layer before storing it, so it can
            # be used in the main thread.
            self.model.layer = self.model.layer.clone()
        else:
            provider_error = (
                tr("error {}").format(self.model.layer.dataProvider().error())
                if self.layer and self.model.layer.dataProvider()
                else None
            )
            self.error = tr(
                f"Couldn't load layer " f"{self.model.name}," f"{provider_error}"
            )
            log(self.error)
