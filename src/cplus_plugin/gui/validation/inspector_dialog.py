# -*- coding: utf-8 -*-
"""
Dialog for viewing NCS validation results.
"""

import os
import typing

from qgis.core import Qgis, QgsApplication
from qgis.gui import QgsGui

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from ...definitions.defaults import ICON_PATH, USER_DOCUMENTATION_SITE
from ...models.validation import ValidationResult
from .result_items import DETAILED_RESULT_TYPE, RuleResultItem
from ...utils import FileUtils, open_documentation, tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/validation_inspector_dialog.ui")
)


class ValidationInspectorDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for showing validation results."""

    def __init__(self, parent=None, result=None):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        help_icon = FileUtils.get_icon("mActionHelpContents_green.svg")
        self.btn_help.setIcon(help_icon)
        self.btn_help.clicked.connect(self.open_help)

        expand_icon = FileUtils.get_icon("mActionExpandTree.svg")
        self.btn_expand.setIcon(expand_icon)
        self.btn_expand.clicked.connect(self.on_expand_all_result_items)

        collapse_icon = FileUtils.get_icon("mActionCollapseTree.svg")
        self.btn_collapse.setIcon(collapse_icon)
        self.btn_collapse.clicked.connect(self.on_collapse_all_result_items)

        self.tw_results.setColumnCount(1)
        self.tw_results.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tw_results.customContextMenuRequested.connect(
            self.on_custom_menu_requested
        )

        self._validation_result = result
        if self._validation_result is not None:
            self._update()

    @property
    def result(self) -> typing.Union[ValidationResult, None]:
        """Returns the validation result used to show results.

        :returns: The validation result in the current view or None
        if not specified.
        :rtype: ValidationResult
        """
        return self._validation_result

    @result.setter
    def result(self, validation_result: ValidationResult):
        """Set the validation result to show.

        :param validation_result: Validation result to show.
        :type validation_result: ValidationResult
        """
        self._validation_result = validation_result
        self._update()

    def open_help(self, activated: bool):
        """Opens the user documentation for the plugin in a browser."""
        open_documentation(USER_DOCUMENTATION_SITE)

    def _update(self):
        """Set result details."""
        if self._validation_result is None:
            return

        for rule_result in self._validation_result:
            if rule_result is None:
                continue

            rule_item = RuleResultItem(rule_result=rule_result)
            self.tw_results.addTopLevelItem(rule_item)

    def on_expand_all_result_items(self):
        """Slot raised to expand all rule result tree items."""
        self._expand_collapse_all_items(True)

    def on_collapse_all_result_items(self):
        """Slot raised to collapse all rule result tree items"""
        self._expand_collapse_all_items(False)

    def _expand_collapse_all_items(self, expand: bool):
        """Expand or collapse all rule result items.

        :param expand: True to expand else False to collapse.
        :type expand: bool
        """
        for i in range(self.tw_results.topLevelItemCount()):
            item = self.tw_results.topLevelItem(i)
            if expand:
                self.tw_results.expandItem(item)

            else:
                self.tw_results.collapseItem(item)

            # Also expand result description node
            item.expand_description(expand)

    def on_custom_menu_requested(self, point: QtCore.QPoint):
        """Slot raised when a custom menu has been requested.

        :param point: Position of the context menu event.
        :type point: QtCore.QPoint
        """
        item = self.tw_results.itemAt(point)
        if item.type() != DETAILED_RESULT_TYPE:
            return

        # Action for copying detailed result item
        copy_action = QtWidgets.QAction()
        copy_action.setText(tr("Copy"))
        copy_action.setIcon(FileUtils.get_icon("mActionEditCopy.svg"))
        copy_action.triggered.connect(
            lambda: self.on_copy_detailed_results(item.text(0))
        )

        menu = QtWidgets.QMenu(self)
        menu.addAction(copy_action)

        menu.exec_(self.tw_results.mapToGlobal(point))

    def on_copy_detailed_results(self, copy_text: str):
        """Slot raised to copy detailed error/warning text.

        :param copy_text: Text to be copied to the clipboard.
        :type copy_text: str
        """
        # Copy details to the clipboard
        QgsApplication.instance().clipboard().setText(copy_text)
