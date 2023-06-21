# -*- coding: utf-8 -*-
"""
Dialog for creating or editing an NCS pathway entry.
"""

import os
import typing
import uuid

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from qgis.core import QgsApplication

from ..models.base import LayerType, NcsPathway

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/ncs_pathway_editor_dialog.ui")
)


class NcsPathwayEditorDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for creating or editing an NCS pathway entry."""

    def __init__(self, parent=None, ncs_pathway=None):
        super().__init__(parent)
        self.setupUi(self)

        self.rb_map_canvas.toggled.connect(self._on_select_map_canvas)
        self.rb_upload.toggled.connect(self._on_upload_from_file)
        self.buttonBox.accepted.connect(self._on_accepted)

        self._edit_mode = False
        self._ncs_pathway = ncs_pathway
        if self._ncs_pathway is not None:
            self._update_controls()
            self._edit_mode = True

        help_icon = QgsApplication.instance().getThemeIcon("mActionHelpContents.svg")
        self.btn_help.setIcon(help_icon)

        self.rb_map_canvas.setChecked(True)

    @property
    def ncs_pathway(self) -> NcsPathway:
        """Returns a reference to the NcsPathway object.

        :returns: Reference to the NcsPathway object.
        :rtype: NcsPathway
        """
        return self._ncs_pathway

    @property
    def edit_mode(self) -> bool:
        """Returns the state of the editor.

        :returns: True if the editor is editing an existing NcsPathway
        object, else False if its creating a new object.
        :rtype: bool
        """
        return self._edit_mode

    def _update_controls(self):
        """Update controls with data from the NcsPathway object."""
        if self._ncs_pathway is None:
            return

        self.txt_name.setText(self._ncs_pathway.name)
        self.txt_description.setText(self._ncs_pathway.description)

    def validate(self) -> bool:
        """Validates if name and layer have been specified.

        :returns: True if user input (i.e. name and layer) have been set.
        :rtype: True
        """
        status = True

        if not self.txt_name.text():
            status = False

        # TODO: Add layer validation

        return status

    def _create_update_ncs_pathway(self):
        """Create or update NcsPathway from user input."""
        if self._ncs_pathway is None:
            self._ncs_pathway = NcsPathway(
                uuid.uuid4(),
                self.txt_name.text(),
                self.txt_description.text(),
                "",
                LayerType.VECTOR,
                True,
            )
        else:
            # Update mode
            self._ncs_pathway.name = self.txt_name.text()
            self._ncs_pathway.description = self.txt_description.text()

    def _on_accepted(self):
        """Validates user input before closing."""
        if not self.validate():
            return

        self._create_update_ncs_pathway()
        self.accept()

    def _on_select_map_canvas(self, toggled):
        """Slot raised when radio button for choosing map layer
        from map canvas has been selected.
        """
        if toggled:
            self.stackedWidget.setCurrentIndex(0)

    def _on_upload_from_file(self, toggled):
        """ "Slot raised when radio button for uploading map layer from f
        ile has been selected.
        """
        if toggled:
            self.stackedWidget.setCurrentIndex(1)
