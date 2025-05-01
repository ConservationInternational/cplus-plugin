# -*- coding: utf-8 -*-
"""
Unit tests for the PWL dialog.
"""
import os

from unittest import TestCase

from cplus_plugin.conf import settings_manager, Settings
from cplus_plugin.gui.priority_layer_dialog import PriorityLayerDialog

from model_data_for_testing import (
    get_pwl_test_data_path,
    get_test_pwl,
    get_valid_ncs_pathway,
    PWL_UUID_STR,
    VALID_NCS_UUID_STR,
)

from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestPriorityWeightingLayerDialog(TestCase):
    """Tests for PWL dialog."""

    def setUp(self) -> None:
        # We need at least one NCS pathway in settings.
        settings_manager.save_ncs_pathway(get_valid_ncs_pathway())

        self.pwl_path = get_pwl_test_data_path()

    def tearDown(self):
        """Remove test NCS pathway in settings."""
        settings_manager.remove_ncs_pathway(VALID_NCS_UUID_STR)
        settings_manager.delete_priority_layers()

    def reset_settings(self):
        """Reset the test NCS pathway amd PWL in settings."""
        self.tearDown()
        self.setUp()

    def test_add_pwl(self):
        """Assert new PWL can be added via the dialog."""
        self.reset_settings()

        ncs = settings_manager.get_ncs_pathway(VALID_NCS_UUID_STR)
        self.assertEqual(len(ncs.priority_layers), 0)

        layer_dialog = PriorityLayerDialog(parent=PARENT)
        layer_dialog.layer_name.setText("Test Add PWL")
        layer_dialog.layer_description.setText("Test PWL Description")
        layer_dialog.map_layer_file_widget.setFilePath(self.pwl_path)
        layer_dialog.set_selected_items([ncs])
        layer_dialog.accept()

        saved_ncs = settings_manager.get_ncs_pathway(VALID_NCS_UUID_STR)
        self.assertEqual(len(saved_ncs.priority_layers), 1)
        self.assertEqual(len(settings_manager.get_priority_layers()), 1)

    def test_edit_pwl(self):
        """Assert a PWL can be edited via the dialog."""
        self.reset_settings()

        pwl = get_test_pwl()
        settings_manager.save_priority_layer(pwl)

        ncs = settings_manager.get_ncs_pathway(VALID_NCS_UUID_STR)
        self.assertEqual(len(ncs.priority_layers), 0)

        edit_name = "PWL Edited"
        edit_description = "PWL Edited Description"
        layer_dialog = PriorityLayerDialog(pwl, PARENT)
        layer_dialog.layer_name.setText(edit_name)
        layer_dialog.layer_description.setText(edit_description)
        layer_dialog.map_layer_file_widget.setFilePath(self.pwl_path)
        layer_dialog.set_selected_items([ncs])
        layer_dialog.accept()

        saved_ncs = settings_manager.get_ncs_pathway(VALID_NCS_UUID_STR)
        self.assertEqual(len(saved_ncs.priority_layers), 1)
        self.assertEqual(len(settings_manager.get_priority_layers()), 1)

        saved_pwl = settings_manager.get_priority_layer(PWL_UUID_STR)
        self.assertIsNotNone(saved_pwl)
        self.assertEqual(saved_pwl["name"], edit_name)
        self.assertEqual(saved_pwl["description"], edit_description)
