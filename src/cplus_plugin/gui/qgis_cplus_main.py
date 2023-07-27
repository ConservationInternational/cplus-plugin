# -*- coding: utf-8 -*-

"""
 The plugin main window class.
"""

import os

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets,
    QtNetwork,
)

from qgis.PyQt.uic import loadUiType


from qgis import processing

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsProject,
    QgsProcessing,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsRectangle,
    QgsTask,
    QgsWkbTypes,
)

from qgis.gui import (
    QgsMessageBar,
    QgsMapCanvas,
    QgsRubberBand,
)

from qgis.utils import iface

from .implementation_model_widget import ImplementationModelContainerWidget
from .priority_group_widget import PriorityGroupWidget

from ..conf import settings_manager

from ..resources import *

from ..utils import open_documentation, tr, log

from ..definitions.defaults import (
    ADD_LAYER_ICON_PATH,
    PILOT_AREA_EXTENT,
    OPTIONS_TITLE,
    ICON_PATH,
    REMOVE_LAYER_ICON_PATH,
    USER_DOCUMENTATION_SITE,
)

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_cplus_main_dockwidget.ui")
)


class QgisCplusMain(QtWidgets.QDockWidget, WidgetUi):
    """Main plugin UI"""

    analysis_finished = QtCore.pyqtSignal(dict)

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

        # Step 3, priority weighting layers initialization
        self.priority_groups_widgets = {}

        self.initialize_priority_layers()

        self.analysis_finished.connect(self.post_analysis)

    def prepare_input(self):
        """Initializes plugin input widgets"""
        self.prepare_extent_box()
        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.prepare_message_bar()

        self.progress_bar = QtWidgets.QProgressBar()

        self.help_btn.clicked.connect(self.open_help)
        self.pilot_area_btn.clicked.connect(self.zoom_pilot_area)
        self.run_scenario_btn.clicked.connect(self.run_scenario_analysis)
        self.options_btn.clicked.connect(self.open_settings)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        add_layer_icon = QtGui.QIcon(ADD_LAYER_ICON_PATH)
        self.layer_add_btn.setIcon(add_layer_icon)

        remove_layer_icon = QtGui.QIcon(REMOVE_LAYER_ICON_PATH)
        self.layer_remove_btn.setIcon(remove_layer_icon)

        self.layer_add_btn.clicked.connect(self.add_priority_layer_group)
        self.layer_remove_btn.clicked.connect(self.remove_priority_layer_group)

    def initialize_priority_layers(self):
        """Prepares the priority weighted layers UI with the defaults.

        Gets the store priority layers from plugin settings and populates
        them into the QListWidget as QListWidgetItems then fetches the
        priority groups and adds them to the QTreeWidget as QTreeWidgetItems
        with their corresponding priority layers as their child items.
        """
        self.priority_layers_list.clear()

        for layer in settings_manager.get_priority_layers():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, layer.get("name"))
            item.setData(QtCore.Qt.UserRole, layer.get("uuid"))

            self.priority_layers_list.addItem(item)

        list_items = []
        items_only = []
        stored_priority_groups = settings_manager.get_priority_groups()
        self.priority_groups_list.clear()
        self.priority_groups_widgets

        for group in stored_priority_groups:
            group_widget = PriorityGroupWidget(
                group,
            )
            group_widget.input_value_changed.connect(self.group_value_changed)
            group_widget.slider_value_changed.connect(self.group_value_changed)

            self.priority_groups_widgets[group["name"]] = group_widget

            pw_layers = settings_manager.find_layers_by_group(group["name"])

            item = QtWidgets.QTreeWidgetItem()
            item.setSizeHint(0, group_widget.sizeHint())
            item.setExpanded(True)

            # Add priority layers into the group as a child items.

            item.setExpanded(True) if len(pw_layers) > 0 else None

            for layer in pw_layers:
                if item.parent() is None:
                    layer_item = QtWidgets.QTreeWidgetItem(item)
                    layer_item.setText(0, layer.get("name"))

            list_items.append((item, group_widget))
            items_only.append(item)

        self.priority_groups_list.addTopLevelItems(items_only)
        for item in list_items:
            self.priority_groups_list.setItemWidget(item[0], 0, item[1])

    def group_value_changed(self, group_name, group_value):
        """Slot to handle priority group widget changes.

        :param group_name: Group name
        :type group_name: str

        :param group_value: Group value
        :type group_value: int
        """

        group = settings_manager.find_group_by_name(group_name)
        group["value"] = group_value
        settings_manager.save_priority_group(group)

        for index in range(self.priority_groups_list.topLevelItemCount()):
            item = self.priority_groups_list.topLevelItem(index)

            for child_index in range(item.childCount()):
                child = item.child(child_index)
                layer = settings_manager.find_layer_by_name(child.text(0))
                new_groups = []
                for group in layer.get("groups"):
                    if group.get("name") == group_name:
                        group["value"] = group_value
                    new_groups.append(group)
                layer["groups"] = new_groups
                settings_manager.save_priority_layer(layer)

    def update_priority_layers(self):
        """Updates the priority weighting layers list in the UI."""
        self.priority_layers_list.clear()
        for layer in settings_manager.get_priority_layers():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, layer.get("name"))
            item.setData(QtCore.Qt.UserRole, layer.get("uuid"))

            self.priority_layers_list.addItem(item)
            for index in range(self.priority_groups_list.topLevelItemCount()):
                group = self.priority_groups_list.topLevelItem(index)
                if group.text(0) in layer.get("groups"):
                    self.add_priority_layer_group(group, item)
                else:
                    group_children = group.takeChildren()
                    children = []
                    for child in group_children:
                        if child.text(0) == layer.get("name"):
                            continue
                        children.append(child)
                    group.addChildren(children)

    def add_priority_layer_group(self, target_group=None, priority_layer=None):
        """Adds priority layer from the weighting layers into a priority group
           If no target_group or priority_layer is passed then the current selected
           group or priority layer from their respective list will be used.

           Checks if priority layer is already in the target group and if so no
           addition is done.

           After addition is done the respective priority layer plugin settings
           are updated to store the new information.

        :param target_group: Priority group where layer will be added to
        :type target_group: dict

        :param priority_layer: Priority weighting layer to be added
        :type priority_layer: dict
        """
        selected_priority_layer = (
            priority_layer or self.priority_layers_list.currentItem()
        )
        selected_group = target_group or self.priority_groups_list.currentItem()

        if (
            selected_group is not None and selected_group.parent() is None
        ) and selected_priority_layer is not None:
            children = selected_group.takeChildren()
            item_found = False
            text = selected_priority_layer.data(QtCore.Qt.DisplayRole)
            for child in children:
                if child.text(0) == text:
                    item_found = True
                    break
            selected_group.addChildren(children)

            if not item_found:
                selected_group.setExpanded(True)
                item = QtWidgets.QTreeWidgetItem(selected_group)
                item.setText(0, text)
                group_widget = self.priority_groups_list.itemWidget(selected_group, 0)
                layer_id = selected_priority_layer.data(QtCore.Qt.UserRole)

                priority_layer = settings_manager.get_priority_layer(layer_id)
                target_group_name = (
                    group_widget.group.get("name") if group_widget.group else None
                )

                groups = priority_layer.get("groups")
                new_groups = []
                group_found = False

                for group in groups:
                    if target_group_name == group["name"]:
                        group_found = True
                        new_group = settings_manager.find_group_by_name(
                            target_group_name
                        )
                    else:
                        new_group = group
                    new_groups.append(new_group)
                if not group_found:
                    searched_group = settings_manager.find_group_by_name(
                        target_group_name
                    )
                    new_groups.append(searched_group)

                priority_layer["groups"] = new_groups
                settings_manager.save_priority_layer(priority_layer)

    def remove_priority_layer_group(self, target_group=None, priority_layer=None):
        """Remove priority layer from a priority group.
           If no target_group or priority_layer is passed then the current selected
           group or priority layer from their respective list will be used.

           Checks if priority layer is already in the target group and if no,
           the removal is not performed.

        :param target_group: Priority group where layer will be removed from
        :type target_group: dict

        :param priority_layer: Priority weighting layer to be removed
        :type priority_layer: dict
        """
        selected_group = self.priority_groups_list.currentItem()
        parent_item = selected_group.parent() if selected_group is not None else None

        if parent_item:
            priority_layer = settings_manager.find_layer_by_name(selected_group.text(0))
            group_widget = self.priority_groups_list.itemWidget(parent_item, 0)

            groups = priority_layer.get("groups")
            new_groups = []
            for group in groups:
                if group.get("name") == group_widget.group.get("name"):
                    continue
                new_groups.append(group)
            priority_layer["groups"] = new_groups
            settings_manager.save_priority_layer(priority_layer)

            parent_item.removeChild(selected_group)

    def open_help(self):
        """Opens the user documentation for the plugin in a browser"""
        open_documentation(USER_DOCUMENTATION_SITE)

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
        """Performs the scenario analysis. This covers the pilot study area,
        and checks whether the AOI is outside the pilot study area.
        """
        extent_list = PILOT_AREA_EXTENT["coordinates"]
        default_extent = QgsRectangle(
            extent_list[3], extent_list[2], extent_list[1], extent_list[0]
        )
        passed_extent = self.extent_box.outputExtent()
        contains = default_extent == passed_extent or default_extent.contains(
            passed_extent
        )

        scenario_name = self.scenario_name.text()
        scenario_description = self.scenario_description.text()

        implementation_models = [
            item.implementation_model
            for item in self.implementation_model_widget.selected_items()
        ]

        priority_weight_layers = self.priority_layers_list.selectedItems()

        if scenario_name == "" or scenario_name is None:
            self.show_message(
                tr(f"Scenario name cannot be blank."),
                level=Qgis.Critical,
            )
            return
        if scenario_description == "" or scenario_description is None:
            self.show_message(
                tr(f"Scenario description cannot be blank."),
                level=Qgis.Critical,
            )
            return
        if implementation_models == [] or implementation_models is None:
            self.show_message(
                tr("Select at least one implementation models from step two."),
                level=Qgis.Info,
            )
            return
        if priority_weight_layers == [] or priority_weight_layers is None:
            self.show_message(
                tr(
                    f"Select at least one priority weight layer models from step three."
                ),
                level=Qgis.Info,
            )
            return

        if contains:
            self.show_message(
                tr(f"Selected area of interest is inside the pilot area."),
                level=Qgis.Info,
            )
            try:
                run_task = QgsTask.fromFunction(
                    "Run analysis function",
                    self.run_analysis(
                        scenario_name,
                        scenario_description,
                        passed_extent,
                        implementation_models,
                        priority_weight_layers,
                    ),
                )
                QgsApplication.taskManager().addTask(run_task)
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
                        'scenario analysis, error message "{}" type "{}"'.format(
                            err, type(err)
                        )
                    )
                )

        else:
            self.show_message(
                tr("Selected area of interest is outside the pilot area."),
                level=Qgis.Critical,
            )
            return

    def run_analysis(
        self,
        scenario_name,
        scenario_description,
        passed_extent,
        implementation_models,
        priority_weight_layers,
    ):
        """Runs the actual scenario analysis by executing processing algorithms

        :param scenario_name: Scenario name
        :type scenario_name: str

        :param scenario_description: Scenario description
        :type scenario_description: str

        :param passed_extent: Area of interest
        :type passed_extent: QgsRectangle

        :param implementation_models: List of the selected implementation models
        :type implementation_models: list

        :param priority_weight_layers: List of the priority weight layers
        :type priority_weight_layers: list

        """
        outputs = {}
        layers = []

        extent = (
            f"{passed_extent.xMinimum()}, {passed_extent.xMaximum()},"
            f"{passed_extent.yMinimum()}, {passed_extent.yMaximum()}"
        )

        for model in implementation_models:
            pathways = model.pathways

            for pathway in pathways:
                layers.append(QgsRasterLayer(pathway.path))

        self.show_progress(
            f"Calculating the highest position",
            minimum=0,
            maximum=100,
        )

        position_feedback = QgsProcessingFeedback()

        position_feedback.progressChanged.connect(self.update_progress_bar)

        alg_params = {
            "IGNORE_NODATA": True,
            "INPUT_RASTERS": layers,
            "EXTENT": extent,
            "OUTPUT_NODATA_VALUE": -9999,
            "REFERENCE_LAYER": layers[0] if len(layers) > 1 else None,
            "OUTPUT": "cplus_scenario_output.tif",
        }
        outputs["HighestPositionInRasterStack"] = processing.run(
            "native:highestpositioninrasterstack",
            alg_params,
            feedback=position_feedback,
        )
        outputs["cplus_scenario_output"] = outputs["HighestPositionInRasterStack"][
            "OUTPUT"
        ]

        # Update progress bar if processing is done
        if outputs["HighestPositionInRasterStack"] is not None:
            self.update_progress_bar(100)

        self.analysis_finished.emit(outputs)

        return True

    def post_analysis(self, outputs):
        """Handles analysis outputs from the final analysis results

        :param outputs: Dictionary of output layers
        :type outputs: dict
        """
        layer = outputs.get("cplus_scenario_output")

        layer = QgsRasterLayer(layer, "cplus_scenario_output")

        QgsProject.instance().addMapLayer(layer)

    def update_progress_bar(self, value):
        """Sets the value of the progress bar

        :param value: Value to be set on the progress bar
        :type value: float
        """
        if self.progress_bar:
            try:
                self.progress_bar.setValue(int(value))
            except RuntimeError:
                log(tr("Error setting value to a progress bar"), notify=False)

    def analysis_progress(self, value):
        """Tracks the analysis progress of value and updates
        the info message when the analysis has finished

        :param value: Analysis progress value
        :type value: int
        """
        if value == 100:
            self.show_message(tr("Analysis has finished."), level=Qgis.Info)

    def update_message_bar(self, message):
        """Changes the message in the message bar item.

        :param message: Message to be updated
        :type message: str
        """
        message_bar_item = self.message_bar.createMessage(message)
        message_bar_item.layout().addWidget(self.progress_bar)
        self.message_bar.pushWidget(message_bar_item, Qgis.Info)

    def show_progress(self, message, minimum=0, maximum=0):
        """Shows the progress message on the main widget message bar

        :param message: Progress message
        :type message: str

        :param minimum: Minimum value that can be set on the progress bar
        :type minimum: int

        :param maximum: Maximum value that can be set on the progress bar
        :type maximum: int
        """

        try:
            self.message_bar.clearWidgets()
            message_bar_item = self.message_bar.createMessage(message)
            self.progress_bar = QtWidgets.QProgressBar()
            self.progress_bar.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.progress_bar.setMinimum(minimum)
            self.progress_bar.setMaximum(maximum)
            message_bar_item.layout().addWidget(self.progress_bar)
            self.message_bar.pushWidget(message_bar_item, Qgis.Info)

        except Exception as e:
            log(f"Error showing progress bar, {e}")

    def show_message(self, message, level=Qgis.Warning):
        """Shows message on the main widget message bar.

        :param message: Text message
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

        :param index: Zero-based index position of new current tab
        :type index: int
        """
        if index == 1:
            self.implementation_model_widget.load()
        elif index == 2:
            # Validate NCS pathway - implementation model mapping
            valid = self.implementation_model_widget.is_valid()
            if not valid:
                msg = self.tr(
                    "Define one or more NCS pathways for at least one implementation model."
                )
                self.show_message(msg)
                self.tab_widget.setCurrentIndex(1)

            else:
                self.message_bar.clearWidgets()

    def open_settings(self):
        """Options the CPLUS settings in the QGIS options dialog."""
        self.iface.showOptionsDialog(currentPage=OPTIONS_TITLE)
