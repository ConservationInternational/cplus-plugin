# -*- coding: utf-8 -*-
"""
Unit tests for constant raster models and functionality.
"""

import sys
from unittest import TestCase
from uuid import UUID

from cplus_plugin.definitions.constants import (
    COMPONENT_ID_ATTRIBUTE,
    COMPONENT_TYPE_ATTRIBUTE,
    COMPONENT_UUID_ATTRIBUTE,
    ENABLED_ATTRIBUTE,
    SKIP_RASTER_ATTRIBUTE,
    VALUE_INFO_ATTRIBUTE,
    NORMALIZED_ATTRIBUTE,
    ABSOLUTE_ATTRIBUTE,
    MIN_VALUE_ATTRIBUTE_KEY,
    MAX_VALUE_ATTRIBUTE_KEY,
    ALLOWABLE_MIN_ATTRIBUTE,
    ALLOWABLE_MAX_ATTRIBUTE,
    COMPONENTS_ATTRIBUTE,
)
from cplus_plugin.models.base import ModelComponentType, Activity, LayerType
from cplus_plugin.models.constant_raster import (
    ConstantRasterInfo,
    ConstantRasterComponent,
    ConstantRasterCollection,
    ConstantRasterMetadata,
    InputRange,
)
from cplus_plugin.models.helpers import (
    constant_raster_collection_to_dict,
    constant_raster_collection_from_dict,
)
from cplus_plugin.gui.constant_rasters.constant_raster_widgets import (
    YearsExperienceWidget,
)

from model_data_for_testing import (
    ACTIVITY_2_UUID_STR,
    ACTIVITY_3_UUID_STR,
    TEST_RASTER_PATH,
    get_activity,
    get_constant_raster_info,
    get_constant_raster_component,
    get_constant_raster_collection,
    get_constant_raster_metadata,
)


class TestInputRange(TestCase):
    """Tests for InputRange NamedTuple."""

    def test_input_range_creation(self):
        """Test InputRange can be created with named parameters."""
        input_range = InputRange(min=0.0, max=100.0)
        self.assertEqual(input_range.min, 0.0)
        self.assertEqual(input_range.max, 100.0)

    def test_input_range_tuple_compatibility(self):
        """Test InputRange is compatible with tuple operations."""
        input_range = InputRange(min=0.0, max=100.0)
        min_val, max_val = input_range
        self.assertEqual(min_val, 0.0)
        self.assertEqual(max_val, 100.0)

    def test_input_range_immutable(self):
        """Test InputRange is immutable."""
        input_range = InputRange(min=0.0, max=100.0)
        with self.assertRaises(AttributeError):
            input_range.min = 50.0


class TestConstantRasterInfo(TestCase):
    """Tests for ConstantRasterInfo model."""

    def setUp(self):
        self.info = get_constant_raster_info()

    def test_creation(self):
        """Test ConstantRasterInfo creation."""
        self.assertEqual(self.info.normalized, 0.5)
        self.assertEqual(self.info.absolute, 50.0)


class TestConstantRasterComponent(TestCase):
    """Tests for ConstantRasterComponent model."""

    def setUp(self):
        self.component = get_constant_raster_component()

    def test_creation(self):
        """Test ConstantRasterComponent creation."""
        self.assertIsNotNone(self.component.value_info)
        self.assertIsNotNone(self.component.component)
        self.assertEqual(self.component.component_type, ModelComponentType.ACTIVITY)
        self.assertFalse(self.component.skip_raster)
        self.assertTrue(self.component.enabled)

    def test_identifier_generation(self):
        """Test identifier generation."""
        identifier = self.component.identifier()
        self.assertIsInstance(identifier, str)
        self.assertTrue(len(identifier) > 0)


