# -*- coding: utf-8 -*-

"""
 The plugin main window class.
"""

import os
import typing
import uuid

import datetime

from functools import partial

from pathlib import Path

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets,
    QtNetwork,
)

from qgis.PyQt.uic import loadUiType

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
    QgsRandomColorRamp,
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

from qgis.gui import (
    QgsMessageBar,
    QgsRubberBand,
)

from qgis.analysis import QgsAlignRaster

from qgis.utils import iface

from .implementation_model_widget import ImplementationModelContainerWidget
from .priority_group_widget import PriorityGroupWidget

from .priority_layer_dialog import PriorityLayerDialog

from ..models.base import Scenario, ScenarioResult, ScenarioState, SpatialExtent
from ..conf import settings_manager, Settings

from ..lib.extent_check import extent_within_pilot
from ..lib.reports.manager import report_manager
from ..models.helpers import clone_implementation_model

from .components.custom_tree_widget import CustomTreeWidget

from ..resources import *

from ..utils import (
    align_rasters,
    clean_filename,
    open_documentation,
    tr,
    log,
    FileUtils,
)

from ..definitions.defaults import (
    ADD_LAYER_ICON_PATH,
    PILOT_AREA_EXTENT,
    PRIORITY_LAYERS,
    OPTIONS_TITLE,
    ICON_PATH,
    QGIS_GDAL_PROVIDER,
    REMOVE_LAYER_ICON_PATH,
    SCENARIO_OUTPUT_FILE_NAME,
    SCENARIO_OUTPUT_LAYER_NAME,
    USER_DOCUMENTATION_SITE,
)
from ..definitions.constants import (
    IM_GROUP_LAYER_NAME,
    IM_WEIGHTED_GROUP_NAME,
    NCS_PATHWAYS_GROUP_LAYER_NAME,
    USER_DEFINED_ATTRIBUTE,
)

from .progress_dialog import ProgressDialog

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/qgis_cplus_main_dockwidget.ui")
)


