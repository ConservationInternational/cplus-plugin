# -*- coding: utf-8 -*-
"""
Editor for a model's description property.
"""
import os
import typing

from qgis.PyQt import QtCore, QtWidgets


class ModelDescriptionEditorDialog(QtWidgets.QDialog):
    """Dialog for editing a model's description."""

    def __init__(self, parent=None, description=None):
        super().__init__(parent)
        self._init_ui()
        if description is not None:
            self.txt_description.setPlainText(description)

    def _init_ui(self):
        """Add UI controls."""
        layout = QtWidgets.QVBoxLayout(self)

        self.txt_description = QtWidgets.QPlainTextEdit(self)
        self.txt_description.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.txt_description.setPlaceholderText(
            self.tr("Enter the model's description...")
        )
        layout.addWidget(self.txt_description)

        self.dlg_btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel, self
        )
        self.dlg_btn.rejected.connect(self.reject)
        self.dlg_btn.accepted.connect(self.accept)
        layout.addWidget(self.dlg_btn)

        self.setLayout(layout)
        self.resize(400, 250)
        self.setWindowTitle(self.tr("Model Description Editor"))

    @property
    def description(self) -> str:
        """Returns the description text.

        :returns: The description specified by the user.
        :rtype: str
        """
        return self.txt_description.toPlainText()
