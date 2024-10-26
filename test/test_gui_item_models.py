# -*- coding: utf-8 -*-
"""
Unit tests for GUI item models for model components.
"""

from unittest import TestCase

from cplus_plugin.gui.carbon_item_model import CarbonLayerModel

from cplus_plugin.gui.component_item_model import (
    ActivityItemModel,
    ActivityItem,
    NcsPathwayItem,
    NcsPathwayItemModel,
)

from model_data_for_testing import (
    get_activity,
    get_invalid_ncs_pathway,
    get_test_layer,
    get_valid_ncs_pathway,
    ACTIVITY_UUID_STR,
    TEST_RASTER_PATH,
    VALID_NCS_UUID_STR,
)
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestNcsPathwayItemModel(TestCase):
    """Tests for the NcsPathwayItemModel."""

    def setUp(self):
        self.ncs = get_valid_ncs_pathway()
        self.invalid_ncs = get_invalid_ncs_pathway()

    def test_add_valid_ncs_pathway(self):
        """Assert a valid NCS pathway object can be added."""
        ncs_item_model = NcsPathwayItemModel(PARENT)
        result = ncs_item_model.add_ncs_pathway(self.ncs)
        self.assertTrue(result)

    def test_add_duplicate_ncs_pathway(self):
        """Assert a duplicate NCS pathway object cannot be added."""
        ncs_item_model = NcsPathwayItemModel(PARENT)
        _ = ncs_item_model.add_ncs_pathway(self.ncs)
        result = ncs_item_model.add_ncs_pathway(self.ncs)
        self.assertFalse(result)

    def test_get_valid_pathways(self):
        """Assert get only the valid NcsPathway objects in the model."""
        ncs_item_model = NcsPathwayItemModel(PARENT)
        _ = ncs_item_model.add_ncs_pathway(self.invalid_ncs)
        _ = ncs_item_model.add_ncs_pathway(self.ncs)
        valid_ncs_pathways = ncs_item_model.pathways(True)
        self.assertEqual(len(valid_ncs_pathways), 1)

    def test_remove_ncs_pathway(self):
        """Assert successful removal of an NcsPathway object."""
        ncs_item_model = NcsPathwayItemModel(PARENT)
        _ = ncs_item_model.add_ncs_pathway(self.ncs)
        result = ncs_item_model.remove_ncs_pathway(VALID_NCS_UUID_STR)
        self.assertTrue(result)


class TestActivityItemModel(TestCase):
    """Tests for the activity item model."""

    def setUp(self):
        self.ncs = get_valid_ncs_pathway()
        self.invalid_ncs = get_invalid_ncs_pathway()

    def test_add_implementation_model(self):
        """Assert an activity can be added."""
        activity_item_model = ActivityItemModel(PARENT)
        result = activity_item_model.append_activity(get_activity())
        self.assertTrue(result)

    def test_model_has_items(self):
        """Assert the item model actually contains items."""
        activity_item_model = ActivityItemModel(PARENT)
        _ = activity_item_model.append_activity(get_activity())
        activities = activity_item_model.activities()
        self.assertEqual(len(activities), 1)

    def test_remove_activity(self):
        """Assert an activity can be removed."""
        activity_item_model = ActivityItemModel(PARENT)
        _ = activity_item_model.append_activity(get_activity())
        result = activity_item_model.remove_activity(ACTIVITY_UUID_STR)
        self.assertTrue(result)

    def test_add_activity_with_layer(self):
        """Assert can add map layer to an activity."""
        activity_item_model = ActivityItemModel(PARENT)
        activity = get_activity()
        layer = get_test_layer()
        result = activity_item_model.append_activity(activity, layer)
        self.assertTrue(result)

    def test_remove_activity_with_layer(self):
        """Assert an activity with layer can be removed."""
        activity_item_model = ActivityItemModel(PARENT)
        activity = get_activity()
        layer = get_test_layer()
        _ = activity_item_model.append_activity(activity, layer)
        result = activity_item_model.remove_activity(ACTIVITY_UUID_STR)
        self.assertTrue(result)


class TestCarbonItemModel(TestCase):
    """Tests for the NCS carbon item model."""

    def test_add_carbon_layer(self):
        """Assert a carbon layer can be added."""
        carbon_model = CarbonLayerModel()
        result = carbon_model.add_carbon_layer(TEST_RASTER_PATH)
        self.assertTrue(result)

    def test_carbon_layer_index(self):
        """Assert a valid model index is returned for an existing path."""
        carbon_model = CarbonLayerModel()
        _ = carbon_model.add_carbon_layer(TEST_RASTER_PATH)
        index = carbon_model.carbon_layer_index(TEST_RASTER_PATH)
        self.assertTrue(index.isValid())

    def test_carbon_layer_exists(self):
        """Assert the model contains an existing carbon layer."""
        carbon_model = CarbonLayerModel()
        _ = carbon_model.add_carbon_layer(TEST_RASTER_PATH)
        result = carbon_model.contains_layer_path(TEST_RASTER_PATH)
        self.assertTrue(result)

    def test_number_of_carbon_layer_items(self):
        """Assert the number of carbon layer items in the model."""
        carbon_model = CarbonLayerModel()
        _ = carbon_model.add_carbon_layer(TEST_RASTER_PATH)
        num_layers = len(carbon_model.carbon_paths())
        self.assertEqual(num_layers, 1)