class QgisCplusMain(QtWidgets.QDockWidget, WidgetUi):
    """Main plugin UI"""

    analysis_finished = QtCore.pyqtSignal(ScenarioResult)

    def __init__(
        self,
        iface,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.progress_dialog = None
        self.task = None
        self.processing_cancelled = False

        self.prepare_input()

        # Insert widget for step 2
        self.implementation_model_widget = ImplementationModelContainerWidget(
            self, self.message_bar
        )
        self.implementation_model_widget.ncs_reloaded.connect(
            self.on_ncs_pathways_reloaded
        )
        self.tab_widget.insertTab(
            1, self.implementation_model_widget, self.tr("Step 2")
        )
        self.tab_widget.currentChanged.connect(self.on_tab_step_changed)

        # Step 3, priority weighting layers initialization
        self.priority_groups_widgets = {}
        self.pwl_item_flags = None

        self.initialize_priority_layers()

        self.position_feedback = QgsProcessingFeedback()
        self.processing_context = QgsProcessingContext()

        self.scenario_result = None

        self.analysis_finished.connect(self.post_analysis)

        # Report manager
        self.report_manager = report_manager
        self.report_manager.generate_started.connect(self.on_report_running)
        self.report_manager.generate_completed.connect(self.on_report_finished)
        self.reporting_feedback: typing.Union[QgsFeedback, None] = None

    def prepare_input(self):
        """Initializes plugin input widgets"""
        self.prepare_extent_box()
        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()
        self.prepare_message_bar()

        self.progress_dialog = None
        self.scenario_directory = None

        self.help_btn.clicked.connect(self.open_help)
        self.pilot_area_btn.clicked.connect(self.zoom_pilot_area)

        self.run_scenario_btn.clicked.connect(self.run_analysis)
        self.options_btn.clicked.connect(self.open_settings)

        self.restore_scenario()

        self.scenario_name.textChanged.connect(self.save_scenario)
        self.scenario_description.textChanged.connect(self.save_scenario)
        self.extent_box.extentChanged.connect(self.save_scenario)

        # Monitors if current extents are within the pilot AOI
        self.extent_box.extentChanged.connect(self.on_extent_changed)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        add_layer_icon = QtGui.QIcon(ADD_LAYER_ICON_PATH)
        self.layer_add_btn.setIcon(add_layer_icon)

        remove_layer_icon = QtGui.QIcon(REMOVE_LAYER_ICON_PATH)
        self.layer_remove_btn.setIcon(remove_layer_icon)

        self.layer_add_btn.clicked.connect(self.add_priority_layer_group)
        self.layer_remove_btn.clicked.connect(self.remove_priority_layer_group)

        # Priority layers buttons
        self.add_pwl_btn.setIcon(FileUtils.get_icon("symbologyAdd.svg"))
        self.edit_pwl_btn.setIcon(FileUtils.get_icon("mActionToggleEditing.svg"))
        self.remove_pwl_btn.setIcon(FileUtils.get_icon("symbologyRemove.svg"))

        self.add_pwl_btn.clicked.connect(self.add_priority_layer)
        self.edit_pwl_btn.clicked.connect(self.edit_priority_layer)
        self.remove_pwl_btn.clicked.connect(self.remove_priority_layer)

        # Add priority groups list into the groups frame
        self.priority_groups_list = CustomTreeWidget()

        self.priority_groups_list.setHeaderHidden(True)

        self.priority_groups_list.setDragEnabled(True)
        self.priority_groups_list.setDragDropOverwriteMode(True)
        self.priority_groups_list.viewport().setAcceptDrops(True)

        self.priority_groups_list.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)

        self.priority_groups_list.child_dragged_dropped.connect(
            self.priority_groups_update
        )

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.priority_groups_list)
        self.priority_groups_frame.setLayout(layout)

        # Scenario analysis variables

        self.analysis_scenario_name = None
        self.analysis_scenario_description = None
        self.analysis_extent = None
        self.analysis_implementation_models = None
        self.analysis_weighted_ims = []
        self.analysis_priority_layers_groups = []

    def priority_groups_update(self, target_item, selected_items):
        """Updates the priority groups list item with the passed
         selected layer items.

        :param target_item: The priority group tree widget
         item that is to be updated
        :type target_item: QTreeWidgetItem

        :param selected_items: Priority layers items from the list widget
        :type selected_items: list
        """
        self.priority_groups_list.setCurrentItem(target_item)

        for item in selected_items:
            self.add_priority_layer_group(target_item, item)

    def update_pwl_layers(self, notify=False):
        """Updates the priority layers path available in
        the store implementation models

        :param notify: Whether to show message to user about the update
        :type notify: bool
        """
        settings_manager.update_implementation_models()
        self.update_priority_layers()
        if notify:
            self.show_message(
                tr(
                    "Updated all the implementation models"
                    " with their respective priority layers"
                ),
                Qgis.Info,
            )
        log(
            tr(
                "Updated all the implementation models"
                " with their respective priority layers"
            )
        )

    def save_scenario(self):
        """Save current scenario details into settings"""
        scenario_name = self.scenario_name.text()
        scenario_description = self.scenario_description.text()
        extent = self.extent_box.outputExtent()

        extent_box = [
            extent.xMinimum(),
            extent.xMaximum(),
            extent.yMinimum(),
            extent.yMaximum(),
        ]

        settings_manager.set_value(Settings.SCENARIO_NAME, scenario_name)
        settings_manager.set_value(Settings.SCENARIO_DESCRIPTION, scenario_description)
        settings_manager.set_value(Settings.SCENARIO_EXTENT, extent_box)

    def restore_scenario(self):
        """Update the first tab input with the last scenario details"""
        scenario_name = settings_manager.get_value(Settings.SCENARIO_NAME)
        scenario_description = settings_manager.get_value(Settings.SCENARIO_DESCRIPTION)
        extent = settings_manager.get_value(Settings.SCENARIO_EXTENT)

        self.scenario_name.setText(scenario_name) if scenario_name is not None else None
        self.scenario_description.setText(
            scenario_description
        ) if scenario_description is not None else None

        if extent is not None:
            extent_rectangle = QgsRectangle(
                float(extent[0]), float(extent[2]), float(extent[1]), float(extent[3])
            )
            self.extent_box.setOutputExtentFromUser(
                extent_rectangle,
                QgsCoordinateReferenceSystem("EPSG:4326"),
            )

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

            if self.pwl_item_flags is None:
                self.pwl_item_flags = item.flags()

            self.priority_layers_list.addItem(item)

        list_items = []
        items_only = []
        stored_priority_groups = settings_manager.get_priority_groups()
        self.priority_groups_list.clear()

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
                    layer_item.setData(
                        0, QtCore.Qt.UserRole, layer.get(USER_DEFINED_ATTRIBUTE)
                    )

            list_items.append((item, group_widget))
            items_only.append(item)

        self.priority_groups_list.addTopLevelItems(items_only)
        for item in list_items:
            self.priority_groups_list.setItemWidget(item[0], 0, item[1])

        # Trigger process to enable/disable PWLs based on current extents
        self.on_extent_changed(self.extent_box.outputExtent())

    def on_ncs_pathways_reloaded(self):
        """Slot raised when NCS pathways have been reloaded in the view."""
        within_pilot_area = extent_within_pilot(
            self.extent_box.outputExtent(), self.extent_box.outputCrs()
        )
        self.implementation_model_widget.enable_default_items(within_pilot_area)

    def on_extent_changed(self, new_extent: QgsRectangle):
        """Slot raised when scenario extents have changed.

        Used to enable/disable default model items if they are within or
        outside the pilot AOI.
        """
        within_pilot_area = extent_within_pilot(new_extent, self.extent_box.outputCrs())

        if not within_pilot_area:
            msg = tr(
                "Area of interest is outside the pilot area. Please use your "
                "own NCS pathways, implementation models and PWLs."
            )
            self.show_message(msg, Qgis.Info)

        else:
            self.message_bar.clearWidgets()

        self.implementation_model_widget.enable_default_items(within_pilot_area)

        # Enable/disable PWL items
        for i in range(self.priority_layers_list.count()):
            pwl_item = self.priority_layers_list.item(i)
            uuid_str = pwl_item.data(QtCore.Qt.UserRole)
            if not uuid_str:
                continue

            pwl_uuid = uuid.UUID(uuid_str)
            pwl = settings_manager.get_priority_layer(pwl_uuid)
            if USER_DEFINED_ATTRIBUTE not in pwl:
                continue

            is_user_defined = pwl.get(USER_DEFINED_ATTRIBUTE)
            if is_user_defined:
                continue

            if within_pilot_area:
                pwl_item.setFlags(self.pwl_item_flags)
            else:
                pwl_item.setFlags(QtCore.Qt.NoItemFlags)

        # Enable/disable PWL items already defined under the priority groups
        for i in range(self.priority_groups_list.topLevelItemCount()):
            group_item = self.priority_groups_list.topLevelItem(i)

            for c in range(group_item.childCount()):
                pwl_tree_item = group_item.child(c)
                is_user_defined = pwl_tree_item.data(0, QtCore.Qt.UserRole)
                if is_user_defined:
                    continue

                if within_pilot_area:
                    pwl_tree_item.setFlags(self.pwl_item_flags)
                else:
                    pwl_tree_item.setFlags(QtCore.Qt.NoItemFlags)

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

    def update_priority_layers(self, update_groups=True):
        """Updates the priority weighting layers list in the UI.

        :param update_groups: Whether to update the priority groups list or not
        :type update_groups: bool
        """
        self.priority_layers_list.clear()
        for layer in settings_manager.get_priority_layers():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, layer.get("name"))
            item.setData(QtCore.Qt.UserRole, layer.get("uuid"))

            self.priority_layers_list.addItem(item)
            if update_groups:
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

        # Trigger check to enable/disable PWLs
        self.on_extent_changed(self.extent_box.outputExtent())

    def add_priority_layer_group(self, target_group=None, priority_layer=None):
        """Adds priority layer from the weighting layers into a priority group
        If no target_group or priority_layer is passed then the current selected
        group or priority layer from their respective list will be used.

        Checks if priority layer is already in the target group and if so no
        addition is done.

        Once the addition is done, the respective priority layer plugin settings
        are updated to store the new information.

        :param target_group: Priority group where layer will be added to
        :type target_group: dict

        :param priority_layer: Priority weighting layer to be added
        :type priority_layer: dict
        """
        selected_priority_layers = (
            priority_layer or self.priority_layers_list.selectedItems()
        )
        selected_priority_layers = (
            [selected_priority_layers]
            if not isinstance(selected_priority_layers, list)
            else selected_priority_layers
        )

        selected_group = target_group or self.priority_groups_list.currentItem()

        for selected_priority_layer in selected_priority_layers:
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
                    group_widget = self.priority_groups_list.itemWidget(
                        selected_group, 0
                    )
                    layer_id = selected_priority_layer.data(QtCore.Qt.UserRole)

                    priority_layer = settings_manager.get_priority_layer(layer_id)
                    item.setData(
                        0,
                        QtCore.Qt.UserRole,
                        priority_layer.get(USER_DEFINED_ATTRIBUTE),
                    )
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

        # Trigger check to enable/disable PWLs based on current extent
        self.on_extent_changed(self.extent_box.outputExtent())

    def remove_priority_layer_group(self):
        """Remove the current select priority layer from the current priority group."""
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

    def add_priority_layer(self):
        """Adds a new priority layer into the plugin, then updates
        the priority list to show the new added priority layer.
        """
        layer_dialog = PriorityLayerDialog()
        layer_dialog.exec_()
        self.update_priority_layers(update_groups=False)

    def edit_priority_layer(self):
        """Edits the current selected priority layer
        and updates the layer box list."""
        if self.priority_layers_list.currentItem() is None:
            self.show_message(
                tr("Select first the priority weighting layer from the layers list."),
                Qgis.Critical,
            )
            return
        current_text = self.priority_layers_list.currentItem().data(
            QtCore.Qt.DisplayRole
        )
        if current_text == "":
            self.show_message(
                tr("Could not fetch the selected priority layer for editing."),
                Qgis.Critical,
            )
            return
        layer = settings_manager.find_layer_by_name(current_text)
        layer_dialog = PriorityLayerDialog(layer)
        layer_dialog.exec_()

    def remove_priority_layer(self):
        """Removes the current active priority layer."""
        if self.priority_layers_list.currentItem() is None:
            self.show_message(
                tr(
                    "Select first the priority " "weighting layer from the layers list."
                ),
                Qgis.Critical,
            )
            return
        current_text = self.priority_layers_list.currentItem().data(
            QtCore.Qt.DisplayRole
        )
        if current_text == "":
            self.show_message(
                tr("Could not fetch the selected priority layer for editing."),
                Qgis.Critical,
            )
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
            self.update_priority_layers(update_groups=False)

    def prepare_message_bar(self):
        """Initializes the widget message bar settings"""
        self.message_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        self.grid_layout.addWidget(
            self.message_bar, 0, 0, 1, 1, alignment=QtCore.Qt.AlignTop
        )
        self.dock_widget_contents.layout().insertLayout(0, self.grid_layout)

    def run_analysis(self):
        """Runs the plugin analysis"""

        extent_list = PILOT_AREA_EXTENT["coordinates"]
        default_extent = QgsRectangle(
            extent_list[0], extent_list[2], extent_list[1], extent_list[3]
        )
        passed_extent = self.extent_box.outputExtent()
        contains = default_extent == passed_extent or default_extent.contains(
            passed_extent
        )
        self.analysis_scenario_name = self.scenario_name.text()
        self.analysis_scenario_description = self.scenario_description.text()

        self.position_feedback = QgsProcessingFeedback()
        self.processing_context = QgsProcessingContext()

        for group in settings_manager.get_priority_groups():
            group_layer_dict = {
                "name": group.get("name"),
                "value": group.get("value"),
                "layers": [],
            }
            for layer in settings_manager.get_priority_layers():
                pwl_items = self.priority_layers_list.findItems(
                    layer.get("name"), QtCore.Qt.MatchExactly
                )
                if len(pwl_items) > 0:
                    # Exclude adding the PWL since its for a disabled default
                    # item outside the pilot AOI.
                    if pwl_items[0].flags() == QtCore.Qt.NoItemFlags:
                        continue

                group_names = [group.get("name") for group in layer.get("groups", [])]
                if group.get("name") in group_names:
                    group_layer_dict["layers"].append(layer.get("name"))
            self.analysis_priority_layers_groups.append(group_layer_dict)

        self.analysis_implementation_models = [
            item.implementation_model
            for item in self.implementation_model_widget.selected_im_items()
            if item.isEnabled()
        ]

        self.analysis_weighted_ims = []

        base_dir = settings_manager.get_value(Settings.BASE_DIR)

        if self.analysis_scenario_name == "" or self.analysis_scenario_name is None:
            self.show_message(
                tr(f"Scenario name cannot be blank."),
                level=Qgis.Critical,
            )
            return
        if (
            self.analysis_scenario_description == ""
            or self.analysis_scenario_description is None
        ):
            self.show_message(
                tr(f"Scenario description cannot be blank."),
                level=Qgis.Critical,
            )
            return
        if (
            self.analysis_implementation_models == []
            or self.analysis_implementation_models is None
        ):
            self.show_message(
                tr("Select at least one implementation models from step two."),
                level=Qgis.Critical,
            )
            return

        if not contains:
            self.show_message(
                tr(f"Selected area of interest is outside the pilot area."),
                level=Qgis.Info,
            )
            default_ext = (
                f"{default_extent.xMinimum()}, {default_extent.xMaximum()},"
                f"{default_extent.yMinimum()}, {default_extent.yMaximum()}"
            )
            log(
                f"Outside the pilot area, passed extent "
                f"{passed_extent}"
                f"default extent{default_ext}"
            )

        if base_dir is None:
            self.show_message(
                tr(
                    f"Plugin base data directory is not set! "
                    f"Go to plugin settings in order to set it."
                ),
                level=Qgis.Critial,
            )
            return
        self.analysis_extent = SpatialExtent(
            bbox=[
                passed_extent.xMinimum(),
                passed_extent.xMaximum(),
                passed_extent.yMinimum(),
                passed_extent.yMaximum(),
            ]
        )

        try:
            self.scenario_directory = (
                f"{base_dir}/"
                f'scenario_{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
            )

            FileUtils.create_new_dir(self.scenario_directory)

            if self.progress_dialog is not None:
                self.progress_dialog.disconnect()

            # Creates and opens the progress dialog for the analysis
            self.progress_dialog = ProgressDialog(
                "Raster calculation",
                "implementation models",
                0,
                100,
                main_widget=self,
            )
            self.progress_dialog.analysis_cancelled.connect(
                self.on_progress_dialog_cancelled
            )
            self.progress_dialog.run_dialog()
            self.progress_dialog.scenario_name = ""
            self.progress_dialog.change_status_message(
                tr("Raster calculation"), tr("models")
            )

        except Exception as err:
            self.show_message(
                tr(
                    "An error occurred when opening the progress dialog, "
                    "check logs for more information"
                ),
                level=Qgis.Info,
            )
            log(
                tr(
                    "An error occurred when opening the progress dialog for "
                    'scenario analysis, error message "{}"'.format(err)
                )
            )

        self.processing_cancelled = False

        self.run_scenario_btn.setEnabled(False)

        self.run_pathways_analysis(
            self.analysis_implementation_models,
            self.analysis_priority_layers_groups,
            self.analysis_extent,
        )

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

            alg = QgsApplication.processingRegistry().algorithmById(
                "native:highestpositioninrasterstack"
            )

            # self.processing_cancelled = False
            self.task = QgsProcessingAlgRunnerTask(
                alg,
                alg_params,
                self.processing_context,
                feedback=self.position_feedback,
            )
            self.task.executed.connect(self.scenario_results)
            QgsApplication.taskManager().addTask(self.task)

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

    def transform_extent(self, extent, source_crs, dest_crs):
        """Transforms the passed extent into the destination crs

         :param extent: Target extent
        :type extent: QgsRectangle

        :param source_crs: Source CRS of the passed extent
        :type source_crs: QgsCoordinateReferenceSystem

        :param dest_crs: Destination CRS
        :type dest_crs: QgsCoordinateReferenceSystem
        """

        transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
        transformed_extent = transform.transformBoundingBox(extent)

        return transformed_extent

    def main_task(self):
        """Serves as a QgsTask function for the main task that contains
        smaller sub-tasks running the actual processing calculations.
        """

        log("Running from main task.")

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

    def pathways_analysis_done(
        self,
        pathway_count,
        models,
        extent,
        priority_layers_groups,
        pathways,
        pathway,
        last_pathway,
        success,
        output,
    ):
        """Slot that handles post calculations for the models pathways and
         carbon layers.

        :param pathways: List of all the avaialble pathways
        :type pathways: list

        :param pathway: Target pathway
        :type pathway: NCSPathway

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers
        groups and their values
        :type priority_layers_groups: dict

        :param last_pathway: Whether the pathway is the last from
         the models pathway list
        :type last_pathway: bool

        :param success: Whether the scenario analysis was successful
        :type success: bool

        :param output: Analysis output results
        :type output: dict
        """
        if output is not None and output.get("OUTPUT") is not None:
            pathway.path = output.get("OUTPUT")

        if (pathway_count == len(pathways) - 1) and last_pathway:
            snapping_enabled = settings_manager.get_value(
                Settings.SNAPPING_ENABLED, default=False, setting_type=bool
            )
            reference_layer = settings_manager.get_value(
                Settings.SNAP_LAYER, default=""
            )
            reference_layer_path = Path(reference_layer)
            if (
                snapping_enabled
                and os.path.exists(reference_layer)
                and reference_layer_path.is_file()
            ):
                self.snap_analyzed_pathways(
                    pathways, models, priority_layers_groups, extent
                )
            else:
                self.run_pathways_normalization(models, priority_layers_groups, extent)

    def snap_analyzed_pathways(self, pathways, models, priority_layers_groups, extent):
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
        pathway_count = 0

        main_task = QgsTask.fromFunction(
            "Main task for running pathways snapping on the background task",
            self.main_task,
            on_finished=self.main_task,
        )

        main_task.taskCompleted.connect(self.main_task)

        previous_sub_tasks = []

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
            snapping_function = partial(
                self.run_snap_task,
                pathway.path,
                reference_layer_path,
                None,
                directory,
                rescale_values,
                resampling_method,
                pathway,
            )

            on_snap_finished = partial(
                self.snap_task_finished,
                pathways,
                pathway_count,
                models,
                priority_layers_groups,
                extent,
            )
            self.task = QgsTask.fromFunction(
                f"Snapping pathway {pathway.name}",
                snapping_function,
                on_finished=on_snap_finished,
            )

            main_task.addSubTask(
                self.task, previous_sub_tasks, QgsTask.ParentDependsOnSubTask
            )
            previous_sub_tasks.append(self.task)
            pathway_count = pathway_count + 1

        QgsApplication.taskManager().addTask(main_task)

    def run_snap_task(
        self,
        path,
        reference_layer_path,
        extent,
        base_dir,
        rescale_values,
        resampling_method,
        pathway,
        task,
    ):
        """Intermediate function used to hold the QgsTaskWrapper (task) variable
         which is passed dynamically when using a function as a callback for a QgsTask.

         This inturns calls the align raster function that is responsible for handling the
         snap operation.

        :param path: Path of the input pathway layer
        :type path: str

        :param path: Path of the reference layer to be used when snapping
        :type path: str

        :param extent: Snapping extent
        :type extent: list

        :param base_dir: Directory where to store the snapped layer
        :type base_dir: str

        :param rescale_values: Whether to rescale snapped pixel values
        :type rescale_values: bool

        :param resampling_method: Index of the algorithm to use for sampling as
        defined from QgsAlignRaster.ResampleAlg
        :type resampling_method: bool

        :param pathway: NCS pathway instance that contains the input path
        :type pathway: NCSPathway

         :param task: Qgis task wrapper instance
        :type task: QgsTaskWrapper
        """

        input_result_path, reference_result_path = align_rasters(
            path,
            reference_layer_path,
            extent,
            base_dir,
            rescale_values,
            resampling_method,
        )
        pathway.path = input_result_path

    def snap_task_finished(
        self,
        pathways,
        pathway_count,
        models,
        priority_layers_groups,
        extent,
        exception=None,
    ):
        """Handles operations to be done after snap task has finished

        :param pathways: List of all the available pathways
        :type pathways: list

        :param pathway_count: Count of the snapped pathways
        :type pathway_count: int

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: The selected extent from user
        :type extent: list

        :param exception: Exception that occured while running the snapping task.
        :type exception: Exception
        """
        if pathway_count == len(pathways) - 1:
            self.run_pathways_normalization(models, priority_layers_groups, extent)

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

        pathway_count = 0

        priority_function = partial(
            self.run_models_analysis, models, priority_layers_groups, extent
        )
        main_task = QgsTask.fromFunction(
            "Running pathways normalization",
            self.main_task,
            on_finished=priority_function,
        )

        previous_sub_tasks = []

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
                main_task.cancel()
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

            analysis_done = partial(
                self.pathways_normalization_done,
                pathway_count,
                models,
                extent,
                priority_layers_groups,
                pathways,
                pathway,
                (pathway_count == len(pathways) - 1),
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

    def pathways_normalization_done(
        self,
        pathway_count,
        models,
        extent,
        priority_layers_groups,
        pathways,
        pathway,
        last_pathway,
        success,
        output,
    ):
        """Slot that handles normalized pathways layers.

        :param model_index: List index of the target model
        :type model_index: int

        :param pathway: Target pathway
        :type pathway: NCSPathway

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers
        groups and their values
        :type priority_layers_groups: dict

        :param last_pathway: Whether the pathway is the last from
         the models pathway list
        :type last_pathway: bool

        :param success: Whether the scenario analysis was successful
        :type success: bool

        :param output: Analysis output results
        :type output: dict
        """
        if output is not None and output.get("OUTPUT") is not None:
            pathway.path = output.get("OUTPUT")

        if (pathway_count == len(pathways) - 1) and last_pathway:
            self.run_models_analysis(models, priority_layers_groups, extent)

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

        model_count = 0

        priority_function = partial(
            self.run_normalization_analysis, models, priority_layers_groups, extent
        )
        main_task = QgsTask.fromFunction(
            "Running main functions", self.main_task, on_finished=priority_function
        )

        previous_sub_tasks = []

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
                main_task.cancel()
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

            analysis_done = partial(
                self.model_analysis_done,
                model_count,
                model,
                models,
                extent,
                priority_layers_groups,
            )

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

            alg = QgsApplication.processingRegistry().algorithmById(
                "native:cellstatistics"
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

            model_count = model_count + 1

        QgsApplication.taskManager().addTask(main_task)

    def model_analysis_done(
        self,
        model_index,
        model,
        models,
        extent,
        priority_layers_groups,
        success,
        output,
    ):
        """Slot that handles post calculations for the models layers

        :param model_index: List index of the target model
        :type model_index: int

        :param model: Target implementation model
        :type model: ImplementationModel

        :param model: List of the selected implementation models
        :type model: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups
         and their values
        :type priority_layers_groups: dict

        :param success: Whether the scenario analysis was successful
        :type success: bool

        :param output: Analysis output results
        :type output: dict
        """
        if output is not None and output.get("OUTPUT") is not None:
            model.path = output.get("OUTPUT")

        if model_index == len(models) - 1:
            self.run_normalization_analysis(models, priority_layers_groups, extent)

    def run_normalization_analysis(self, models, priority_layers_groups, extent):
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

        model_count = 0

        priority_function = partial(
            self.run_priority_analysis, models, priority_layers_groups, extent
        )
        main_task = QgsTask.fromFunction(
            "Running normalization", self.main_task, on_finished=priority_function
        )

        previous_sub_tasks = []

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

                main_task.cancel()
                return False

            basenames = []
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

            analysis_done = partial(
                self.normalization_analysis_done,
                model_count,
                model,
                models,
                extent,
                priority_layers_groups,
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

            model_count = model_count + 1

        QgsApplication.taskManager().addTask(main_task)

    def normalization_analysis_done(
        self,
        model_index,
        model,
        models,
        extent,
        priority_layers_groups,
        success,
        output,
    ):
        """Slot that handles normalized models layers.

        :param model_index: List index of the target model
        :type model_index: int

        :param model: Target implementation model
        :type model: ImplementationModel

        :param models: List of the selected implementation models
        :type modesls: typing.List[ImplementationModel]

        :param success: Whether the scenario analysis was successful
        :type success: bool

        :param output: Analysis output results
        :type output: dict
        """
        if output is not None and output.get("OUTPUT") is not None:
            model.path = output.get("OUTPUT")

        if model_index == len(models) - 1:
            self.run_priority_analysis(models, priority_layers_groups, extent)

    def run_priority_analysis(self, models, priority_layers_groups, extent):
        """Runs the required model analysis on the passed implementation models

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param priority_layers_groups: Used priority layers groups and their values
        :type priority_layers_groups: dict

        :param extent: selected extent from user
        :type extent: str
        """
        model_count = 0

        main_task = QgsTask.fromFunction(
            "Running main task for priority layers weighting",
            self.main_task,
            on_finished=self.run_highest_position_analysis,
        )
        models_cleaning = partial(self.run_models_cleaning, extent)

        main_task.taskCompleted.connect(models_cleaning)

        previous_sub_tasks = []

        self.progress_dialog.analysis_finished_message = tr(f"Weighting")

        self.progress_dialog.scenario_name = tr(f"implementation models")

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
                main_task.cancel()

                return False

            basenames = []
            layers = []

            analysis_done = partial(
                self.priority_layers_analysis_done, model_count, model, models, extent
            )
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
                return

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

            model_count = model_count + 1

        QgsApplication.taskManager().addTask(main_task)

    def priority_layers_analysis_done(
        self, model_index, model, models, extent, success, output
    ):
        """Slot that handles post calculations for the models priority layers

        :param model_index: List index of the target model
        :type model_index: int

        :param model: Target implementation model
        :type model: ImplementationModel

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param extent: selected extent from user
        :type extent: str

        :param success: Whether the scenario analysis was successful
        :type success: bool

        :param output: Analysis output results
        :type output: dict
        """
        if output is not None and output.get("OUTPUT") is not None:
            model.path = output.get("OUTPUT")

        self.analysis_weighted_ims.append(model)

        if model_index == len(models) - 1:
            self.run_models_cleaning(extent)

    def run_models_cleaning(self, extent=None):
        """Runs cleaning on the weighted implementation models replacing
        zero values with no-data as they are not statistical meaningful for the
        whole analysis.

        :param extent: Selected extent from user
        :type extent: str
        """
        model_count = 0

        main_task = QgsTask.fromFunction(
            "Running main task for weighted models updates",
            self.main_task,
            on_finished=self.run_highest_position_analysis,
        )

        main_task.taskCompleted.connect(self.run_highest_position_analysis)

        previous_sub_tasks = []

        self.progress_dialog.analysis_finished_message = tr(f"Updating")

        self.progress_dialog.scenario_name = tr(f"implementation models")

        for model in self.analysis_weighted_ims:
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
                main_task.cancel()

            analysis_done = partial(
                self.models_update_done, model_count, model, self.analysis_weighted_ims
            )

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

            alg = QgsApplication.processingRegistry().algorithmById(
                "native:cellstatistics"
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

            model_count = model_count + 1

        QgsApplication.taskManager().addTask(main_task)

    def models_update_done(self, model_index, model, models, success, output):
        """Slot that handles post operations for the updates on the weighted models.

        :param model_index: List index of the target model
        :type model_index: int

        :param model: Target implementation model
        :type model: ImplementationModel

        :param models: List of the selected implementation models
        :type models: typing.List[ImplementationModel]

        :param success: Whether the scenario analysis was successful
        :type success: bool

        :param output: Analysis output results
        :type output: dict
        """
        if output is not None and output.get("OUTPUT") is not None:
            model.path = output.get("OUTPUT")

        if model_index == len(models) - 1:
            self.run_highest_position_analysis()

    def cancel_processing_task(self):
        """Cancels the current processing task."""
        self.processing_cancelled = True

        # Analysis processing tasks
        try:
            if self.task:
                self.task.cancel()
        except Exception as e:
            self.on_progress_dialog_cancelled()
            log(f"Problem cancelling task, {e}")

        # Report generating task
        try:
            if self.reporting_feedback:
                self.reporting_feedback.cancel()
        except Exception as e:
            self.on_progress_dialog_cancelled()
            log(f"Problem cancelling report generating task, {e}")

    def scenario_results(self, success, output):
        """Called when the task ends. Sets the progress bar to 100 if it finished.

        :param success: Whether the scenario analysis was successful
        :type success: bool

        :param output: Analysis output results
        :type output: dict
        """
        if output is not None:
            self.update_progress_bar(100)
            self.scenario_result.analysis_output = output
            self.scenario_result.state = ScenarioState.FINISHED
            self.analysis_finished.emit(self.scenario_result)

        else:
            self.progress_dialog.change_status_message(
                "No valid output from the processing results."
            )
            log(f"No valid output from the processing results.")

    def move_layer_to_group(self, layer, group) -> None:
        """Moves a layer open in QGIS to another group.

        :param layer: Raster layer to move
        :type layer: QgsRasterLayer

        :param group: Group to which the raster should be moved
        :type group: QgsLayerTreeGroup
        """
        if layer:
            instance_root = QgsProject.instance().layerTreeRoot()
            layer = instance_root.findLayer(layer.id())
            layer_clone = layer.clone()
            parent = layer.parent()
            group.insertChildNode(0, layer_clone)  # Add to top of group
            parent.removeChildNode(layer)

    def post_analysis(self, scenario_result):
        """Handles analysis outputs from the final analysis results.
        Adds the resulting scenario raster to the canvas with styling.
        Adds each of the implementation models to the canvas with styling.
        Adds each IMs pathways to the canvas.

        :param scenario_result: ScenarioResult of output results
        :type scenario_result: ScenarioResult
        """

        # If the processing were stopped, no file will be added
        if not self.processing_cancelled:
            list_models = scenario_result.scenario.models
            raster = scenario_result.analysis_output["OUTPUT"]
            im_weighted_dir = os.path.dirname(raster) + "/weighted_ims/"
            list_weighted_ims = (
                os.listdir(im_weighted_dir) if os.path.exists(im_weighted_dir) else []
            )

            scenario_name = scenario_result.scenario.name
            qgis_instance = QgsProject.instance()
            instance_root = qgis_instance.layerTreeRoot()

            # Check if there are other groups for the scenario
            # and assign a suffix.
            counter = 1
            group_name = scenario_name

            # Control to prevent infinite loop
            max_limit = 100
            while True and counter <= max_limit:
                scenario_grp = instance_root.findGroup(group_name)
                if scenario_grp is None:
                    break
                group_name = f"{scenario_name} {counter!s}"
                counter += 1

            # Groups
            scenario_group = instance_root.insertGroup(0, group_name)
            im_group = scenario_group.addGroup(tr(IM_GROUP_LAYER_NAME))
            im_weighted_group = (
                scenario_group.addGroup(tr(IM_WEIGHTED_GROUP_NAME))
                if os.path.exists(im_weighted_dir)
                else None
            )
            pathways_group = scenario_group.addGroup(tr(NCS_PATHWAYS_GROUP_LAYER_NAME))

            # Group settings
            im_group.setExpanded(False)
            im_weighted_group.setExpanded(False) if im_weighted_group else None
            pathways_group.setExpanded(False)
            pathways_group.setItemVisibilityCheckedRecursive(False)

            # Add scenario result layer to the canvas with styling
            layer_file = scenario_result.analysis_output.get("OUTPUT")
            layer_name = (
                f"{SCENARIO_OUTPUT_LAYER_NAME}_"
                f'{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
            )
            scenario_result.output_layer_name = layer_name
            layer = QgsRasterLayer(layer_file, layer_name, QGIS_GDAL_PROVIDER)
            scenario_layer = qgis_instance.addMapLayer(layer)

            # Scenario result layer styling
            renderer = self.style_models_layer(layer, self.analysis_weighted_ims)
            layer.setRenderer(renderer)
            layer.triggerRepaint()

            """A workaround to add a layer to a group.
            Adding it using group.insertChildNode or group.addLayer causes issues,
            but adding to the root is fine.
            This approach adds it to the root, and then moves it to the group.
            """
            self.move_layer_to_group(scenario_layer, scenario_group)

            # Add implementation models and pathways
            im_index = 0
            for im in list_models:
                im_name = im.name
                im_layer = QgsRasterLayer(im.path, im.name)
                list_pathways = im.pathways

                # Add IM layer with styling, if available
                if im_layer:
                    renderer = self.style_model_layer(im_layer, im)

                    added_im_layer = qgis_instance.addMapLayer(im_layer)
                    self.move_layer_to_group(added_im_layer, im_group)

                    im_layer.setRenderer(renderer)
                    im_layer.triggerRepaint()

                # Add IM pathways
                if len(list_pathways) > 0:
                    # im_pathway_group = pathways_group.addGroup(im_name)
                    im_pathway_group = pathways_group.insertGroup(im_index, im_name)
                    im_pathway_group.setExpanded(False)

                    pw_index = 0
                    for pathway in list_pathways:
                        try:
                            # pathway_name = pathway.name
                            pathway_layer = pathway.to_map_layer()

                            added_pw_layer = qgis_instance.addMapLayer(pathway_layer)
                            self.move_layer_to_group(added_pw_layer, im_pathway_group)

                            pathway_layer.triggerRepaint()

                            pw_index = pw_index + 1
                        except Exception as err:
                            self.show_message(
                                tr(
                                    "An error occurred loading a pathway, "
                                    "check logs for more information"
                                ),
                                level=Qgis.Info,
                            )
                            log(
                                tr(
                                    "An error occurred loading a pathway, "
                                    'scenario analysis, error message "{}"'.format(err)
                                )
                            )

                im_index = im_index + 1

            for model in self.analysis_weighted_ims:
                weighted_im_path = model.path
                weighted_im_name = Path(weighted_im_path).stem

                if not weighted_im_path.endswith(".tif"):
                    continue

                im_weighted_layer = QgsRasterLayer(
                    weighted_im_path, weighted_im_name, QGIS_GDAL_PROVIDER
                )

                renderer = self.style_model_layer(im_weighted_layer, model)
                im_weighted_layer.setRenderer(renderer)
                im_weighted_layer.triggerRepaint()

                added_im_weighted_layer = qgis_instance.addMapLayer(im_weighted_layer)
                self.move_layer_to_group(added_im_weighted_layer, im_weighted_group)

            # Initiate report generation
            self.run_report()
        else:
            # Reinitializes variables if processing were cancelled by the user
            # Not doing this breaks the processing if a user tries to run
            # the processing after cancelling or if the processing fails
            self.position_feedback = QgsProcessingFeedback()
            self.processing_context = QgsProcessingContext()

    def style_models_layer(self, layer, models):
        """Applies the styling to the passed layer that
         contains the passed list of models.

        :param layer: Layer to be styled
        :type layer: QgsRasterLayer

        :param models: List which contains the implementation
        models that were passed to the highest position analysis tool
        :type models: list

        :returns: Renderer for the symbology.
        :rtype: QgsPalettedRasterRenderer
        """
        area_classes = []
        for model in models:
            im_name = model.name

            raster_val = model.style_pixel_value
            color = model.scenario_fill_symbol().color()
            color_ramp_shader = QgsColorRampShader.ColorRampItem(
                float(raster_val), QtGui.QColor(color), im_name
            )
            area_classes.append(color_ramp_shader)

        class_data = QgsPalettedRasterRenderer.colorTableToClassData(area_classes)
        renderer = QgsPalettedRasterRenderer(layer.dataProvider(), 1, class_data)

        return renderer

    def style_model_layer(self, layer, model):
        """Applies the styling to the layer that contains the passed
         implementation model name.

        :param layer: Raster layer to which to apply the symbology
        :type layer: QgsRasterLayer

        :param model: Implementation model
        :type model: ImplementationModel

        :returns: Renderer for the symbology.
        :rtype: QgsSingleBandPseudoColorRenderer
        """

        # Retrieves a build-in QGIS color ramp
        color_ramp = model.model_color_ramp()

        stats = layer.dataProvider().bandStatistics(1)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1)

        renderer.setClassificationMin(stats.minimumValue)
        renderer.setClassificationMax(stats.maximumValue)

        renderer.createShader(
            color_ramp, QgsColorRampShader.Interpolated, QgsColorRampShader.Continuous
        )

        return renderer

    def update_progress_bar(self, value):
        """Sets the value of the progress bar

        :param value: Value to be set on the progress bar
        :type value: float
        """
        if self.progress_dialog and not self.processing_cancelled:
            try:
                self.progress_dialog.update_progress_bar(int(value))
            except RuntimeError:
                log(tr("Error setting value to a progress bar"), notify=False)

    def update_message_bar(self, message):
        """Changes the message in the message bar item.

        :param message: Message to be updated
        :type message: str
        """
        message_bar_item = self.message_bar.createMessage(message)
        self.message_bar.pushWidget(message_bar_item, Qgis.Info)

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
            extent_list[0], extent_list[2], extent_list[1], extent_list[3]
        )
        zoom_extent = QgsRectangle(
            extent_list[0] - 0.5, extent_list[2], extent_list[1] + 0.5, extent_list[3]
        )

        canvas_crs = map_canvas.mapSettings().destinationCrs()
        original_crs = QgsCoordinateReferenceSystem("EPSG:4326")

        if canvas_crs.authid() != original_crs.authid():
            zoom_extent = self.transform_extent(zoom_extent, original_crs, canvas_crs)
            default_extent = self.transform_extent(
                default_extent, original_crs, canvas_crs
            )

        aoi = QgsRubberBand(iface.mapCanvas(), QgsWkbTypes.PolygonGeometry)

        aoi.setFillColor(QtGui.QColor(0, 0, 0, 0))
        aoi.setStrokeColor(QtGui.QColor(88, 128, 8))
        aoi.setWidth(3)
        aoi.setLineStyle(QtCore.Qt.DashLine)

        geom = QgsGeometry.fromRect(default_extent)

        aoi.setToGeometry(geom, canvas_crs)

        map_canvas.setExtent(zoom_extent)
        map_canvas.refresh()

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
            extent_list[0], extent_list[2], extent_list[1], extent_list[3]
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
            self.implementation_model_widget.can_show_error_messages = True
            self.implementation_model_widget.load()

        elif index == 2:
            # Validate implementation model selection
            selected_implementation_models = (
                self.implementation_model_widget.selected_im_items()
            )
            if len(selected_implementation_models) == 0:
                msg = self.tr("Please select at least one implementation model.")
                self.show_message(msg)
                self.tab_widget.setCurrentIndex(1)

            else:
                self.message_bar.clearWidgets()

    def open_settings(self):
        """Options the CPLUS settings in the QGIS options dialog."""
        self.iface.showOptionsDialog(currentPage=OPTIONS_TITLE)

    def run_report(self):
        """Run report generation. This should be called after the
        analysis is complete.
        """
        if self.processing_cancelled:
            # Will not proceed if processing has been cancelled by the user
            return

        if self.scenario_result is None:
            log(
                "Cannot run report generation, scenario result is " "not defined",
                info=False,
            )
            return

        self.reset_reporting_feedback()

        submit_result = self.report_manager.generate(
            self.scenario_result, self.reporting_feedback
        )
        if not submit_result.status:
            msg = self.tr("Unable to submit report request for scenario")
            self.show_message(f"{msg} {self.scenario_result.scenario.name}.")

    def on_report_running(self, scenario_id: str):
        """Slot raised when report task has started."""
        if not self.report_job_is_for_current_scenario(scenario_id):
            return

        self.progress_dialog.update_progress_bar(0)
        self.progress_dialog.report_running = True
        self.progress_dialog.change_status_message(
            tr("Generating report"), tr("scenario")
        )

    def reset_reporting_feedback(self):
        """Creates a new reporting feedback object and reconnects
        the signals.

        We are doing this to address cases where the feedback is canceled
        and the same object has to be reused for subsequent report
        generation tasks.
        """
        if self.reporting_feedback is not None:
            self.reporting_feedback.progressChanged.disconnect()

        self.reporting_feedback = QgsFeedback(self)
        self.reporting_feedback.progressChanged.connect(
            self.on_reporting_progress_changed
        )

    def on_reporting_progress_changed(self, progress: float):
        """Slot raised when the reporting progress has changed."""
        self.progress_dialog.update_progress_bar(progress)

    def on_report_finished(self, scenario_id: str):
        """Slot raised when report task has finished."""
        if not self.report_job_is_for_current_scenario(scenario_id):
            return

        self.progress_dialog.set_report_complete()
        self.progress_dialog.change_status_message(
            tr("Report generation complete"), tr("scenario")
        )
        self.run_scenario_btn.setEnabled(True)

    def report_job_is_for_current_scenario(self, scenario_id: str) -> bool:
        """Checks if the given scenario identifier is for the current
        scenario result.

        This is to ensure that signals raised by the report manager refer
        to the current scenario result object and not for old jobs.

        :param scenario_id: Scenario identifier usually from a signal
        raised by the report manager.
        :type scenario_id: str

        :returns: True if the scenario identifier matches the current
        scenario object in the results, else False.
        :rtype: bool
        """
        if self.scenario_result is None:
            return False

        current_scenario = self.scenario_result.scenario
        if current_scenario is None:
            return False

        if str(current_scenario.uuid) == scenario_id:
            return True

        return False

    def on_progress_dialog_cancelled(self):
        """Slot raised when analysis has been cancelled in progress dialog."""
        if not self.run_scenario_btn.isEnabled():
            self.run_scenario_btn.setEnabled(True)
