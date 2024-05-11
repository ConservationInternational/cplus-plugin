# -*- coding: utf-8 -*-
"""
Dialog for showing the progress of the validation process.
"""

import os
import typing

from qgis.core import Qgis
from qgis.gui import QgsGui

from qgis.PyQt import QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from ...lib.validation.feedback import ValidationFeedback
from ...lib.validation.manager import validation_manager
from ...models.validation import RuleInfo, SubmitResult
from ...utils import tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/validation_progress.ui")
)


class ValidationProgressDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for showing the progress of the validation process."""

    def __init__(
        self,
        submit_result: SubmitResult,
        parent=None,
        hide_details_button=False,
        close_on_completion=False,
    ):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        self._submit_result = submit_result
        self._feedback = self._submit_result.feedback
        self._feedback.rule_validation_started.connect(self._on_rule_validation_started)
        self._feedback.progressChanged.connect(self._on_progress_changed)
        self._feedback.validation_completed.connect(self._on_validation_completed)

        self._close_on_completion = close_on_completion

        self.btn_show_details = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        if hide_details_button:
            self.btn_show_details.setVisible(False)

        self._initialize_ui()

    def _initialize_ui(self):
        """Initializes the UI controls."""
        self.btn_show_details.setText(tr("Show results"))
        # Just in case the process is complete when the dialog is being loaded
        if validation_manager.is_validation_complete(self._submit_result):
            self.btn_show_details.setEnabled(True)
        else:
            self.btn_show_details.setEnabled(False)

        self.btn_show_details.clicked.connect(self._on_show_validation_results)

        self.pg_bar.setValue(int(self._feedback.progress()))
        self._update_current_rule(self._feedback.current_rule)

    def _on_rule_validation_started(self, rule_info: RuleInfo):
        """Slot raised when rule validation has started.

        param rule_info: Information about the rule whose execution has started.
        :type rule_info: RuleInfo
        """
        self._update_current_rule(rule_info)

    def _update_current_rule(self, rule_info: RuleInfo):
        """
        Update the label with the name of the rule being executed.

        param rule_info: Information about the rule currently being executed..
        :type rule_info: RuleInfo
        """
        if rule_info is None:
            return

        prefix_tr = tr("Validating Rule")
        self.lbl_rule.setText(f"{prefix_tr}: {rule_info.name}...")

    def _on_progress_changed(self, progress: float):
        """Slot raised when overall progress of the validation has changed.

        :param progress: Current progress of the validation.
        :type progress: float
        """
        self.pg_bar.setValue(int(progress))

    def _on_validation_completed(self):
        """Slot raised when overall validation has completed."""
        self.pg_bar.setValue(100)
        self.lbl_rule.setText(tr("Validation complete"))
        self.btn_show_details.setEnabled(True)
        if self._close_on_completion:
            self.close()

    def _on_show_validation_results(self, checked: bool):
        """Slot raised to show the validation inspector.

        This will re-check whether the validation is complete and
        get the corresponding result to display in the inspector.

        :param checked: True if the button is checked else False.
        :type checked: bool
        """
        # Not ideal but the two dialogs are tightly coupled
        from .inspector_dialog import ValidationInspectorDialog

        if validation_manager.is_validation_complete(self._submit_result):
            validation_result = validation_manager.validation_result(
                self._submit_result
            )
            if validation_result is None:
                return

            inspector_dialog = ValidationInspectorDialog(self, result=validation_result)
            inspector_dialog.exec_()

    def hide_results_button(self, hide: bool):
        """Hides or shows the button for showing the validation inspector.

        By default, the button is visible.

        :param hide: True to hide the 'Show Results' button else False
        to make it visible again.
        :type hide: bool
        """
        if hide and self.btn_show_details.isVisible():
            self.btn_show_details.setVisible(False)

        elif not hide and not self.btn_show_details.isVisible():
            self.btn_show_details.setVisible(True)

    @property
    def feedback(self) -> ValidationFeedback:
        """Gets the feedback object used in the progress dialog.

        :returns: Feedback objects used in the progress dialog.
        :rtype: ValidationFeedback
        """
        return self._feedback