class TestConstantRasterCollection(TestCase):
    """Tests for ConstantRasterCollection model."""

    def setUp(self):
        self.collection = get_constant_raster_collection()

    def test_creation(self):
        """Test ConstantRasterCollection creation."""
        self.assertEqual(self.collection.min_value, 0.0)
        self.assertEqual(self.collection.max_value, 100.0)
        self.assertEqual(self.collection.component_type, ModelComponentType.ACTIVITY)
        self.assertFalse(self.collection.skip_raster)
        self.assertEqual(len(self.collection.components), 1)

    def test_enabled_components(self):
        """Test getting enabled components."""
        enabled = self.collection.enabled_components()
        self.assertEqual(len(enabled), 1)

        # Disable a component
        self.collection.components[0].enabled = False
        enabled = self.collection.enabled_components()
        self.assertEqual(len(enabled), 0)

    def test_component_by_id(self):
        """Test retrieving component by ID."""
        component_id = self.collection.components[0].component_id
        found = self.collection.component_by_id(component_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.component_id, component_id)

    def test_add_component(self):
        """Test adding a component to collection."""
        activity2 = Activity(
            UUID(ACTIVITY_2_UUID_STR),
            "Test Activity 2",
            "Description for test activity 2",
            TEST_RASTER_PATH,
            LayerType.RASTER,
            True,
        )

        new_component = ConstantRasterComponent(
            value_info=get_constant_raster_info(),
            component=activity2,
            skip_raster=False,
            enabled=True,
        )
        result = self.collection.add_component(new_component)
        self.assertTrue(result)
        self.assertEqual(len(self.collection.components), 2)

    def test_add_duplicate_component(self):
        """Test adding duplicate component fails."""
        existing = self.collection.components[0]
        result = self.collection.add_component(existing)
        self.assertFalse(result)
        self.assertEqual(len(self.collection.components), 1)

    def test_remove_component(self):
        """Test removing a component from collection."""
        component_id = self.collection.components[0].component_id
        result = self.collection.remove_component(component_id)
        self.assertTrue(result)
        self.assertEqual(len(self.collection.components), 0)

    def test_validate_valid_range(self):
        """Test validation with valid min/max range."""
        result = self.collection.validate()
        self.assertTrue(result)

    def test_validate_invalid_min_max(self):
        """Test validation fails with invalid min/max."""
        self.collection.min_value = 100.0
        self.collection.max_value = 0.0
        with self.assertRaises(ValueError):
            self.collection.validate()

    def test_validate_with_metadata_constraints(self):
        """Test validation with metadata input range constraints."""
        metadata = get_constant_raster_metadata()
        # Collection range within metadata input range
        self.collection.min_value = 10.0
        self.collection.max_value = 90.0
        result = self.collection.validate(metadata)
        self.assertTrue(result)

        # Collection range outside metadata input range
        self.collection.min_value = -10.0
        with self.assertRaises(ValueError):
            self.collection.validate(metadata)

    def test_normalize_updates_range_from_components(self):
        """Test normalize() updates min/max from component absolute values."""
        # Add components with different absolute values
        component1 = get_constant_raster_component()
        component1.value_info.absolute = 20.0
        component1.enabled = True

        component2 = get_constant_raster_component()
        component2.value_info.absolute = 24.0
        component2.enabled = True

        component3 = get_constant_raster_component()
        component3.value_info.absolute = 50.0
        component3.enabled = True

        self.collection.components = [component1, component2, component3]

        # Call normalize
        self.collection.normalize()

        # Check that min/max are updated
        self.assertEqual(self.collection.min_value, 20.0)
        self.assertEqual(self.collection.max_value, 50.0)
        self.assertEqual(self.collection.allowable_min, 20.0)
        self.assertEqual(self.collection.allowable_max, 50.0)

    def test_normalize_ignores_disabled_components(self):
        """Test normalize() only considers enabled components."""
        component1 = get_constant_raster_component()
        component1.value_info.absolute = 5.0
        component1.enabled = False  # Disabled

        component2 = get_constant_raster_component()
        component2.value_info.absolute = 30.0
        component2.enabled = True

        component3 = get_constant_raster_component()
        component3.value_info.absolute = 40.0
        component3.enabled = True

        self.collection.components = [component1, component2, component3]

        # Call normalize
        self.collection.normalize()

        # Should use 30-40 range, ignoring the disabled component with value 5
        self.assertEqual(self.collection.min_value, 30.0)
        self.assertEqual(self.collection.max_value, 40.0)

    def test_len_and_iter(self):
        """Test collection length and iteration."""
        self.assertEqual(len(self.collection), 1)

        count = 0
        for component in self.collection:
            count += 1
            self.assertIsInstance(component, ConstantRasterComponent)
        self.assertEqual(count, 1)


