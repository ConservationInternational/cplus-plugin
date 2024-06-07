# -*- coding: utf-8 -*-
"""
    Scenario dialog
"""

import os
from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from qgis.PyQt.uic import loadUiType

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsRectangle,
)

from qgis.utils import iface

from ..definitions.defaults import ICON_PATH


DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/scenario_dialog.ui")
)


class ScenarioDialog(QtWidgets.QDialog, DialogUi):
    """Dialog that provide UI for scenario details."""

    def __init__(
        self,
        scenario=None,
        scenario_result=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        self.scenario = scenario
        self.scenario_result = scenario_result

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        self.initialize_ui()

    def initialize_ui(self):
        """Populate UI inputs when loading the dialog"""

        if self.scenario is not None:
            self.scenario_name.setText(self.scenario.name)
            self.scenario_description.setText(self.scenario.description)

            self.extent_box.setOutputCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
            map_canvas = iface.mapCanvas()
            self.extent_box.setCurrentExtent(
                map_canvas.mapSettings().destinationCrs().bounds(),
                map_canvas.mapSettings().destinationCrs(),
            )
            self.extent_box.setOutputExtentFromCurrent()
            self.extent_box.setMapCanvas(map_canvas)

            extent_list = self.scenario.extent.bbox
            if extent_list:
                default_extent = QgsRectangle(
                    float(extent_list[0]),
                    float(extent_list[2]),
                    float(extent_list[1]),
                    float(extent_list[3]),
                )

                self.extent_box.setOutputExtentFromUser(
                    default_extent,
                    QgsCoordinateReferenceSystem("EPSG:4326"),
                )
