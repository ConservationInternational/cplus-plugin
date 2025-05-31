# -*- coding: utf-8 -*-
"""
Wizard for customizing custom activity metrics table.
"""

import os
import re
import typing

from qgis.core import Qgis, QgsFallbackNumericFormat
from qgis.gui import (
    QgsExpressionBuilderDialog,
    QgsGui,
    QgsMessageBar,
    QgsNumericFormatSelectorWidget,
)

from qgis.PyQt import QtCore, QtWidgets

from qgis.PyQt.uic import loadUiType

from ..definitions.defaults import USER_DOCUMENTATION_SITE
from ..lib.reports.metrics import (
    create_metrics_expression_context,
    create_metrics_expression_scope,
    MetricsExpressionContextGenerator,
    VAR_ACTIVITY_AREA,
)
from .metrics_builder_model import (
    ActivityColumnMetricItem,
    ActivityColumnSummaryTreeModel,
    ActivityMetricTableModel,
    COLUMN_METRIC_STR,
    CELL_METRIC_STR,
    HorizontalMoveDirection,
    MetricColumnListItem,
    MetricColumnListModel,
)
from ..models.base import Activity
from ..models.helpers import clone_activity, clone_metric_configuration_profile
from ..models.report import (
    ActivityColumnMetric,
    MetricColumn,
    MetricConfiguration,
    MetricConfigurationProfile,
    MetricProfileCollection,
    MetricType,
)
from ..utils import FileUtils, log, open_documentation, tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/activity_metrics_builder_dialog.ui")
)


class ColumnMetricItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Delegate that allows the user to choose the type of metric for a
    particular activity column.
    """

    INDEX_PROPERTY_NAME = "delegate_index"
    EXPRESSION_PROPERTY_NAME = "cell_expression"

    def createEditor(
        self,
        parent: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        idx: QtCore.QModelIndex,
    ) -> QtWidgets.QLineEdit:
        """Creates a combobox for choosing the metric type.

        :param parent: Parent widget.
        :type parent: QtWidgets.QWidget

        :param option: Options for drawing the widget in the view.
        :type option: QtWidgets.QStyleOptionViewItem

        :param idx: Location of the request in the data model.
        :type idx: QtCore.QModelIndex

        :returns: The editor widget.
        :rtype: QtWidgets.QLineEdit
        """
        metric_combobox = QtWidgets.QComboBox(parent)
        metric_combobox.setFrame(False)
        metric_combobox.setProperty(self.INDEX_PROPERTY_NAME, idx)
        metric_combobox.addItem(tr(COLUMN_METRIC_STR), MetricType.COLUMN)
        metric_combobox.addItem(tr(CELL_METRIC_STR), MetricType.CELL)
        metric_combobox.activated.connect(self.on_metric_type_changed)

        return metric_combobox

    def setEditorData(self, widget: QtWidgets.QWidget, idx: QtCore.QModelIndex):
        """Sets the data to be displayed and edited by the editor.

        :param widget: Editor widget.
        :type widget: QtWidgets.QWidget

        :param idx: Location in the data model.
        :type idx: QtCore.QModelIndex
        """
        select_index = -1

        item = idx.model().itemFromIndex(idx)
        if item is None or not isinstance(item, ActivityColumnMetricItem):
            return

        current_metric_type = item.metric_type
        if current_metric_type == MetricType.COLUMN:
            select_index = widget.findData(MetricType.COLUMN)
        elif current_metric_type == MetricType.CELL:
            select_index = widget.findData(MetricType.CELL)

        if select_index != -1:
            # We are temporarily blocking the index changed slot
            # so that the expression dialog will not be shown if
            # the metric type is cell-based.
            widget.blockSignals(True)
            widget.setCurrentIndex(select_index)
            widget.blockSignals(False)

    def on_metric_type_changed(self, index: int):
        """Slot raised when the metric type has changed.

        We use this to load the expression builder if a
        cell metric is selected.

        :param index: Index of the current selection.
        :type index: int
        """
        if index == -1:
            return

        editor = self.sender()
        metric_type = editor.itemData(index)
        if metric_type != MetricType.CELL:
            return

        model_index = editor.property(self.INDEX_PROPERTY_NAME)
        if not model_index.isValid():
            log(tr("Invalid index for activity column metric."))
            return

        activity_column_metric_item = model_index.model().itemFromIndex(model_index)
        if activity_column_metric_item is None:
            log(tr("Activity column metric could not be found."))
            return

        expression_builder = QgsExpressionBuilderDialog(
            None,
            activity_column_metric_item.expression,
            editor,
            "CPLUS",
            create_metrics_expression_context(),
        )
        expression_builder.setWindowTitle(tr("Activity Column Expression Builder"))
        if expression_builder.exec_() == QtWidgets.QDialog.Accepted:
            # Save the expression for use when persisting in the model
            editor.setProperty(
                self.EXPRESSION_PROPERTY_NAME, expression_builder.expressionText()
            )

        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QtWidgets.QAbstractItemDelegate.NoHint)

    def setModelData(
        self,
        widget: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        idx: QtCore.QModelIndex,
    ):
        """Gets data from the editor widget and stores it in the specified
        model at the item index.

        :param widget: Editor widget.
        :type widget: QtWidgets.QWidget

        :param model: Model to store the editor data in.
        :type model: QtCore.QAbstractItemModel

        :param idx: Location in the data model.
        :type idx: QtCore.QModelIndex
        """
        metric_type = widget.itemData(widget.currentIndex())
        item = idx.model().itemFromIndex(idx)
        if item is None or not isinstance(item, ActivityColumnMetricItem):
            return

        expression = ""
        if metric_type == MetricType.COLUMN:
            # Inherit the column expression if defined
            metric_column = model.metric_column(idx.column() - 1)
            if metric_column is not None:
                expression = metric_column.expression
        elif metric_type == MetricType.CELL:
            expression = widget.property(self.EXPRESSION_PROPERTY_NAME)

        item.update_metric_type(metric_type, expression)

    def updateEditorGeometry(
        self,
        widget: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        idx: QtCore.QModelIndex,
    ):
        """Updates the geometry of the editor for the item with the given index,
        according to the rectangle specified in the option.

        :param widget: Widget whose geometry will be updated.
        :type widget: QtWidgets.QWidget

        :param option: Option containing the rectangle for
        updating the widget.
        :type option: QtWidgets.QStyleOptionViewItem

        :param idx: Location of the widget in the data model.
        :type idx: QtCore.QModelIndex
        """
        widget.setGeometry(option.rect)


class ActivityMetricsBuilder(QtWidgets.QWizard, WidgetUi):
    """Wizard for customizing custom activity metrics table."""

    AREA_COLUMN = "Area"
    MAX_COLUMNS = 10

    def __init__(
        self,
        parent=None,
        activities=None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        self._activities = []
        if activities is not None:
            self._activities = [clone_activity(activity) for activity in activities]

        self._profile_collection = None

        # Setup notification bars
        self._column_message_bar = QgsMessageBar()
        self.vl_column_notification.addWidget(self._column_message_bar)

        self._activity_metric_message_bar = QgsMessageBar()
        self.vl_metric_notification.addWidget(self._activity_metric_message_bar)

        self._column_list_model = MetricColumnListModel()
        self._activity_metric_table_model = ActivityMetricTableModel()
        self._summary_model = ActivityColumnSummaryTreeModel()

        # Initialize wizard
        ci_icon = FileUtils.get_icon("cplus_logo.svg")
        ci_pixmap = ci_icon.pixmap(64, 64)
        self.setPixmap(QtWidgets.QWizard.LogoPixmap, ci_pixmap)

        help_button = self.button(QtWidgets.QWizard.HelpButton)
        help_icon = FileUtils.get_icon("mActionHelpContents_green.svg")
        help_button.setIcon(help_icon)

        self.currentIdChanged.connect(self.on_page_id_changed)
        self.helpRequested.connect(self.on_help_requested)
        self.accepted.connect(self.on_accepted)

        # Intro page
        banner = FileUtils.get_pixmap("metrics_illustration.svg")
        self.lbl_banner.setPixmap(banner)
        self.lbl_banner.setScaledContents(True)

        # Columns page
        add_icon = FileUtils.get_icon("symbologyAdd.svg")
        self.btn_add_column.setIcon(add_icon)
        self.btn_add_column.clicked.connect(self.on_add_column)

        remove_icon = FileUtils.get_icon("symbologyRemove.svg")
        self.btn_delete_column.setIcon(remove_icon)
        self.btn_delete_column.setEnabled(False)
        self.btn_delete_column.clicked.connect(self.on_remove_column)

        move_up_icon = FileUtils.get_icon("mActionArrowUp.svg")
        self.btn_column_up.setIcon(move_up_icon)
        self.btn_column_up.setEnabled(False)
        self.btn_column_up.clicked.connect(self.on_move_up_column)

        move_down_icon = FileUtils.get_icon("mActionArrowDown.svg")
        self.btn_column_down.setIcon(move_down_icon)
        self.btn_column_down.setEnabled(False)
        self.btn_column_down.clicked.connect(self.on_move_down_column)

        # Profile management
        self.cbo_profile.currentIndexChanged.connect(self.on_profile_changed)

        self.btn_add_profile.setIcon(add_icon)
        self.btn_add_profile.clicked.connect(self.on_add_profile)

        edit_icon = FileUtils.get_icon("mActionToggleEditing.svg")
        self.btn_rename_profile.setIcon(edit_icon)
        self.btn_rename_profile.clicked.connect(self.on_rename_profile)

        copy_icon = FileUtils.get_icon("mActionEditCopy.svg")
        self.btn_copy_profile.setIcon(copy_icon)
        self.btn_copy_profile.clicked.connect(self.on_copy_profile)

        self.btn_delete_profile.setIcon(remove_icon)
        self.btn_delete_profile.clicked.connect(self.on_delete_profile)

        self.splitter.setStretchFactor(0, 20)
        self.splitter.setStretchFactor(1, 80)

        self.cbo_column_expression.setAllowEmptyFieldName(True)
        self.cbo_column_expression.setAllowEvalErrors(False)
        self.cbo_column_expression.setExpressionDialogTitle(
            tr("Column Expression Builder")
        )
        self._metrics_context_generator = MetricsExpressionContextGenerator()
        self.cbo_column_expression.registerExpressionContextGenerator(
            self._metrics_context_generator
        )

        self.lst_columns.setModel(self._column_list_model)
        self.lst_columns.selectionModel().selectionChanged.connect(
            self.on_column_selection_changed
        )

        self.txt_column_name.textChanged.connect(self._on_column_header_changed)
        self.cbo_column_alignment.currentIndexChanged.connect(
            self._on_column_alignment_changed
        )
        self.cbo_column_expression.fieldChanged.connect(
            self._on_column_expression_changed
        )

        self.column_properties_widget.setDockMode(True)
        self.column_properties_stack.setMainPanel(self.column_properties_widget)

        self.chk_format_number.toggled.connect(self.on_format_number_checked)
        self.btn_customize_number.clicked.connect(self.on_customize_number)

        self.chk_format_number.setChecked(False)

        # Activity metrics page
        self.tb_activity_metrics.setModel(self._activity_metric_table_model)

        # Update activities if specified
        self._update_activities()

        self.tb_activity_metrics.installEventFilter(self)

        # Final summary page
        self.tv_summary.setModel(self._summary_model)

    @property
    def profile_collection(self) -> MetricProfileCollection:
        """Gets the profile collection used in the wizard.

        :returns: The profile collection used in the wizard.
        :rtype: MetricProfileCollection
        """
        return self._profile_collection

    @profile_collection.setter
    def profile_collection(self, collection: MetricProfileCollection):
        """Set the profile collection to use in the wizard.

        :param collection: Metric profile collection.
        :type collection: MetricProfileCollection
        """
        if not collection.profiles:
            # Initialize defaults
            self.initialize_collection()
            return

        self.clear_views()

        self._profile_collection = collection

        self.cbo_profile.blockSignals(True)
        current_profile = self._profile_collection.get_current_profile()
        for profile in self._profile_collection.profiles:
            self.cbo_profile.addItem(profile.name, profile.id)
            if current_profile is None:
                current_profile = profile

        self.cbo_profile.blockSignals(False)

        if current_profile is not None:
            self.set_current_profile(current_profile.id)

    def clear_views(self):
        """Removes items in item views i.e. combobox, list and table items."""
        self.cbo_profile.clear()

        self.clear_columns()

    def clear_columns(self):
        """Remove columns from the UI list model."""
        # Remove columns
        while self._column_list_model.rowCount() > 0:
            column_name = self._column_list_model.column_items[0].name
            self.remove_column(column_name)

    def initialize_collection(self):
        """Creates an initial profile collection. Use this if None is
        specified.
        """
        # Add a default area column
        area_metric_column = MetricColumn.create_default_column(
            self.AREA_COLUMN, tr("Area (Ha)"), f"@{VAR_ACTIVITY_AREA}"
        )
        area_metric_column.auto_calculated = True
        area_metric_column.format_as_number = True

        column_metrics = []
        for activity in self._activities:
            activity_column_metric = ActivityColumnMetric(
                activity,
                area_metric_column,
                MetricType.COLUMN,
                area_metric_column.expression,
            )
            column_metrics.append([activity_column_metric])

        default_configuration = MetricConfiguration(
            [area_metric_column], column_metrics
        )

        # Create a default profile
        default_metric_profile = MetricConfigurationProfile(
            tr("Default"), default_configuration
        )

        self._profile_collection = MetricProfileCollection()
        self._profile_collection.add_profile(default_metric_profile)
        self.cbo_profile.blockSignals(True)
        self.cbo_profile.addItem(default_metric_profile.name, default_metric_profile.id)
        self.cbo_profile.blockSignals(False)
        self.set_current_profile(default_metric_profile.id)

    def set_current_profile(
        self, profile: typing.Union[str, MetricConfigurationProfile]
    ):
        """Updates the UI to set the current metric profile.

        :param profile: Profile or profile ID to be set. It must
        exist in the profile collection.
        :type profile: typing.Union[str, MetricConfigurationProfile]
        """
        if self._profile_collection is None:
            return

        # Convert profile to corresponding ID
        if isinstance(profile, MetricConfigurationProfile):
            profile = profile.id

        if not self._profile_collection.profile_exists(profile):
            return

        metric_profile = self._profile_collection.get_profile(profile)
        if metric_profile is None:
            return

        # Update combobox
        item_index = self.cbo_profile.findData(profile)
        if item_index == -1:
            return

        self.cbo_profile.blockSignals(True)
        self.cbo_profile.setCurrentIndex(item_index)
        self.cbo_profile.blockSignals(False)

        # Clear columns
        self.clear_columns()

        # Load configuration in the view
        self.load_configuration(metric_profile.config)

        # Set the current profile
        self._profile_collection.current_profile = profile

    @property
    def column_list_model(self) -> MetricColumnListModel:
        """Gets the columns list model used in the wizard.

        :returns: The columns list model used in the model.
        :rtype: MetricColumnListModel
        """
        return self._column_list_model

    @property
    def activity_table_model(self) -> ActivityMetricTableModel:
        """Gets the activity table model used to show the metric for
        each activity and column.

        :returns: The activity table model.
        :rtype: ActivityMetricTableModel
        """
        return self._activity_metric_table_model

    @property
    def activities(self) -> typing.List[Activity]:
        """Gets the activities in the model.

        :returns: All the activities in the model.
        :rtype:
        """
        return self._activities

    @activities.setter
    def activities(self, activities: typing.List[Activity]):
        """Sets the activities to be used in the model.

        :param activities: Activities to be used in the model i.e.
        those whose metrics will be used in the customization.
        :type activities: typing.List[Activity]
        """
        self._activities = [clone_activity(activity) for activity in activities]
        self._update_activities()

    @property
    def metric_configuration(self) -> MetricConfiguration:
        """Gets the user configuration for metric column and
        corresponding cell metric configuration.

        :returns: User metric configuration.
        :rtype: MetricConfiguration
        """
        return MetricConfiguration(
            self._activity_metric_table_model.metric_columns,
            self._activity_metric_table_model.models,
        )

    def load_configuration(self, configuration: MetricConfiguration):
        """Load a metric configuration.

        All the columns in the configuration will be loaded, with an attempt
        to restore the metric configuration of similar activities that
        existed in the configuration with those currently being configured.

        :param configuration: Configuration containing mapping of metric
        columns and cell metrics.
        :type configuration: MetricConfiguration
        """
        if configuration is None:
            return

        if not configuration.is_valid():
            log("Metric configuration is invalid and cannot be loaded.")
            return

        # Add metric columns
        for mc in configuration.metric_columns:
            # Do not add a column with a similar name
            if self._column_list_model.column_exists(mc.name):
                continue

            item = MetricColumnListItem(mc)
            self.add_column_item(item)

        # Configure activity cell metrics matching the same activity
        # and column name in the configuration
        for r in range(self._activity_metric_table_model.rowCount()):
            for c in range(1, self._activity_metric_table_model.columnCount()):
                item = self._activity_metric_table_model.item(r, c)
                # Fetch the closest match in configuration (based on activity
                # ID and name or header label)
                model_match = configuration.find(
                    str(item.model.activity.uuid), item.model.metric_column.name
                )
                if model_match is None:
                    continue

                item.update_metric_type(model_match.metric_type, model_match.expression)

    def on_page_id_changed(self, page_id: int):
        """Slot raised when the page ID changes.

        :param page_id: ID of the new page.
        :type page_id: int
        """
        # Update title
        window_title = (
            f"{tr('Activity Metrics Wizard')} - "
            f"{tr('Step')} {page_id + 1} {tr('of')} "
            f"{len(self.pageIds())!s}"
        )
        self.setWindowTitle(window_title)

        # Activity metrics page
        if page_id == 2:
            # If expression is not specified for at
            # least one column then enable the groupbox.
            group_box_checked = False
            self.gb_custom_activity_metric.setChecked(group_box_checked)
            for item in self._column_list_model.column_items:
                if (
                    not item.expression
                    and not self.gb_custom_activity_metric.isChecked()
                ):
                    group_box_checked = True
                    break

            self.gb_custom_activity_metric.setChecked(group_box_checked)

        # Final summary page
        elif page_id == 3:
            self.load_summary_details()

    def validateCurrentPage(self) -> bool:
        """Validates the current page.

        :returns: True if the current page is valid, else False.
        :rtype: bool
        """
        # Columns page
        if self.currentId() == 1:
            # Save latest changes in current profile
            self.update_current_profile()
            return self.is_columns_page_valid()

        elif self.currentId() == 2:
            return self.is_activity_metrics_page_valid()

        return True

    def on_help_requested(self):
        """Slot raised when the help button has been clicked.

        Opens the online help documentation in the user's browser.
        """
        open_documentation(USER_DOCUMENTATION_SITE)

    def on_customize_number(self):
        """Slot raised to customize number formatting options."""
        format_selector = QgsNumericFormatSelectorWidget(self.column_properties_widget)
        format_selector.setPanelTitle(tr("Number Formatter"))
        format_selector.changed.connect(self._on_number_format_changed)

        # Get current column item
        current_columns_items = self.selected_column_items()
        if len(current_columns_items) > 0:
            number_formatter = current_columns_items[0].number_formatter
            format_selector.setFormat(number_formatter)

        self.column_properties_widget.openPanel(format_selector)

    def _on_number_format_changed(self):
        """Slot raised whenever the number format configuration has changed."""
        format_selector = self.sender()
        if format_selector is None:
            return

        selected_columns = self.selected_column_items()
        if len(selected_columns) == 0:
            return

        number_formatter = format_selector.format()

        current_column = selected_columns[0]
        current_column.number_formatter = number_formatter

        # Update column properties in activity metrics table
        self._activity_metric_table_model.update_column_properties(
            current_column.row(), current_column.model
        )

    def on_format_number_checked(self, checked: bool):
        """Slot raised when the format number checkbox has been
        checked or unchecked.

        :param checked: True if checked or False if unchecked.
        :type checked: bool
        """
        self.btn_customize_number.setEnabled(checked)
        self.save_column_properties()

    def clear_activities(self):
        """Removes all activities in the activity metrics table."""
        self._activity_metric_table_model.removeRows(
            0, self._activity_metric_table_model.rowCount()
        )

    def _update_activities(self):
        """Update the list of activities in the activity metrics
        table.

        Clears any existing activities.
        """
        self.clear_activities()

        for activity in self.activities:
            self._activity_metric_table_model.append_activity(activity)

    def push_column_message(
        self,
        message: str,
        level: Qgis.MessageLevel = Qgis.MessageLevel.Warning,
        clear_first: bool = False,
    ):
        """Push a message to the notification bar in the
        columns wizard page.

        :param message: Message to the show in the notification bar.
        :type message: str

        :param level: Severity of the message. Warning is the default.
        :type level: Qgis.MessageLevel

        :param clear_first: Clear any current messages in the notification
        bar, default is False.
        :type clear_first: bool
        """
        if clear_first:
            self._column_message_bar.clearWidgets()

        self._column_message_bar.pushMessage(message, level, 5)

    def push_activity_metric_message(
        self,
        message: str,
        level: Qgis.MessageLevel = Qgis.MessageLevel.Warning,
        clear_first: bool = False,
    ):
        """Push a message to the notification bar in the
        activity metric wizard page.

        :param message: Message to the show in the notification bar.
        :type message: str

        :param level: Severity of the message. Warning is the default.
        :type level: Qgis.MessageLevel

        :param clear_first: Clear any current messages in the notification
        bar, default is False.
        :type clear_first: bool
        """
        if clear_first:
            self._activity_metric_message_bar.clearWidgets()

        self._activity_metric_message_bar.pushMessage(message, level, 5)

    def on_add_column(self):
        """Slot raised to add a new column."""
        if not self.can_add_new_column():
            QtWidgets.QMessageBox.warning(
                self,
                tr("Columns Limit"),
                tr("Maximum number of columns reached."),
            )
            return

        label_text = (
            f"{tr('Specify the name of the column.')}<br>"
            f"<i><sup>*</sup>{tr('Any special characters will be removed.')}"
            f"</i>"
        )
        column_name, ok = QtWidgets.QInputDialog.getText(
            self,
            tr("Set Column Name"),
            label_text,
        )

        if ok and column_name:
            # Remove special characters
            clean_column_name = re.sub("\W+", " ", column_name)
            column_exists = self._column_list_model.column_exists(clean_column_name)
            if column_exists:
                QtWidgets.QMessageBox.warning(
                    self,
                    tr("Duplicate Column Name"),
                    tr("There is an already existing column name."),
                )
                return

            column_item = MetricColumnListItem(clean_column_name)
            # Set default number formatter; can always be changed
            column_item.number_formatter = MetricColumn.default_formatter()
            self.add_column_item(column_item)

    def can_add_new_column(self) -> bool:
        """Checks if the maximum limit has been reached.

        :returns: True if the limit has not been reached else
        False if MAX_COLUMNS has been reached.
        :rtype: bool
        """
        return len(self._column_list_model.column_items) < self.MAX_COLUMNS

    def add_column_item(self, item: MetricColumnListItem):
        """Adds a metric column item.

        If there is a column with a similar name, the item
        will not be added.

        :param item: Metrics column item to be added.
        :type item: MetricColumnListItem
        """
        # Check if the maximum limit has been reached
        if not self.can_add_new_column():
            log("Maximum number of columns reached.", info=False)
            return

        # Check if there are items with a similar name
        if self._column_list_model.column_exists(item.name):
            return

        self._column_list_model.add_column(item)

        # Select item
        self.select_column(item.row())

        # Add column to activity metrics table
        self._activity_metric_table_model.append_column(item.model)
        self.resize_activity_table_columns()

        if not item.model.auto_calculated:
            self.tb_activity_metrics.setItemDelegateForColumn(
                item.row() + 1, ColumnMetricItemDelegate(self.tb_activity_metrics)
            )

    def on_remove_column(self):
        """Slot raised to remove the selected column."""
        selected_items = self.selected_column_items()
        for item in selected_items:
            self.remove_column(item.name)

        self.resize_activity_table_columns()

    def remove_column(self, name: str):
        """Remove a metric column with the given name.

        :param name: Name of the metric column to be removed.
        :type name: str
        """
        item = self._column_list_model.item_from_name(name)
        if item is None:
            return

        index = item.row()

        self._column_list_model.remove_column(name)

        # Remove corresponding column in activity metrics table
        self._activity_metric_table_model.remove_column(index)

    def on_move_up_column(self):
        """Slot raised to move the selected column one level up."""
        selected_items = self.selected_column_items()
        if len(selected_items) == 0:
            return

        item = selected_items[0]
        current_row = item.row()
        row = self._column_list_model.move_column_up(current_row)
        if row == -1:
            return

        # Maintain selection
        self.select_column(row)

        # Move corresponding column in the activity metrics table.
        # We have normalized it to reflect the position in the
        # metrics table.
        reference_index = current_row + 1
        self._move_activity_metric_column(reference_index, HorizontalMoveDirection.LEFT)

    def _move_activity_metric_column(
        self, reference_index: int, direction: HorizontalMoveDirection
    ):
        """Moves the activity column metric at the given index
        depending on the direction.

        :param reference_index: Location of the reference column
        that will be moved.
        :type reference_index: int

        :param direction: Direction the reference column will
        be moved.
        :type direction: HorizontalMoveDirection
        """
        if direction == HorizontalMoveDirection.LEFT:
            adjacent_index = reference_index - 1
        else:
            adjacent_index = reference_index + 1

        reference_delegate = self.tb_activity_metrics.itemDelegateForColumn(
            reference_index
        )
        adjacent_delegate = self.tb_activity_metrics.itemDelegateForColumn(
            adjacent_index
        )

        if direction == HorizontalMoveDirection.LEFT:
            new_index = self._activity_metric_table_model.move_column_left(
                reference_index
            )
        else:
            new_index = self._activity_metric_table_model.move_column_right(
                reference_index
            )

        if new_index != -1:
            if direction == HorizontalMoveDirection.LEFT:
                adjacent_new_index = new_index + 1
            else:
                adjacent_new_index = new_index - 1

            # Also adjust the delegates
            self.tb_activity_metrics.setItemDelegateForColumn(
                new_index, reference_delegate
            )
            self.tb_activity_metrics.setItemDelegateForColumn(
                adjacent_new_index, adjacent_delegate
            )

    def on_move_down_column(self):
        """Slot raised to move the selected column one level down."""
        selected_items = self.selected_column_items()
        if len(selected_items) == 0:
            return

        item = selected_items[0]
        current_row = item.row()
        row = self._column_list_model.move_column_down(current_row)
        if row == -1:
            return

        # Maintain selection
        self.select_column(row)

        # Move corresponding column in the activity metrics table.
        # We have normalized it to reflect the position in the
        # metrics table.
        reference_index = current_row + 1
        self._move_activity_metric_column(
            reference_index, HorizontalMoveDirection.RIGHT
        )

    def on_profile_changed(self, index: int):
        """Slot raised when the profile has changed.

        :param index: Index of the current profile.
        :type index: int
        """
        if index == -1:
            return

        profile_id = self.cbo_profile.itemData(index)
        if not profile_id:
            return

        self.update_current_profile()

        self.set_current_profile(profile_id)

    def update_current_profile(self):
        """Saves the current profile to the profile collection."""
        current_profile = self._profile_collection.get_current_profile()
        if current_profile is None:
            return

        # Update metric config as per setup in the UI
        current_profile.config = self.metric_configuration

    def _profile_name_dialog(
        self, dialog_title, initial_text: str = ""
    ) -> typing.Tuple[str, bool]:
        """Creates a dialog for specifying the profile name with
        an optional initial value.

        :param dialog_title: Dialog title.
        :type dialog_title: str

        :param initial_text: Optional text to include in
        the dialog when shown.
        :type initial_text: str

        :returns: A tuple containing the specified input text and True or
        False if the dialog was accepted or rejected respectively.
        :rtype: typing.Tuple[str, bool]
        """
        label_text = (
            f"{tr('Specify the name of the profile.')}<br>"
            f"<i><sup>*</sup>{tr('Any special characters will be removed.')}"
            f"</i>"
        )
        return QtWidgets.QInputDialog.getText(
            self, dialog_title, label_text, text=initial_text
        )

    @staticmethod
    def clean_profile_name(profile_name: str) -> str:
        """Remove special characters from profile name.

        :param profile_name: The raw profile name
        :type profile_name: str
        :returns: Cleaned profile name with special characters removed
        :rtype: str
        """
        return re.sub(r"\W+", " ", profile_name)

    def check_duplicate_profile_name(self, clean_profile_name: str) -> bool:
        """Check if a profile name already exists.

        :param clean_profile_name: The cleaned profile name to check
        :type clean_profile_name: str
        :returns: True if duplicate exists, False otherwise
        :rtype: bool
        """
        tr_msg = tr("There is an already existing profile with the name")
        if clean_profile_name in self.profile_collection.identifiers.values():
            QtWidgets.QMessageBox.warning(
                self,
                tr("Duplicate Profile Name"),
                f"{tr_msg} '{clean_profile_name}'",
            )
            return True

        return False

    def _get_validated_profile_name(
        self, dialog_title, initial_text: str = ""
    ) -> typing.Optional[str]:
        """Get a validated profile name from user input.

        :param dialog_title: Dialog title.
        :type dialog_title: str

        :param initial_text: Optional initial text for the dialog
        :type initial_text: str
        :returns: Clean profile name if valid, None if cancelled or duplicate
        :rtype: typing.Optional[str]
        """
        profile_name, ok = self._profile_name_dialog(dialog_title, initial_text)

        # Cancelled
        if not ok:
            return None

        # No text provided
        if ok and not profile_name:
            QtWidgets.QMessageBox.warning(
                self,
                dialog_title,
                tr("Profile name cannot be empty"),
            )
            return None

        clean_profile_name = self.clean_profile_name(profile_name)

        if self.check_duplicate_profile_name(clean_profile_name):
            return None

        return clean_profile_name

    def on_add_profile(self):
        """Slot to add a new profile."""
        clean_profile_name = self._get_validated_profile_name(tr("Add New Profile"))

        if clean_profile_name is None:
            return

        metric_profile = MetricConfigurationProfile(
            clean_profile_name, MetricConfiguration.create()
        )

        if not self._profile_collection.add_profile(metric_profile):
            QtWidgets.QMessageBox.warning(
                self,
                tr("Add New Profile"),
                tr(
                    "Profile could not be added. Check for a "
                    "duplicate name or an invalid profile"
                ),
            )
            return

        # Save any changes to the profile the user was working
        self.update_current_profile()

        self.cbo_profile.addItem(clean_profile_name, metric_profile.id)
        self.set_current_profile(metric_profile.id)

    def on_rename_profile(self):
        """Slot to rename the current profile."""
        current_profile = self._profile_collection.get_current_profile()
        if current_profile is None:
            QtWidgets.QMessageBox.warning(
                self,
                tr("Rename Profile"),
                tr("Please select a profile to rename."),
            )
            return

        clean_profile_name = self._get_validated_profile_name(
            tr("Rename Profile"), current_profile.name
        )
        if clean_profile_name is None:
            return

        # Update UI
        current_index = self.cbo_profile.currentIndex()
        self.cbo_profile.setItemText(current_index, clean_profile_name)

        # Update profile name
        current_profile.name = clean_profile_name
        self.cbo_profile.setItemData(current_index, current_profile.id)

        # Update profile collection
        self._profile_collection.current_profile = current_profile.id
        self.update_current_profile()

    def on_delete_profile(self):
        """Slot to delete the current profile."""
        # Check to ensure that at least one profile
        # exists in the collection
        if len(self._profile_collection.profiles) == 1:
            QtWidgets.QMessageBox.warning(
                self,
                tr("Delete Profile"),
                tr("Cannot delete as at least one metric profile must exist."),
            )
            return

        current_index = self.cbo_profile.currentIndex()
        current_profile_id = self.cbo_profile.itemData(current_index)
        if not current_profile_id or not self._profile_collection.remove_profile(
            current_profile_id
        ):
            QtWidgets.QMessageBox.warning(
                self,
                tr("Delete Profile"),
                tr("An error occurred in attempting to delete the current profile."),
            )
            return

        self.cbo_profile.removeItem(current_index)

        # Set last profile in the collection as the current profile
        last_profile_id = self._profile_collection.profiles[-1].id
        self.set_current_profile(last_profile_id)

    def on_copy_profile(self):
        """Slot to copy the current profile."""
        current_profile = self._profile_collection.get_current_profile()
        if current_profile is None:
            QtWidgets.QMessageBox.warning(
                self,
                tr("Copy Profile"),
                tr("Please select a profile to copy"),
            )
            return

        # Check validity
        if not current_profile.is_valid():
            QtWidgets.QMessageBox.warning(
                self,
                tr("Copy Profile"),
                tr("The current profile cannot be copied as it is invalid"),
            )
            return

        clean_profile_name = self._get_validated_profile_name(
            tr("Copy Profile"), f"{current_profile.name} {tr('Copy')}"
        )
        if clean_profile_name is None:
            return

        # Save any changes before cloning
        self.update_current_profile()

        cloned_profile = clone_metric_configuration_profile(
            current_profile, self._activities
        )
        if cloned_profile is None:
            QtWidgets.QMessageBox.warning(
                self,
                tr("Copy Profile"),
                tr("Unable to copy the current profile"),
            )
            return

        # Update the name then add it to the collection
        cloned_profile.name = clean_profile_name
        if not self._profile_collection.add_profile(cloned_profile):
            QtWidgets.QMessageBox.warning(
                self,
                tr("Copy Profile"),
                tr(
                    "Copied profile could not be added. Check for a "
                    "duplicate name or an invalid profile"
                ),
            )
            return

        self.cbo_profile.addItem(clean_profile_name, cloned_profile.id)
        self.set_current_profile(cloned_profile.id)

    def select_column(self, row: int):
        """Select the column item in the specified row.

        :param row: Column item in the specified row number to be selected.
        :type row: int
        """
        index = self._column_list_model.index(row, 0)
        if not index.isValid():
            return

        selection_model = self.lst_columns.selectionModel()
        selection_model.select(index, QtCore.QItemSelectionModel.ClearAndSelect)

    def load_column_properties(self, column_item: MetricColumnListItem):
        """Load the properties of the column item in the corresponding
        UI controls.

        :param column_item: Column item whose properties are to be loaded.
        :type column_item: MetricColumnListItem
        """
        # Set column properties
        self.txt_column_name.blockSignals(True)
        self.txt_column_name.setText(column_item.header)
        self.txt_column_name.blockSignals(False)

        # Load alignment options
        self.cbo_column_alignment.blockSignals(True)

        self.cbo_column_alignment.clear()

        left_icon = FileUtils.get_icon("mIconAlignLeft.svg")
        self.cbo_column_alignment.addItem(left_icon, tr("Left"), QtCore.Qt.AlignLeft)

        right_icon = FileUtils.get_icon("mIconAlignRight.svg")
        self.cbo_column_alignment.addItem(right_icon, tr("Right"), QtCore.Qt.AlignRight)

        center_icon = FileUtils.get_icon("mIconAlignCenter.svg")
        self.cbo_column_alignment.addItem(
            center_icon, tr("Center"), QtCore.Qt.AlignHCenter
        )

        justify_icon = FileUtils.get_icon("mIconAlignJustify.svg")
        self.cbo_column_alignment.addItem(
            justify_icon, tr("Justify"), QtCore.Qt.AlignJustify
        )

        alignment_index = self.cbo_column_alignment.findData(column_item.alignment)
        if alignment_index != -1:
            self.cbo_column_alignment.setCurrentIndex(alignment_index)

        self.cbo_column_alignment.blockSignals(False)

        self.cbo_column_expression.blockSignals(True)

        if column_item.auto_calculated:
            self.cbo_column_expression.setEnabled(False)
        else:
            self.cbo_column_expression.setEnabled(True)

        self.cbo_column_expression.setExpression(column_item.expression)

        self.cbo_column_expression.blockSignals(False)

        self.chk_format_number.blockSignals(True)
        self.chk_format_number.setChecked(column_item.format_as_number)
        self.chk_format_number.blockSignals(False)

    def clear_column_properties(self):
        """Clear widget values for column properties."""
        self.txt_column_name.clear()
        self.cbo_column_alignment.clear()
        self.cbo_column_expression.setExpression("")

    def on_column_selection_changed(
        self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection
    ):
        """Slot raised when selection in the columns view has changed.

        :param selected: Current item selection.
        :type selected: QtCore.QItemSelection

        :param deselected: Previously selected items that have been
        deselected.
        :type deselected: QtCore.QItemSelection
        """
        self.btn_delete_column.setEnabled(True)
        self.btn_column_up.setEnabled(True)
        self.btn_column_down.setEnabled(True)

        # Close any open panels
        self.column_properties_stack.acceptAllPanels()

        selected_columns = self.selected_column_items()
        if len(selected_columns) != 1:
            self.btn_delete_column.setEnabled(False)
            self.btn_column_up.setEnabled(False)
            self.btn_column_down.setEnabled(False)

            self.clear_column_properties()

        else:
            # List view is set to single selection hence this
            # condition will be for one item selected.
            self.load_column_properties(selected_columns[0])

    def selected_column_items(self) -> typing.List[MetricColumnListItem]:
        """Returns the selected column items in the column list view.

        :returns: A collection of the selected column items.
        :rtype: list
        """
        selection_model = self.lst_columns.selectionModel()
        idxs = selection_model.selectedRows()

        return [self._column_list_model.item(idx.row()) for idx in idxs]

    def _on_column_header_changed(self, header: str):
        """Slot raised when the header label has changed.

        :param header: New header label text.
        :type header: str
        """
        self.save_column_properties()

    def _on_column_alignment_changed(self, index: int):
        """Slot raised when the column alignment has changed.

        :param index: Current index of the selected alignment.
        :type index: int
        """
        self.save_column_properties()

    def _on_column_expression_changed(self, field_name: str):
        """Slot raised when the column expression changes.

        :param field_name: The field that has changed.
        :type field_name: str
        """
        self.save_column_properties()

    def save_column_properties(self):
        """Updates the properties of the metric column based on the
        values of the UI controls for the current selected column
        item.
        """
        selected_columns = self.selected_column_items()
        if len(selected_columns) == 0:
            return

        current_column = selected_columns[0]
        current_column.header = self.txt_column_name.text()
        current_column.alignment = self.cbo_column_alignment.itemData(
            self.cbo_column_alignment.currentIndex()
        )
        current_column.expression = self.cbo_column_expression.expression()
        current_column.format_as_number = self.chk_format_number.isChecked()
        if not current_column.format_as_number:
            current_column.number_formatter = QgsFallbackNumericFormat()

        # Update column properties in activity metrics table
        self._activity_metric_table_model.update_column_properties(
            current_column.row(), current_column.model
        )

    def is_columns_page_valid(self) -> bool:
        """Validates the columns page.

        :returns: True if the columns page is valid, else False.
        :rtype: bool
        """
        self._column_message_bar.clearWidgets()

        if self._column_list_model.rowCount() == 0:
            self.push_column_message(
                tr(
                    "At least one column is required to use in the activity "
                    "metrics table."
                )
            )
            return False

        else:
            # Check other profiles
            zero_column_profiles = []
            for profile in self._profile_collection.profiles:
                if not profile.config.metric_columns:
                    zero_column_profiles.append(profile.name)

            if zero_column_profiles:
                msg_tr = tr("At least one column is required in the following profiles")
                self.push_column_message(f"{msg_tr}: {', '.join(zero_column_profiles)}")
                return False

        # Check column headers start with current profile then other profiles
        is_valid = True
        for item in self._column_list_model.column_items:
            if not item.is_valid:
                if is_valid:
                    is_valid = False

                tr_msg = tr("header label is empty")
                msg = f"'{item.name}' {tr_msg}."
                self.push_column_message(msg)

        if not is_valid:
            return False

        # Try other profiles if current profile is valid
        null_header_profiles = []
        for profile in self._profile_collection.profiles:
            for metric_column in profile.config.metric_columns:
                if not metric_column.header or not metric_column.name:
                    if profile.name not in null_header_profiles:
                        null_header_profiles.append(profile.name)

        if null_header_profiles:
            msg_tr = tr("The following profiles have one or more empty column headers")
            self.push_column_message(f"{msg_tr}: {', '.join(null_header_profiles)}")
            return False

        return True

    def is_activity_metrics_page_valid(self) -> bool:
        """Validates the activity metrics page.

        :returns: True if the activity metrics page is valid,
        else False.
        :rtype: bool
        """
        self._activity_metric_message_bar.clearWidgets()

        is_valid = self._activity_metric_table_model.validate(True)
        if not is_valid:
            msg = tr("The metrics for the highlighted items are undefined.")
            self.push_activity_metric_message(msg)

        return is_valid

    def eventFilter(self, observed_object: QtCore.QObject, event: QtCore.QEvent):
        """Captures events sent to specific widgets in the wizard.

        :param observed_object: Object receiving the event.
        :type observed_object: QtCore.QObject

        :param event: The specific event being received by the observed object.
        :type event: QtCore.QEvent
        """
        # Resize activity metric table columns based on the size of the table view.
        if observed_object == self.tb_activity_metrics:
            if event.type() == QtCore.QEvent.Resize:
                self.resize_activity_table_columns()

        return super().eventFilter(observed_object, event)

    def resize_activity_table_columns(self):
        """Resize column width of activity metrics table for the
        entire width to be occupied.

        Use a reasonable size if the table has only one column.
        """
        if self._activity_metric_table_model.columnCount() == 1:
            self.tb_activity_metrics.setColumnWidth(0, 120)
            return

        width = self.tb_activity_metrics.width()
        # Make all columns have the same width
        column_count = self._activity_metric_table_model.columnCount()
        column_width = int(width / float(column_count))
        for c in range(column_count):
            self.tb_activity_metrics.setColumnWidth(c, column_width)

    def load_summary_details(self):
        """Load items summarizing the metric configuration."""
        activity_column_metric_models = self._activity_metric_table_model.models
        self._summary_model.set_summary_models(activity_column_metric_models)
        self.tv_summary.expandAll()

    def on_accepted(self):
        """Slot raised when the wizard has been accepted by the user.

        Used to save any changes for the current metric configuration
        profile.
        """
        self.update_current_profile()
