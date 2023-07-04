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

from .priority_group_widget import PriorityGroupWidget
from .priority_layer_group import PriorityLayerDialog
from ..resources import *

from ..utils import open_documentation, tr, log
from ..conf import settings_manager


from ..definitions.defaults import PILOT_AREA_EXTENT, PRIORITY_GROUPS, PRIORITY_LAYERS


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

        self.initialize_priority_layers()

        self.prepare_input()

    def initialize_priority_layers(self):
        """Prepares the priority weighted layers UI with the defaults"""

        selected_groups = []

        for layer in settings_manager.get_priority_layers():
            self.priority_layers_list.addItem(layer["name"])
            log(f"adding item {layer['name']}")
            if layer.get("selected"):
                selected_groups = layer["groups"]

        scroll_container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)

        for group in PRIORITY_GROUPS:
            log(f"Initializing {group['name']}")
            group_widget = PriorityGroupWidget(group)

            layer_group = None
            for selected_group in selected_groups:
                if selected_group["name"] == group["name"]:
                    layer_group = selected_group

            group_widget.set_group(layer_group)

            layout.addWidget(group_widget)
            layout.setAlignment(group_widget, QtCore.Qt.AlignTop)

        vertical_spacer = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        layout.addItem(vertical_spacer)
        scroll_container.setLayout(layout)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(scroll_container)

    def update_priority_layers(self):
        self.priority_layers_list.clear()
        for layer in settings_manager.get_priority_layers():
            self.priority_layers_list.addItem(layer["name"])

    def prepare_input(self):
        """Initializes plugin input widgets"""
        self.prepare_extent_box()
        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.prepare_message_bar()
        self.help_btn.clicked.connect(open_documentation)
        self.pilot_area_btn.clicked.connect(self.zoom_pilot_area)
        self.run_scenario_btn.clicked.connect(self.run_scenario_analysis)

        self.add_pwl_btn.clicked.connect(self.add_priority_layer)
        self.edit_pwl_btn.clicked.connect(self.edit_priority_layer)
        self.remove_pwl_btn.clicked.connect(self.remove_priority_layer)

    def add_priority_layer(self):
        """Adds a new priority layer into the plugin, then updates
        the priority list to show the new added priority layer.
        """
        layer_dialog = PriorityLayerDialog()
        layer_dialog.exec_()
        self.update_priority_layers()

    def edit_priority_layer(self):
        """Edits the passed layer and updates the layer box list."""
        current_text = self.priority_layers_list.currentText()
        if current_text == "":
            return
        layer = settings_manager.find_layer_by_name(current_text)
        layer_dialog = PriorityLayerDialog(layer)
        layer_dialog.exec_()

        self.update_priority_layers()

    def remove_priority_layer(self):
        """Removes the current active priority layer."""
        current_text = self.priority_layers_list.currentText()
        if current_text == "":
            return
        layer = settings_manager.find_layer_by_name(current_text)
        reply = QtWidgets.QMessageBox.warning(
            self,
            tr("QGIS CPLUS PLUGIN"),
            tr('Remove the priority layer "{}"?').format(current_text),
            QtWidgets.QMessageBox.Yes,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            settings_manager.delete_priority_layer(layer.get("uuid"))
            self.update_priority_layers()

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
