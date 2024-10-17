# -*- coding: utf-8 -*-
"""
Wizard for customizing custom activity metrics table.
"""

import os
import re
import typing

from qgis.core import (
    Qgis,
    QgsColorRamp,
    QgsFillSymbolLayer,
    QgsGradientColorRamp,
    QgsMapLayerProxyModel,
    QgsRasterLayer,
)
from qgis.gui import QgsGui, QgsMessageBar

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from ..conf import Settings, settings_manager

from ..definitions.defaults import ICON_PATH, USER_DOCUMENTATION_SITE
from .metrics_builder_model import MetricColumnListItem, MetricColumnListModel
from ..models.base import Activity
from ..utils import FileUtils, log, generate_random_color, open_documentation, tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/activity_metrics_builder_dialog.ui")
)


class ActivityMetricsBuilder(QtWidgets.QWizard, WidgetUi):
    """Wizard for customizing custom activity metrics table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        self._message_bar = QgsMessageBar()
        # self.vl_notification.addWidget(self._message_bar)

        self._column_list_model = MetricColumnListModel()

        # Initialize wizard
        ci_icon = FileUtils.get_icon("cplus_logo.svg")
        ci_pixmap = ci_icon.pixmap(64, 64)
        self.setPixmap(QtWidgets.QWizard.LogoPixmap, ci_pixmap)

        help_button = self.button(QtWidgets.QWizard.HelpButton)
        help_icon = FileUtils.get_icon("mActionHelpContents_green.svg")
        help_button.setIcon(help_icon)

        self.currentIdChanged.connect(self.on_page_id_changed)
        self.helpRequested.connect(self.on_help_requested)

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

        self.splitter.setStretchFactor(0, 25)
        self.splitter.setStretchFactor(1, 75)

        self.lst_columns.setModel(self._column_list_model)
        self.lst_columns.selectionModel().selectionChanged.connect(
            self.on_column_selection_changed
        )

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

    def on_help_requested(self):
        """Slot raised when the help button has been clicked.

        Opens the online help documentation in the user's browser.
        """
        open_documentation(USER_DOCUMENTATION_SITE)

    def on_add_column(self):
        """Slot raised to add a new column."""
        label_text = (
            f"{tr('Specify the name of the column.')}<br>"
            f"<i>{tr('Any special characters will be removed.')}"
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
                    tr("There is an already existing column name"),
                )
                return

            self._column_list_model.add_new_column(clean_column_name)

    def on_remove_column(self):
        """Slot raised to remove the selected column."""
        selected_items = self.selected_column_items()
        for item in selected_items:
            self._column_list_model.remove_column(item.name)

    def on_move_up_column(self):
        """Slot raised to move the selected column one level up."""
        selected_items = self.selected_column_items()
        if len(selected_items) == 0:
            return

        item = selected_items[0]
        row = self._column_list_model.move_column_up(item.row())
        if row == -1:
            return

        # Maintain selection
        self.select_column(row)

    def on_move_down_column(self):
        """Slot raised to move the selected column one level down."""
        selected_items = self.selected_column_items()
        if len(selected_items) == 0:
            return

        item = selected_items[0]
        row = self._column_list_model.move_column_down(item.row())
        if row == -1:
            return

        # Maintain selection
        self.select_column(row)

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

        selected_columns = self.selected_column_items()
        if len(selected_columns) != 1:
            self.btn_delete_column.setEnabled(False)
            self.btn_column_up.setEnabled(False)
            self.btn_column_down.setEnabled(False)

    def selected_column_items(self) -> typing.List[MetricColumnListItem]:
        """Returns the selected column items in the column list view.

        :returns: A collection of the selected column items.
        :rtype: list
        """
        selection_model = self.lst_columns.selectionModel()
        idxs = selection_model.selectedRows()

        return [self._column_list_model.item(idx.row()) for idx in idxs]
