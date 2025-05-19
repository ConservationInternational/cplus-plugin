# -*- coding: utf-8 -*-
"""
Unit tests for the Default PWL dialog.
"""
from unittest import TestCase

from cplus_plugin.conf import settings_manager
from cplus_plugin.gui.settings.priority_layer_add import DlgPriorityAddEdit

from data.priority_weighting_layers import DEFAULT_PRIORITY_LAYERS, PWL_TEST_DATA_PATH

from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestDefaultPriorityWeightingLayerDialog(TestCase):
    """Tests for default PWL dialog."""

    def setUp(self) -> None:
        self.pwl_path = PWL_TEST_DATA_PATH

    def tearDown(self):
        """Remove test NCS pathway and PWL in settings."""
        settings_manager.remove_default_layers()

    def reset_settings(self):
        """Reset the test NCS pathway amd PWL in settings."""
        self.tearDown()
        self.setUp()

    def test_valid_pwl(self):
        """Assert valid PWL added via the dialog."""
        self.reset_settings()

        layer_dialog = DlgPriorityAddEdit(parent=PARENT)
        layer_dialog.txt_name.setText("Test Add Default PWL")
        layer_dialog.txt_description.setPlainText("Test Default PWL Description")
        layer_dialog.txt_version.setText("1.0.0")
        layer_dialog.txt_license.setPlainText("Apache 2.0")
        layer_dialog.map_layer_file_widget.setFilePath(self.pwl_path)
        layer_dialog.accept()

        self.assertTrue(layer_dialog.is_valid_layer())

    def test_invalid_pwl(self):
        """Assert invalid PWL added via the dialog."""
        self.reset_settings()

        layer_dialog = DlgPriorityAddEdit(parent=PARENT)
        layer_dialog.txt_name.setText("Test Add Default PWL")
        layer_dialog.txt_description.setPlainText("Test Default PWL Description")
        layer_dialog.txt_version.setText("1.0.0")
        layer_dialog.txt_license.setPlainText("Apache 2.0")
        # Empty file path
        layer_dialog.map_layer_file_widget.setFilePath("")
        layer_dialog.accept()

        self.assertFalse(layer_dialog.is_valid_layer())

    def test_add_pwl(self):
        """Assert new PWL can be added via the dialog."""
        self.reset_settings()

        default_layers = settings_manager.get_default_layers("priority_layer")
        self.assertEqual(len(default_layers), 0)

        layer_dialog = DlgPriorityAddEdit(parent=PARENT)
        layer_dialog.txt_name.setText("Test Add Default PWL")
        layer_dialog.txt_description.setPlainText("Test Default PWL Description")
        layer_dialog.txt_version.setText("1.0.0")
        layer_dialog.txt_license.setPlainText("Apache 2.0")
        layer_dialog.map_layer_file_widget.setFilePath(self.pwl_path)
        layer_dialog.accept()

        saved_pwl = layer_dialog.layer
        self.assertIsNotNone(saved_pwl)

    def test_edit_pwl(self):
        """Assert a PWL can be edited via the dialog."""
        self.reset_settings()

        settings_manager.save_default_layers("priority_layer", DEFAULT_PRIORITY_LAYERS)

        self.assertEqual(len(settings_manager.get_default_layers("priority_layer")), 1)

        pwl = DEFAULT_PRIORITY_LAYERS[0]

        edit_name = "PWL Edited"
        edit_description = "PWL Edited Description"
        layer_dialog = DlgPriorityAddEdit(PARENT, pwl)
        layer_dialog.txt_name.setText(edit_name)
        layer_dialog.txt_description.setPlainText(edit_description)
        layer_dialog.map_layer_file_widget.setFilePath(self.pwl_path)
        layer_dialog.save()

        saved_pwl = layer_dialog.layer
        self.assertIsNotNone(saved_pwl)
        self.assertEqual(saved_pwl["name"], edit_name)
        self.assertEqual(saved_pwl["description"], edit_description)
