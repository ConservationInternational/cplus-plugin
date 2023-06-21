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

<<<<<<< HEAD
from .priority_group_widget import PriorityGroupWidget
from .priority_layer_group import PriorityLayerDialog
=======
from .implementation_model_widget import ImplementationModelContainerWidget

>>>>>>> 28399ff (Initial implementation model UI framework.)
from ..resources import *

from ..utils import open_documentation, tr, log
from ..conf import settings_manager

from ..definitions.defaults import PILOT_AREA_EXTENT, PRIORITY_GROUPS, PRIORITY_LAYERS, OPTIONS_TITLE

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
        self.priority_groups_widgets = {}

        self.initialize_priority_layers()

        # Insert widget for step 2
        self.implementation_model_widget = ImplementationModelContainerWidget(self)
        self.tabWidget.insertTab(1, self.implementation_model_widget, self.tr("Step 2"))

        self.prepare_input()

    def initialize_priority_layers(self):
        """Prepares the priority weighted layers UI with the defaults"""

        selected_groups = []
        for layer in settings_manager.get_priority_layers():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, layer.get("name"))
            item.setData(QtCore.Qt.UserRole, layer.get("uuid"))

            self.priority_layers_list.addItem(item)
            log(f"adding item {layer['name']} groups - {layer['groups']}")
            if layer.get("selected"):
                selected_groups = layer["groups"]
                self.priority_layers_list.setCurrentItem(item)

        scroll_container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)

        for group in PRIORITY_GROUPS:
            group_widget = PriorityGroupWidget(group)

            layer_group = None
            for selected_group in selected_groups:
                if selected_group["name"] == group["name"]:
                    layer_group = selected_group

            group_widget.set_group(layer_group)

            self.priority_groups_widgets[group["name"]] = group_widget

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

    def save_current_groups(self):
        item = self.priority_layers_list.currentItem()
        groups = []
        for key, group_widget in self.priority_groups_widgets.items():
            group = {
                "name": group_widget.name(),
                "value": int(group_widget.group_value() or 0),
            }
            groups.append(group)
        layer_id = item.data(QtCore.Qt.UserRole)
        layer = settings_manager.get_priority_layer(layer_id)
        layer["groups"] = groups
        layer["selected"] = True
        settings_manager.save_priority_layer(layer)
        settings_manager.set_current_priority_layer(layer_id)

    def update_priority_layers(self):
        self.priority_layers_list.clear()
        for layer in settings_manager.get_priority_layers():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, layer.get("name"))
            item.setData(QtCore.Qt.UserRole, layer.get("uuid"))

            self.priority_layers_list.addItem(item)

            if layer.get("selected"):
                self.priority_layers_list.setCurrentItem(item)
                self.update_priority_groups(item, None)

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

        self.save_groups_btn.clicked.connect(self.save_current_groups)

        settings_manager.priority_layers_changed.connect(self.update_priority_layers)

        self.add_pwl_btn.clicked.connect(self.add_priority_layer)
        self.edit_pwl_btn.clicked.connect(self.edit_priority_layer)
        self.remove_pwl_btn.clicked.connect(self.remove_priority_layer)

        self.priority_layers_list.currentItemChanged.connect(
            self.update_priority_groups
        )

    def update_priority_groups(self, item, previous):
        if item is not None:
            layer_id = item.data(QtCore.Qt.UserRole)
            layer = settings_manager.get_priority_layer(layer_id)

            for group in layer.get("groups", []):
                group_widget = self.priority_groups_widgets.get(group["name"])
                group_widget.set_group(group)

    def add_priority_layer(self):
        """Adds a new priority layer into the plugin, then updates
        the priority list to show the new added priority layer.
        """
        layer_dialog = PriorityLayerDialog()
        layer_dialog.exec_()
        self.update_priority_layers()

    def edit_priority_layer(self):
        """Edits the passed layer and updates the layer box list."""
        current_text = self.priority_layers_list.currentItem().data(
            QtCore.Qt.DisplayRole
        )
        if current_text == "":
            return
        layer = settings_manager.find_layer_by_name(current_text)
        layer_dialog = PriorityLayerDialog(layer)
        layer_dialog.exec_()

        self.update_priority_layers()

    def remove_priority_layer(self):
        """Removes the current active priority layer."""
        current_text = self.priority_layers_list.currentItem().data(
            QtCore.Qt.DisplayRole
        )
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

    def open_settings(self):
        """Options the CPLUS settings in the QGIS options dialog."""
        self.iface.showOptionsDialog(currentPage=OPTIONS_TITLE)

    def on_step_changed(self, index: int):
        """Slot raised when the current tab changes.

        :param index: Zero-based index position of new current tab.
        :type index: int
        """
        if index == 1:
            self.implementation_model_widget.load()
