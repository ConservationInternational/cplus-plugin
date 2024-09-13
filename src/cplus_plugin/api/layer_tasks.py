# coding=utf-8
"""
 Plugin tasks related to the layer
"""

from qgis.core import QgsTask
from qgis.PyQt import QtCore

from ..conf import settings_manager
from ..utils import log
from .request import CplusApiRequest


class FetchDefaultLayerTask(QgsTask):
    """Qgs task for fetching default layer."""

    task_finished = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.request = CplusApiRequest()
        self.result = {}

    def run(self):
        """Execute the task logic.
        :return: True if task runs successfully
        :rtype: bool
        """
        try:
            self.result = self.request.fetch_default_layer_list()
            return True
        except Exception as ex:
            log(f"Error during fetch scenario history: {ex}", info=False)
            return False

    def finished(self, is_success):
        """Handler when task has been executed.
        :param is_success: True if task runs successfully.
        :type is_success: bool
        """
        if is_success:
            self.store_default_layers(self.result)
        self.task_finished.emit(is_success)

    def store_default_layers(self, result: dict):
        """Store default layers to settings manager.

        :param result: Dictionary of type and layer list
        :type result: dict
        """
        for key, layers in result.items():
            settings_manager.save_default_layers(key, layers)
