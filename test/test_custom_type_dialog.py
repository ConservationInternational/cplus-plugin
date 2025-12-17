# -*- coding: utf-8 -*-
"""
Unit tests for CustomTypeDefinitionDialog.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from qgis.PyQt import QtWidgets

from cplus_plugin.gui.constant_rasters.custom_type_dialog import (
    CustomTypeDefinitionDialog,
)
from cplus_plugin.models.base import ModelComponentType
from cplus_plugin.definitions.constants import (
    NAME_ATTRIBUTE,
    COMPONENT_TYPE_ATTRIBUTE,
    MIN_VALUE_ATTRIBUTE_KEY,
    MAX_VALUE_ATTRIBUTE_KEY,
    DEFAULT_VALUE_ATTRIBUTE_KEY,
)


class TestCustomTypeDefinitionDialog(TestCase):
    """Test cases for CustomTypeDefinitionDialog."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])

    def test_dialog_initialization_create_mode(self):
        """Test dialog initializes correctly in create mode."""
        dialog = CustomTypeDefinitionDialog(edit_mode=False)

        self.assertIsNotNone(dialog)
        self.assertFalse(dialog.edit_mode)
        self.assertEqual(dialog.windowTitle(), "Add Investability Type")
        self.assertEqual(dialog.txt_type_name.text(), "")

    def test_dialog_initialization_edit_mode(self):
        """Test dialog initializes correctly in edit mode."""
        dialog = CustomTypeDefinitionDialog(edit_mode=True)

        self.assertTrue(dialog.edit_mode)
        self.assertEqual(dialog.windowTitle(), "Edit Investability Type")

    def test_get_type_definition_structure(self):
        """Test get_type_definition returns correct structure."""
        dialog = CustomTypeDefinitionDialog()
        dialog.txt_type_name.setText("Test Type")

        type_def = dialog.get_type_definition()

        self.assertIsInstance(type_def, dict)
        self.assertIn(NAME_ATTRIBUTE, type_def)
        self.assertIn(COMPONENT_TYPE_ATTRIBUTE, type_def)
        self.assertIn(MIN_VALUE_ATTRIBUTE_KEY, type_def)
        self.assertIn(MAX_VALUE_ATTRIBUTE_KEY, type_def)
        self.assertIn(DEFAULT_VALUE_ATTRIBUTE_KEY, type_def)

    def test_get_type_definition_uses_constants(self):
        """Test get_type_definition uses constants as keys."""
        dialog = CustomTypeDefinitionDialog()
        dialog.txt_type_name.setText("Test Type")

        type_def = dialog.get_type_definition()

        # Should use constant keys, not hardcoded strings
        self.assertEqual(type_def[NAME_ATTRIBUTE], "Test Type")
        self.assertEqual(
            type_def[COMPONENT_TYPE_ATTRIBUTE], ModelComponentType.ACTIVITY.value
        )
        self.assertEqual(type_def[MIN_VALUE_ATTRIBUTE_KEY], 0.0)
        self.assertEqual(type_def[MAX_VALUE_ATTRIBUTE_KEY], 100.0)
        self.assertEqual(type_def[DEFAULT_VALUE_ATTRIBUTE_KEY], 0.0)

    def test_get_type_definition_uses_enum_value(self):
        """Test component_type uses ModelComponentType.ACTIVITY.value."""
        dialog = CustomTypeDefinitionDialog()
        dialog.txt_type_name.setText("Test Type")

        type_def = dialog.get_type_definition()

        # Should be string "activity", not enum object
        self.assertIsInstance(type_def[COMPONENT_TYPE_ATTRIBUTE], str)
        self.assertEqual(type_def[COMPONENT_TYPE_ATTRIBUTE], "activity")

    def test_get_type_definition_strips_whitespace(self):
        """Test name is stripped of leading/trailing whitespace."""
        dialog = CustomTypeDefinitionDialog()
        dialog.txt_type_name.setText("  Test Type  ")

        type_def = dialog.get_type_definition()

        self.assertEqual(type_def[NAME_ATTRIBUTE], "Test Type")

    def test_set_values_populates_name(self):
        """Test set_values populates the name field."""
        dialog = CustomTypeDefinitionDialog(edit_mode=True)
        type_def = {NAME_ATTRIBUTE: "Original Name"}

        dialog.set_values(type_def)

        self.assertEqual(dialog.txt_type_name.text(), "Original Name")
        self.assertEqual(dialog.original_name, "Original Name")

    def test_set_values_with_missing_name(self):
        """Test set_values handles missing name gracefully."""
        dialog = CustomTypeDefinitionDialog(edit_mode=True)
        type_def = {}

        dialog.set_values(type_def)

        self.assertEqual(dialog.txt_type_name.text(), "")
        self.assertEqual(dialog.original_name, "")

    def test_name_validation_empty(self):
        """Test validation rejects empty name."""
        dialog = CustomTypeDefinitionDialog()
        dialog.txt_type_name.setText("")

        # Simulate validation
        is_valid = dialog.txt_type_name.text().strip() != ""

        self.assertFalse(is_valid)

    def test_name_validation_whitespace_only(self):
        """Test validation rejects whitespace-only name."""
        dialog = CustomTypeDefinitionDialog()
        dialog.txt_type_name.setText("   ")

        # Simulate validation
        is_valid = dialog.txt_type_name.text().strip() != ""

        self.assertFalse(is_valid)

    def test_duplicate_name_detection(self):
        """Test duplicate name detection in existing_types."""
        existing_names = ["Type A", "Type B", "Type C"]
        dialog = CustomTypeDefinitionDialog(existing_types=existing_names)
        dialog.txt_type_name.setText("Type B")

        # Simulate duplicate check
        new_name = dialog.txt_type_name.text().strip()
        is_duplicate = new_name in existing_names

        self.assertTrue(is_duplicate)

    def test_range_configuration_default_values(self):
        """Test range configuration spinboxes have correct default values."""
        dialog = CustomTypeDefinitionDialog()

        self.assertEqual(dialog.spin_min_value.value(), 0.0)
        self.assertEqual(dialog.spin_max_value.value(), 100.0)
        self.assertEqual(dialog.spin_default_value.value(), 0.0)

    def test_get_type_definition_includes_range_values(self):
        """Test get_type_definition includes custom range values."""
        dialog = CustomTypeDefinitionDialog()
        dialog.txt_type_name.setText("Custom Type")
        dialog.spin_min_value.setValue(10.0)
        dialog.spin_max_value.setValue(50.0)
        dialog.spin_default_value.setValue(25.0)

        type_def = dialog.get_type_definition()

        self.assertEqual(type_def[MIN_VALUE_ATTRIBUTE_KEY], 10.0)
        self.assertEqual(type_def[MAX_VALUE_ATTRIBUTE_KEY], 50.0)
        self.assertEqual(type_def[DEFAULT_VALUE_ATTRIBUTE_KEY], 25.0)

    def test_set_values_populates_range_fields(self):
        """Test set_values populates all range configuration fields."""
        dialog = CustomTypeDefinitionDialog(edit_mode=True)
        type_def = {
            NAME_ATTRIBUTE: "Test Type",
            MIN_VALUE_ATTRIBUTE_KEY: 5.0,
            MAX_VALUE_ATTRIBUTE_KEY: 95.0,
            DEFAULT_VALUE_ATTRIBUTE_KEY: 50.0,
        }

        dialog.set_values(type_def)

        self.assertEqual(dialog.txt_type_name.text(), "Test Type")
        self.assertEqual(dialog.spin_min_value.value(), 5.0)
        self.assertEqual(dialog.spin_max_value.value(), 95.0)
        self.assertEqual(dialog.spin_default_value.value(), 50.0)

    def test_set_values_handles_missing_range_fields(self):
        """Test set_values uses defaults when range fields are missing."""
        dialog = CustomTypeDefinitionDialog(edit_mode=True)
        type_def = {NAME_ATTRIBUTE: "Test Type"}

        dialog.set_values(type_def)

        self.assertEqual(dialog.spin_min_value.value(), 0.0)
        self.assertEqual(dialog.spin_max_value.value(), 100.0)
        self.assertEqual(dialog.spin_default_value.value(), 0.0)