class TestConstantRasterMetadata(TestCase):
    """Tests for ConstantRasterMetadata model."""

    def setUp(self):
        self.metadata = get_constant_raster_metadata()

    def test_creation(self):
        """Test ConstantRasterMetadata creation."""
        self.assertEqual(self.metadata.id, "test_metadata")
        self.assertEqual(self.metadata.display_name, "Test Constant Raster")
        self.assertIsNotNone(self.metadata.raster_collection)
        self.assertEqual(self.metadata.component_type, ModelComponentType.ACTIVITY)
        self.assertEqual(self.metadata.input_range.min, 0.0)
        self.assertEqual(self.metadata.input_range.max, 100.0)


class TestConstantRasterHelpers(TestCase):
    """Tests for constant raster helper functions."""

    def setUp(self):
        self.collection = get_constant_raster_collection()
        self.activity = get_activity()

    def test_collection_to_dict(self):
        """Test collection serialization."""
        result = constant_raster_collection_to_dict(self.collection)
        self.assertIsInstance(result, dict)
        self.assertIn(MIN_VALUE_ATTRIBUTE_KEY, result)
        self.assertIn(MAX_VALUE_ATTRIBUTE_KEY, result)
        self.assertIn(COMPONENT_TYPE_ATTRIBUTE, result)
        self.assertIn(ALLOWABLE_MIN_ATTRIBUTE, result)
        self.assertIn(ALLOWABLE_MAX_ATTRIBUTE, result)
        self.assertIn(SKIP_RASTER_ATTRIBUTE, result)
        self.assertIn(COMPONENTS_ATTRIBUTE, result)

    def test_collection_from_dict(self):
        """Test collection deserialization."""
        data = constant_raster_collection_to_dict(self.collection)
        restored = constant_raster_collection_from_dict(data, [self.activity])

        self.assertIsNotNone(restored)
        self.assertEqual(restored.min_value, self.collection.min_value)
        self.assertEqual(restored.max_value, self.collection.max_value)
        self.assertEqual(restored.component_type, self.collection.component_type)
        self.assertEqual(len(restored.components), len(self.collection.components))

    def test_collection_round_trip(self):
        """Test serialization and deserialization round trip."""
        data = constant_raster_collection_to_dict(self.collection)
        restored = constant_raster_collection_from_dict(data, [self.activity])

        self.assertEqual(restored.min_value, self.collection.min_value)
        self.assertEqual(restored.max_value, self.collection.max_value)
        self.assertEqual(restored.skip_raster, self.collection.skip_raster)
        self.assertEqual(len(restored.components), len(self.collection.components))

    def test_collection_to_dict_none(self):
        """Test serialization of None collection."""
        result = constant_raster_collection_to_dict(None)
        self.assertEqual(result, {})

    def test_collection_from_dict_empty(self):
        """Test deserialization of empty dict."""
        result = constant_raster_collection_from_dict({}, [])
        self.assertIsNone(result)


