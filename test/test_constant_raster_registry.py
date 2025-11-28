# -*- coding: utf-8 -*-
"""
Unit tests for ConstantRasterRegistry custom type functionality.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from cplus_plugin.lib.constant_raster import ConstantRasterRegistry
from cplus_plugin.models.base import ModelComponentType
from cplus_plugin.definitions.constants import (
    ID_ATTRIBUTE,
    NAME_ATTRIBUTE,
    COMPONENT_TYPE_ATTRIBUTE,
    MIN_VALUE_ATTRIBUTE_KEY,
    MAX_VALUE_ATTRIBUTE_KEY,
)


class TestConstantRasterRegistry(TestCase):
    """Test cases for ConstantRasterRegistry custom type management."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = ConstantRasterRegistry()

    def test_add_custom_type_definition(self):
        """Test adding a custom type definition."""
        type_def = {
            ID_ATTRIBUTE: "test_type",
            NAME_ATTRIBUTE: "Test Type",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        result = self.registry.add_custom_type_definition(type_def)

        self.assertTrue(result)
        self.assertIn(type_def, self.registry._custom_type_definitions)

    def test_add_duplicate_type_definition_fails(self):
        """Test adding duplicate type definition returns False."""
        type_def = {
            ID_ATTRIBUTE: "test_type",
            NAME_ATTRIBUTE: "Test Type",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        self.registry.add_custom_type_definition(type_def)
        result = self.registry.add_custom_type_definition(type_def)

        self.assertFalse(result)

    def test_remove_custom_type_definition(self):
        """Test removing a custom type definition."""
        type_def = {
            ID_ATTRIBUTE: "test_type",
            NAME_ATTRIBUTE: "Test Type",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        self.registry.add_custom_type_definition(type_def)
        result = self.registry.remove_custom_type_definition("test_type")

        self.assertTrue(result)
        self.assertEqual(len(self.registry._custom_type_definitions), 0)

    def test_remove_nonexistent_type_returns_false(self):
        """Test removing nonexistent type returns False."""
        result = self.registry.remove_custom_type_definition("nonexistent")

        self.assertFalse(result)

    def test_update_custom_type_definition(self):
        """Test updating a custom type definition."""
        type_def = {
            ID_ATTRIBUTE: "test_type",
            NAME_ATTRIBUTE: "Test Type",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        self.registry.add_custom_type_definition(type_def)

        updated_def = {
            ID_ATTRIBUTE: "test_type",
            NAME_ATTRIBUTE: "Updated Type",
            MIN_VALUE_ATTRIBUTE_KEY: 5.0,
            MAX_VALUE_ATTRIBUTE_KEY: 95.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        result = self.registry.update_custom_type_definition("test_type", updated_def)

        self.assertTrue(result)
        stored_def = self.registry.get_custom_type_definition("test_type")
        self.assertEqual(stored_def[NAME_ATTRIBUTE], "Updated Type")
        self.assertEqual(stored_def[MIN_VALUE_ATTRIBUTE_KEY], 5.0)

    def test_update_nonexistent_type_returns_false(self):
        """Test updating nonexistent type returns False."""
        updated_def = {
            ID_ATTRIBUTE: "test_type",
            NAME_ATTRIBUTE: "Test",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        result = self.registry.update_custom_type_definition("nonexistent", updated_def)

        self.assertFalse(result)

    def test_get_custom_type_definition(self):
        """Test retrieving a custom type definition by ID."""
        type_def = {
            ID_ATTRIBUTE: "test_type",
            NAME_ATTRIBUTE: "Test Type",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        self.registry.add_custom_type_definition(type_def)
        retrieved = self.registry.get_custom_type_definition("test_type")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved[ID_ATTRIBUTE], "test_type")
        self.assertEqual(retrieved[NAME_ATTRIBUTE], "Test Type")

    def test_get_nonexistent_type_returns_none(self):
        """Test retrieving nonexistent type returns None."""
        retrieved = self.registry.get_custom_type_definition("nonexistent")

        self.assertIsNone(retrieved)

    def test_get_custom_type_definitions(self):
        """Test retrieving all custom type definitions."""
        type_def1 = {
            ID_ATTRIBUTE: "type1",
            NAME_ATTRIBUTE: "Type 1",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }
        type_def2 = {
            ID_ATTRIBUTE: "type2",
            NAME_ATTRIBUTE: "Type 2",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        self.registry.add_custom_type_definition(type_def1)
        self.registry.add_custom_type_definition(type_def2)

        all_defs = self.registry.get_custom_type_definitions()

        self.assertEqual(len(all_defs), 2)
        self.assertIn(type_def1, all_defs)
        self.assertIn(type_def2, all_defs)

    def test_uses_constants_for_keys(self):
        """Test that constants are used for dictionary keys."""
        type_def = {
            ID_ATTRIBUTE: "test",
            NAME_ATTRIBUTE: "Test",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        self.registry.add_custom_type_definition(type_def)
        retrieved = self.registry.get_custom_type_definition("test")

        # Should use constants, not hardcoded strings
        self.assertIn(ID_ATTRIBUTE, retrieved)
        self.assertIn(NAME_ATTRIBUTE, retrieved)
        self.assertIn(MIN_VALUE_ATTRIBUTE_KEY, retrieved)
        self.assertIn(MAX_VALUE_ATTRIBUTE_KEY, retrieved)
        self.assertIn(COMPONENT_TYPE_ATTRIBUTE, retrieved)

    @patch("cplus_plugin.lib.constant_raster.settings_manager")
    def test_save_persists_custom_types(self, mock_settings_manager):
        """Test save() persists custom types to settings."""
        type_def = {
            ID_ATTRIBUTE: "test",
            NAME_ATTRIBUTE: "Test",
            MIN_VALUE_ATTRIBUTE_KEY: 0.0,
            MAX_VALUE_ATTRIBUTE_KEY: 100.0,
            COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
        }

        self.registry.add_custom_type_definition(type_def)
        self.registry.save()

        # Should call save_custom_constant_raster_types
        mock_settings_manager.save_custom_constant_raster_types.assert_called_once()
        args = mock_settings_manager.save_custom_constant_raster_types.call_args[0]
        self.assertIn(type_def, args[0])

    @patch("cplus_plugin.lib.constant_raster.settings_manager")
    def test_load_retrieves_custom_types(self, mock_settings_manager):
        """Test load() retrieves custom types from settings."""
        saved_types = [
            {
                ID_ATTRIBUTE: "test",
                NAME_ATTRIBUTE: "Test",
                MIN_VALUE_ATTRIBUTE_KEY: 0.0,
                MAX_VALUE_ATTRIBUTE_KEY: 100.0,
                COMPONENT_TYPE_ATTRIBUTE: ModelComponentType.ACTIVITY.value,
            }
        ]

        mock_settings_manager.load_custom_constant_raster_types.return_value = (
            saved_types
        )
        self.registry.load()

        self.assertEqual(len(self.registry._custom_type_definitions), 1)
        self.assertEqual(
            self.registry._custom_type_definitions[0][NAME_ATTRIBUTE], "Test"
        )
