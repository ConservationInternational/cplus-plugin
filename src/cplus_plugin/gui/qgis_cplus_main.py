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
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsRectangle,
    QgsWkbTypes,
)

from qgis.gui import (
    QgsMessageBar,
    QgsMapCanvas,
    QgsRubberBand,
)

from qgis.utils import iface

from .implementation_model_widget import ImplementationModelContainerWidget

from ..resources import *

from ..utils import open_documentation, tr, log

from ..definitions.defaults import PILOT_AREA_EXTENT, OPTIONS_TITLE

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
        self.implementation_model_widget = ImplementationModelContainerWidget(self)
        self.tab_widget.insertTab(
            1, self.implementation_model_widget, self.tr("Step 2")
        )
        self.tab_widget.currentChanged.connect(self.on_tab_step_changed)

        self.prepare_input()

    def prepare_input(self):
        """Initializes plugin input widgets"""
        self.prepare_extent_box()
        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.prepare_message_bar()
        self.help_btn.clicked.connect(open_documentation)
        self.pilot_area_btn.clicked.connect(self.zoom_pilot_area)
        self.run_scenario_btn.clicked.connect(self.run_scenario_analysis)
        self.options_btn.clicked.connect(self.open_settings)

    def prepare_message_bar(self):
        """Initializes the widget message bar settings"""
        self.message_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        self.grid_layout.addWidget(
            self.message_bar, 0, 0, 1, 1, alignment=QtCore.Qt.AlignTop
        )
        self.dock_widget_contents.layout().insertLayout(0, self.grid_layout)

    def run_scenario_analysis(self):
        extent_list = PILOT_AREA_EXTENT["coordinates"]
        default_extent = QgsRectangle(
            extent_list[3], extent_list[2], extent_list[1], extent_list[0]
        )
        passed_extent = self.extent_box.outputExtent()
        contains = default_extent == passed_extent or default_extent.contains(
            passed_extent
        )

        if not contains:
            self.show_message(
                tr(f"Selected area of interest is " f"outside the pilot area."),
                level=Qgis.Info,
            )
        else:
            self.show_message(
                tr("Selected area of interest " "is inside the pilot area."),
                level=Qgis.Info,
            )

    def show_message(self, message, level=Qgis.Warning):
        """Shows message on the main widget message bar

        :param message: Message text
        :type message: str

        :param level: Message level type
        :type level: Qgis.MessageLevel
        """
        self.message_bar.clearWidgets()
        self.message_bar.pushMessage(message, level=level)

    def zoom_pilot_area(self):
        """Zoom the current main map canvas to the pilot area extent."""
        map_canvas = iface.mapCanvas()
        extent_list = PILOT_AREA_EXTENT["coordinates"]
        default_extent = QgsRectangle(
            extent_list[3], extent_list[2], extent_list[1], extent_list[0]
        )
        zoom_extent = QgsRectangle(
            extent_list[3] - 0.5, extent_list[2], extent_list[1] + 0.5, extent_list[0]
        )

        aoi = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.PolygonGeometry)

        aoi.setFillColor(QtGui.QColor(0, 0, 0, 0))
        aoi.setStrokeColor(QtGui.QColor(88, 128, 8))
        aoi.setWidth(3)
        aoi.setLineStyle(QtCore.Qt.DashLine)

        geom = QgsGeometry.fromRect(default_extent)
        aoi.setToGeometry(geom, QgsCoordinateReferenceSystem("EPSG:4326"))

        map_canvas.setExtent(zoom_extent)

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

    def on_tab_step_changed(self, index: int):
        """Slot raised when the current tab changes.

        :param index: Zero-based index position of new current tab.
        :type index: int
        """
        if index == 1:
            self.implementation_model_widget.load()

    def open_settings(self):
        """Options the CPLUS settings in the QGIS options dialog."""
        self.iface.showOptionsDialog(currentPage=OPTIONS_TITLE)
