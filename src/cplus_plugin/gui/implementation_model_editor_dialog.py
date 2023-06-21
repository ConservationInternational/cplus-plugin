# -*- coding: utf-8 -*-
"""
Dialog for creating or editing an NCS pathway entry.
"""

import os
import uuid

from qgis.PyQt import QtWidgets

from qgis.PyQt.uic import loadUiType

from qgis.core import QgsApplication

from ..models.base import ImplementationModel

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/ncs_pathway_editor_dialog.ui")
)


class ImplementationModelEditorDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for creating or editing an implementation model entry."""

    def __init__(self, parent=None, implementation_model=None):
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.accepted.connect(self._on_accepted)

        self._edit_mode = False
        self._implementation_model = implementation_model
        if self._implementation_model is not None:
            self._update_controls()
            self._edit_mode = True

        help_icon = QgsApplication.instance().getThemeIcon("mActionHelpContents.svg")
        self.btn_help.setIcon(help_icon)

    @property
    def implementation_model(self) -> ImplementationModel:
        """Returns a reference to the ImplementationModel object.

        :returns: Reference to the ImplementationModel object.
        :rtype: ImplementationModel
        """
        return self._implementation_model

    @property
    def edit_mode(self) -> bool:
        """Returns the state of the editor.

        :returns: True if the editor is editing an existing
        ImplementationModel object, else False if its creating
        a new object.
        :rtype: bool
        """
        return self._edit_mode

    def _update_controls(self):
        """Update controls with data from the ImplementationModel
        object.
        """
        if self._implementation_model is None:
            return

        self.txt_name.setText(self._implementation_model.name)
        self.txt_description.setText(self._implementation_model.description)

    def validate(self) -> bool:
        """Validates if name has been specified.

        :returns: True if the name have been set.
        :rtype: True
        """
        status = True

        if not self.txt_name.text():
            status = False

        return status

    def _create_implementation_model(self):
        """Create or update NcsPathway from user input."""
        if self._implementation_model is None:
            self._implementation_model = ImplementationModel(
                uuid.uuid4(), self.txt_name.text(), self.txt_description.text()
            )
        else:
            # Update mode
            self._ncs_pathway.name = self.txt_name.text()
            self._ncs_pathway.description = self.txt_description.text()

    def _on_accepted(self):
        """Validates user input before closing."""
        if not self.validate():
            return

        self._create_implementation_model()
        self.accept()
