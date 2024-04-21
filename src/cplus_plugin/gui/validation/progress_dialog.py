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

from .inspector_dialog import ValidationInspectorDialog
from ...lib.validation.manager import validation_manager
from ...models.validation import RuleType, SubmitResult
from ...utils import FileUtils, tr, log

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/validation_progress.ui")
)


class ValidationProgressDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for showing the progress of the validation process."""

    def __init__(self, submit_result: SubmitResult, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        self._submit_result = submit_result
        self._feedback = self._submit_result.feedback
        self._feedback.rule_validation_started.connect(self._on_rule_validation_started)
        self._feedback.progressChanged.connect(self._on_progress_changed)
        self._feedback.validation_completed.connect(self._on_validation_completed)

        self.btn_show_details = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)

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

    def _on_rule_validation_started(self, rule_type: RuleType):
        """Slot raised when rule validation has started.

        param rule_type: Rule type whose execution has started.
        :type rule_type: RuleType
        """
        # Update label
        pass

    def _on_progress_changed(self, progress: float):
        """Slot raised when overall progress of the validation has changed.

        :param progress: Current progress of the validation.
        :type progress: float
        """
        self.pg_bar.setValue(int(progress))

    def _on_validation_completed(self):
        """Slot raised when overall validation has completed."""
        self.pg_bar.setValue(100)
        self.btn_show_details.setEnabled(True)

    def _on_show_validation_results(self, checked: bool):
        """Slot raised to show the validation inspector.

        This will re-check whether the validation is complete and
        get the corresponding result to display in the inspector.

        :param checked: True if the button is checked else False.
        :type checked: bool
        """
        if validation_manager.is_validation_complete(self._submit_result):
            validation_result = validation_manager.validation_result(
                self._submit_result
            )
            if validation_result is None:
                return

            inspector_dialog = ValidationInspectorDialog(self, result=validation_result)
            inspector_dialog.exec_()
