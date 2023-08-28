# -*- coding: utf-8 -*-
"""
Dialog for creating or editing an NCS pathway entry.
"""

import os
import uuid

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from ..definitions.defaults import ICON_PATH
from ..models.base import LayerType, NcsPathway
from ..utils import FileUtils

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/ncs_pathway_editor_dialog.ui")
)


class NcsPathwayEditorDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for creating or editing an NCS pathway entry."""

    def __init__(self, parent=None, ncs_pathway=None):
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.accepted.connect(self._on_accepted)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        help_icon = FileUtils.get_icon("mActionHelpContents.svg")
        self.btn_help.setIcon(help_icon)

        add_icon = FileUtils.get_icon("symbologyAdd.svg")
        self.btn_add_carbon.setIcon(add_icon)
        # self.btn_add_carbon.clicked.connect(self._on_add_carbon_layer)

        remove_icon = FileUtils.get_icon("symbologyRemove.svg")
        self.btn_delete_carbon.setIcon(remove_icon)
        self.btn_delete_carbon.setEnabled(False)
        # self.btn_delete_carbon.clicked.connect(self._on_remove_carbon_layer)

        edit_icon = FileUtils.get_icon("mActionToggleEditing.svg")
        self.btn_edit_carbon.setIcon(edit_icon)
        self.btn_edit_carbon.setEnabled(False)
        # self.btn_edit_carbon.clicked.connect(self._on_edit_carbon_layer)

        self._edit_mode = False
        self._ncs_pathway = ncs_pathway
        if self._ncs_pathway is not None:
            self._update_controls()
            self._edit_mode = True

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
        self.txt_description.setPlainText(self._ncs_pathway.description)

    def validate(self) -> bool:
        """Validates if name and layer have been specified.

        :returns: True if user input (i.e. name and layer) have been set.
        :rtype: True
        """
        status = True

        if not self.txt_name.text():
            status = False

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
            self._ncs_pathway.description = self.txt_description.toPlainText()

    def _on_accepted(self):
        """Validates user input before closing."""
        if not self.validate():
            return

        self._create_update_ncs_pathway()
        self.accept()
