# -*- coding: utf-8 -*-
"""
Feedback object that provides the ability to update on the rule
validation process.
"""
import os
import typing

from qgis.PyQt import QtCore

from qgis.core import QgsFeedback

from ...models.validation import RuleType


class ValidationFeedback(QgsFeedback):
    """Feedback object that provides the ability to update on the
    rule validation process.
    """

    rule_validation_started = QtCore.pyqtSignal(RuleType)
    rule_progress_changed = QtCore.pyqtSignal(RuleType, float)
    rule_validation_completed = QtCore.pyqtSignal(RuleType)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._rule_type = None
        self._rule_progress = -1.0

    @property
    def current_rule(self) -> RuleType:
        """Gets the current rule type being executed.

        :returns: Returns the current rule being executed or None if the
        feedback object has not been activated.
        :rtype: RuleType
        """
        return self._rule_type

    @property
    def rule_progress(self) -> float:
        """
        Gets the current progress of the rule validation being
        executed.

        :returns: Percentage value between 0.0 and 100.0.
        :rtype: float
        """
        return self._rule_progress

    @current_rule.setter
    def current_rule(self, rule: RuleType):
        """Sets the current rule type being executed.

        Resets the rule progress to -1.0 indicating
        the rule progress has onot run yet.

        :param rule: Current rule type being executed.
        :type rule: RuleType
        """
        if self._rule_type == rule:
            return

        self._rule_type = rule
        self._rule_progress = -1.0

    @rule_progress.setter
    def rule_progress(self, progress: float):
        """Sets the progress of the rule validation being
        executed.

        :param progress: Percentage value between 0.0 and
        100.0. If the former, the rule_validation_started
        signal will be raised otherwise if the latter then
        the rule_validation_completed signal will be raised.
        :type progress: float
        """
        if isinstance(progress, int):
            progress = float(progress)

        if self._rule_progress == progress:
            return

        if progress < 0.0 or progress > 100.0:
            return

        self._rule_progress = progress

        if self._rule_progress == 0.0:
            self.rule_validation_started.emit(self._rule_type)

        self.rule_progress_changed.emit(self._rule_type, self._rule_progress)

        if self._rule_progress == 100.0:
            self.rule_validation_completed.emit(self._rule_type)
