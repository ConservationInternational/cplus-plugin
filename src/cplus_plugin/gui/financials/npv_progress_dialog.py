# -*- coding: utf-8 -*-
"""
Dialog for showing the progress of creating NPV PWL layers.
"""
from qgis.core import (
    QgsApplication,
)
from qgis.PyQt import QtCore, QtGui, QtWidgets

from ...utils import tr


class NpvPwlProgressDialog(QtWidgets.QProgressDialog):
    """Dialog for showing the progress of creating NPV PWL layers."""

    def __init__(self, parent, feedback):
        super().__init__(
            tr("Creating NPV priority weighting layers..."),
            tr("Cancel"),
            0,
            100,
            parent,
        )

        self._feedback = feedback
        self._feedback.progressChanged.connect(self._on_progress_changed)

        self.canceled.connect(self._on_canceled)
        self.setWindowTitle(tr("NPW PWL Progress"))

    def _on_progress_changed(self, progress: float):
        """Slot raised when feedback progress has changed.

        :param progress: Current progress of the feedback.
        :type progress: float
        """
        self.setValue(int(progress))

        # Force UI to be updated
        QgsApplication.processEvents()

    def _on_canceled(self):
        """Slot raised when the Cancel button has been clicked."""
        self._feedback.cancel()
