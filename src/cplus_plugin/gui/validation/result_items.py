# -*- coding: utf-8 -*-
"""
Tree items for rule and aggregated validation results.
"""

import typing

from qgis.PyQt import QtCore, QtWidgets

from ...models.validation import RuleResult


RULE_RESULT_TYPE = QtWidgets.QTreeWidgetItem.UserType + 2


class RuleResultItem(QtWidgets.QTreeWidgetItem):
    """Tree widget item for showing rule result details."""

    def __init__(self, parent = None, rule_result = RuleResult):
        super().__init__(parent, RULE_RESULT_TYPE)

        self._result = rule_result
        if self._result is not None:
            self._update()