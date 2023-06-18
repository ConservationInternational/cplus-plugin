# -*- coding: utf-8 -*-

"""
 The plugin main window class file
"""

import os

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets,
    QtNetwork,
)
from qgis.PyQt.uic import loadUiType
from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
from qgis.utils import iface

from .implementation_model_widget import ImplementationModelContainerWidget

from ..resources import *

from ..utils import open_documentation

from ..definitions.defaults import PILOT_AREA_EXTENT


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_cplus_main_dockwidget.ui")
)


class QgisCplusMain(QtWidgets.QDockWidget, WidgetUi):
    """Main plugin UI"""

    def __init__(
        self,
        iface,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.iface = iface

        # Insert widget for step 2
        self.implementation_model_widget = ImplementationModelContainerWidget(
            self
        )
        self.tabWidget.insertTab(
            1,
            self.implementation_model_widget,
            self.tr("Step 2")
        )

        self.prepare_input()

    def prepare_input(self):
        """Initializes plugin input widgets"""
        self.prepare_extent_box()
        self.help_btn.clicked.connect(open_documentation)

    def prepare_extent_box(self):
        """Configure the spatial extent box with the initial settings."""
        self.extent_box.setOutputCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        map_canvas = iface.mapCanvas()
        self.extent_box.setCurrentExtent(
            map_canvas.mapSettings().destinationCrs().bounds(),
            map_canvas.mapSettings().destinationCrs(),
        )
        self.extent_box.setOutputExtentFromCurrent()
        self.extent_box.setMapCanvas(map_canvas)

        extent_list = PILOT_AREA_EXTENT["coordinates"]
        default_extent = QgsRectangle(
            extent_list[3], extent_list[2], extent_list[1], extent_list[0]
        )

        self.extent_box.setOutputExtentFromUser(
            default_extent,
            QgsCoordinateReferenceSystem("EPSG:4326"),
        )

        self.extent_box.setChecked(False)
        self.extent_box.setEnabled(False)

    def on_step_changed(self, index: int):
        """Slot raised when the current tab changes.

        :param index: Zero-based index position of new current tab.
        :type index: int
        """
        if index == 1:
            self.implementation_model_widget.load()