class TestYearsExperienceWidget(TestCase):
    """Tests for YearsExperienceWidget."""

    def setUp(self):
        self.widget = YearsExperienceWidget()

    def test_widget_creation(self):
        """Test widget can be created."""
        self.assertIsNotNone(self.widget)
        self.assertTrue(hasattr(self.widget, "sb_experience"))

    def test_reset_does_not_trigger_signals(self):
        """Test reset() blocks signals to prevent unwanted updates."""
        # Track signal emissions
        signal_count = 0

        def on_signal(component):
            nonlocal signal_count
            signal_count += 1

        self.widget.update_requested.connect(on_signal)

        # Set up a component with a value
        component = get_constant_raster_component()
        component.value_info.absolute = 50.0
        self.widget.raster_component = component

        # Reset should not trigger signals
        self.widget.reset()
        self.assertEqual(signal_count, 0)
        self.assertEqual(self.widget.sb_experience.value(), 0.0)

    def test_load_preserves_component_value(self):
        """Test load() correctly loads component values without triggering signals."""
        # Track signal emissions
        signal_count = 0

        def on_signal(component):
            nonlocal signal_count
            signal_count += 1

        self.widget.update_requested.connect(on_signal)

        # Create component with value
        component = get_constant_raster_component()
        component.value_info.absolute = 42.5
        self.widget.raster_component = component

        # Load should not trigger signals
        self.widget.load(component)
        self.assertEqual(signal_count, 0)
        self.assertEqual(self.widget.sb_experience.value(), 42.5)

    def test_reset_then_load_preserves_value(self):
        """Test that reset() followed by load() preserves the component value."""
        # Create component with value
        component = get_constant_raster_component()
        component.value_info.absolute = 35.0
        self.widget.raster_component = component

        # Reset and load
        self.widget.reset()
        self.widget.load(component)

        # Value should be preserved
        self.assertEqual(self.widget.sb_experience.value(), 35.0)
        self.assertEqual(component.value_info.absolute, 35.0)

    def test_switching_between_components_preserves_values(self):
        """Test switching between components preserves their values."""
        activity2 = Activity(
            UUID(ACTIVITY_2_UUID_STR),
            "Test Activity 2",
            "Description for test activity 2",
            TEST_RASTER_PATH,
            LayerType.RASTER,
            True,
        )

        activity3 = Activity(
            UUID(ACTIVITY_3_UUID_STR),
            "Test Activity 3",
            "Description for test activity 3",
            TEST_RASTER_PATH,
            LayerType.RASTER,
            True,
        )

        component1 = ConstantRasterComponent(
            value_info=ConstantRasterInfo(absolute=20.0),
            component=activity2,
            skip_raster=False,
            enabled=True,
        )

        component2 = ConstantRasterComponent(
            value_info=ConstantRasterInfo(absolute=50.0),
            component=activity3,
            skip_raster=False,
            enabled=True,
        )

        # Load first component
        self.widget.raster_component = component1
        self.widget.reset()
        self.widget.load(component1)
        self.assertEqual(self.widget.sb_experience.value(), 20.0)

        # Switch to second component
        self.widget.raster_component = component2
        self.widget.reset()
        self.widget.load(component2)
        self.assertEqual(self.widget.sb_experience.value(), 50.0)

        # Switch back to first component
        self.widget.raster_component = component1
        self.widget.reset()
        self.widget.load(component1)
        self.assertEqual(self.widget.sb_experience.value(), 20.0)

    def test_value_change_updates_component(self):
        """Test that changing widget value updates the component."""
        component = get_constant_raster_component()
        component.value_info.absolute = 0.0
        self.widget.raster_component = component

        # Simulate user changing value
        self.widget.sb_experience.setValue(75.0)

        # Component should be updated
        self.assertEqual(component.value_info.absolute, 75.0)

    def test_create_raster_component(self):
        """Test create_raster_component creates valid component."""
        activity = get_activity()
        component = YearsExperienceWidget.create_raster_component(activity)

        self.assertIsNotNone(component)
        self.assertIsNotNone(component.value_info)
        self.assertEqual(component.value_info.absolute, 0.0)
        self.assertEqual(component.component, activity)
        self.assertFalse(component.skip_raster)

    def test_create_metadata(self):
        """Test create_metadata creates valid metadata."""
        metadata = YearsExperienceWidget.create_metadata()

        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.id, "years_experience_activity")
        self.assertEqual(metadata.display_name, "Years of Experience")
        self.assertEqual(metadata.component_type, ModelComponentType.ACTIVITY)
        self.assertEqual(metadata.input_range.min, 0.0)
        self.assertEqual(metadata.input_range.max, 100.0)
