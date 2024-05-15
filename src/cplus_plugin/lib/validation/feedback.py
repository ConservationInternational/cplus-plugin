# -*- coding: utf-8 -*-
"""
Feedback object that provides the ability to update on the rule
validation process.
"""
import os
import typing

from qgis.PyQt import QtCore

from qgis.core import QgsFeedback

from ...models.validation import RuleInfo, ValidationResult


class ValidationFeedback(QgsFeedback):
    """Feedback object that provides the ability to update the
    rule validation process.
    """

    rule_validation_started = QtCore.pyqtSignal(RuleInfo)
    rule_progress_changed = QtCore.pyqtSignal(RuleInfo, float)
    rule_validation_completed = QtCore.pyqtSignal(RuleInfo)
    validation_completed = QtCore.pyqtSignal(ValidationResult)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.progressChanged.connect(self._on_total_progress_changed)

        self._rule_info = None
        self._rule_progress = -1.0
        self._validation_complete = False

    @property
    def is_validation_complete(self) -> bool:
        """Indicates whether the full validation (i.e. NOT rule validation)
        is complete.

        :returns: True if the full validation is complete, else False.
        :rtype: bool
        """
        return self._validation_complete

    def _on_total_progress_changed(self, progress: float):
        """Slot raised when the progress has changed.

        :param progress: Current progress of the full validation.
        :type progress: float
        """
        if progress >= 100:
            self._validation_complete = True

    @property
    def current_rule(self) -> RuleInfo:
        """Gets the current rule info being executed.

        :returns: Returns the current rule being executed or None if the
        feedback object has not been activated.
        :rtype: RuleInfo
        """
        return self._rule_info

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
    def current_rule(self, rule: RuleInfo):
        """Sets the current rule info being executed.

        Resets the rule progress to -1.0 indicating
        the rule progress has not yet been executed.

        :param rule: Current rule info being executed.
        :type rule: RuleInfo
        """
        if self._rule_info == rule:
            return

        self._rule_info = rule
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
            self.rule_validation_started.emit(self._rule_info)

        self.rule_progress_changed.emit(self._rule_info, self._rule_progress)

        if self._rule_progress == 100.0:
            self.rule_validation_completed.emit(self._rule_info)
