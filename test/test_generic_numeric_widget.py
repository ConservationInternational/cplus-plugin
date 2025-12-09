# -*- coding: utf-8 -*-
"""
Unit tests for GenericNumericWidget.
"""

from unittest import TestCase
from uuid import uuid4

from qgis.PyQt import QtWidgets

from cplus_plugin.gui.constant_rasters.constant_raster_widgets import (
    GenericNumericWidget,
)
from cplus_plugin.models.base import ModelComponentType, Activity, LayerType
from cplus_plugin.models.constant_raster import (
    ConstantRasterMetadata,
    ConstantRasterComponent,
    ConstantRasterInfo,
    InputRange,
)


class TestGenericNumericWidget(TestCase):
    """Test cases for GenericNumericWidget."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            self.app = QtWidgets.QApplication([])

    def test_widget_initialization(self):
        """Test widget initializes with correct parameters."""
        widget = GenericNumericWidget(
            label="Test Label",
            min_value=0.0,
            max_value=50.0,
            metadata_id="test_id",
        )

        self.assertIsNotNone(widget)
        self.assertEqual(widget.label, "Test Label")
        self.assertEqual(widget.min_value, 0.0)
        self.assertEqual(widget.max_value, 50.0)
        self.assertEqual(widget.metadata_id, "test_id")

    def test_spinbox_configuration(self):
        """Test spinbox is configured correctly."""
        widget = GenericNumericWidget(
            label="Test",
            min_value=10.0,
            max_value=90.0,
            default_value=10.0,
            metadata_id="test",
        )

        self.assertEqual(widget.spin_box.minimum(), 10.0)
        self.assertEqual(widget.spin_box.maximum(), 90.0)
        self.assertEqual(widget.spin_box.decimals(), 1)
        self.assertEqual(widget.spin_box.value(), 10.0)

    def test_spinbox_decimals_hardcoded(self):
        """Test spinbox always has 1 decimal place."""
        widget = GenericNumericWidget(
            label="Test",
            min_value=0.0,
            max_value=100.0,
            metadata_id="test",
        )

        self.assertEqual(widget.spin_box.decimals(), 1)

    def test_create_metadata_returns_valid_metadata(self):
        """Test create_metadata returns valid ConstantRasterMetadata."""
        metadata = GenericNumericWidget.create_metadata()

        self.assertIsInstance(metadata, ConstantRasterMetadata)
        self.assertTrue(metadata.user_defined)
        self.assertEqual(metadata.component_type, ModelComponentType.ACTIVITY)

    def test_create_metadata_collection_defaults(self):
        """Test create_metadata creates collection with correct defaults."""
        metadata = GenericNumericWidget.create_metadata()

        collection = metadata.raster_collection
        self.assertIsNotNone(collection)
        self.assertEqual(collection.min_value, 0.0)
        self.assertEqual(collection.max_value, 100.0)
        self.assertEqual(collection.component_type, ModelComponentType.ACTIVITY)

    def test_create_metadata_input_range(self):
        """Test create_metadata sets input range correctly."""
        metadata = GenericNumericWidget.create_metadata()

        self.assertIsInstance(metadata.input_range, InputRange)
        self.assertEqual(metadata.input_range.min, 0.0)
        self.assertEqual(metadata.input_range.max, 100.0)

    def test_create_raster_component(self):
        """Test create_raster_component creates valid component."""
        widget = GenericNumericWidget(
            label="Test",
            min_value=0.0,
            max_value=100.0,
            metadata_id="test",
        )

        activity = Activity(
            uuid=uuid4(),
            name="Test Activity",
            description="Test",
            path="",
            layer_type=LayerType.RASTER,
        )

        component = widget.create_raster_component(activity)

        self.assertIsInstance(component, ConstantRasterComponent)
        self.assertEqual(component.component.uuid, activity.uuid)
        self.assertIsInstance(component.value_info, ConstantRasterInfo)

    def test_create_raster_component_default_value(self):
        """Test create_raster_component sets default value to configured default."""
        widget = GenericNumericWidget(
            label="Test",
            min_value=0.0,
            max_value=100.0,
            default_value=0.0,
            metadata_id="test",
        )

        activity = Activity(
            uuid=uuid4(),
            name="Test Activity",
            description="Test",
            path="",
            layer_type=LayerType.RASTER,
        )

        component = widget.create_raster_component(activity)

        self.assertEqual(component.value_info.normalized, 0.0)
        self.assertEqual(component.value_info.absolute, 0.0)

    def test_reset_clears_to_default(self):
        """Test reset() sets spinbox to default value."""
        widget = GenericNumericWidget(
            label="Test",
            min_value=5.0,
            max_value=50.0,
            default_value=10.0,
            metadata_id="test",
        )

        widget.spin_box.setValue(25.0)
        widget.reset()

        self.assertEqual(widget.spin_box.value(), 10.0)

    def test_load_populates_from_component(self):
        """Test load() populates spinbox from component."""
        widget = GenericNumericWidget(
            label="Test",
            min_value=0.0,
            max_value=100.0,
            metadata_id="test",
        )

        activity = Activity(
            uuid=uuid4(),
            name="Test",
            description="Test",
            path="",
            layer_type=LayerType.RASTER,
        )
        component = ConstantRasterComponent(
            component=activity,
            value_info=ConstantRasterInfo(normalized=42.5, absolute=42.5),
            skip_raster=False,
        )

        widget.load(component)

        self.assertEqual(widget.spin_box.value(), 42.5)
