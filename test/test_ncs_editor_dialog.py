# -*- coding: utf-8 -*-
"""
Unit tests for the NCS pathway editor dialog.
"""

from unittest import TestCase

from cplus_plugin.gui.ncs_pathway_editor_dialog import NcsPathwayEditorDialog

from model_data_for_testing import get_valid_ncs_pathway
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestNcsPathwayEditorDialog(TestCase):
    """Tests for NcsPathwayEditorDialog."""

    def test_invalid_state(self):
        """Assert invalid entries when adding a new NCS pathway."""
        ncs_dialog = NcsPathwayEditorDialog(PARENT)
        result = ncs_dialog.validate()
        self.assertFalse(result)

    def test_edit_mode(self):
        """Assert dialog is in edit mode."""
        valid_ncs = get_valid_ncs_pathway()
        ncs_dialog = NcsPathwayEditorDialog(PARENT, ncs_pathway=valid_ncs)
        self.assertTrue(ncs_dialog.edit_mode)

    def test_layer_defined(self):
        """Assert layer is not empty during edit mode."""
        valid_ncs = get_valid_ncs_pathway()
        ncs_dialog = NcsPathwayEditorDialog(PARENT, ncs_pathway=valid_ncs)
        self.assertIsNotNone(ncs_dialog.layer)
