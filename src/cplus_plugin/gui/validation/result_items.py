# -*- coding: utf-8 -*-
"""
Tree items for rule and aggregated validation results.
"""

import typing

from qgis.PyQt import QtCore, QtGui, QtWidgets

from ...models.validation import RuleResult, ValidationCategory
from ...utils import FileUtils


RULE_RESULT_TYPE = QtWidgets.QTreeWidgetItem.UserType + 2


class RuleResultItem(QtWidgets.QTreeWidgetItem):
    """Tree widget item for showing rule result details."""

    def __init__(self, parent=None, rule_result: RuleResult = None):
        super().__init__(parent, RULE_RESULT_TYPE)

        self._result = rule_result
        self._description_item = None
        if self._result is not None:
            self._update()

    @property
    def result(self) -> RuleResult:
        """Gets the rule result used to show result details.

        :returns: Returns the rule result used to show
        result details.
        :rtype: RuleResult
        """
        return self._result

    @result.setter
    def result(self, rule_result: RuleResult):
        """Sets the rule result to show result details.

        :param rule_result: Rule result to show result details.
        :type rule_result: RuleResult
        """
        self._result = rule_result
        self._update()

    def _update(self):
        """Set the details of the rule result."""
        config = self._result.config
        rule_title = f"Rule: {config.description}"
        self.setText(0, rule_title)
        font = self.font(0)
        font.setBold(True)
        self.setFont(0, font)

        # Set icon
        icon = QtGui.QIcon()
        if self._result.success:
            icon = FileUtils.get_icon("mIconSuccess.svg")
        else:
            if config.category == ValidationCategory.ERROR:
                icon = FileUtils.get_icon("mIconDelete.svg")
            elif config.category == ValidationCategory.WARNING:
                icon = FileUtils.get_icon("mIconWarning.svg")

        self.setIcon(0, icon)

        # Result description
        self._description_item = QtWidgets.QTreeWidgetItem()
        result_description = f"Result: {self._result.summary}"
        self._description_item.setText(0, result_description)
        self.addChild(self._description_item)

        if not self._result.success:
            # Error/warning details
            for error_info in self._result.validate_info:
                err_description = f"{error_info[0]}: {error_info[1]}"
                error_info_item = QtWidgets.QTreeWidgetItem()
                error_info_item.setText(0, err_description)
                error_info_item.setToolTip(0, error_info[1])
                icon = FileUtils.get_icon("dash.svg")
                error_info_item.setIcon(0, icon)
                self._description_item.addChild(error_info_item)

            # Recommendation
            recommendation_item = QtWidgets.QTreeWidgetItem()
            recommendation_description = (
                f"Recommendation: {self._result.recommendation}"
            )
            recommendation_item.setText(0, recommendation_description)
            self.addChild(recommendation_item)

    def expand_description(self, expand: bool):
        """Expand or collapse the result description tree node.

        :param expand: True to expand the result description node else False.
        :type expand: bool
        """
        if self._description_item is not None:
            self._description_item.setExpanded(expand)
