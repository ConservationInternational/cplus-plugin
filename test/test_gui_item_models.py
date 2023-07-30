# -*- coding: utf-8 -*-
"""
Unit tests for GUI item models for model components.
"""

from unittest import TestCase

from cplus_plugin.gui.component_item_model import (
    IMItemModel,
    ImplementationModelItem,
    NcsPathwayItem,
    NcsPathwayItemModel,
)

from model_data_for_testing import (
    get_implementation_model,
    get_invalid_ncs_pathway,
    get_test_layer,
    get_valid_ncs_pathway,
    IMPLEMENTATION_MODEL_UUID_STR,
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


class TestIMItemModel(TestCase):
    """Tests for the implementation model item model."""

    def setUp(self):
        self.ncs = get_valid_ncs_pathway()
        self.invalid_ncs = get_invalid_ncs_pathway()

    def test_add_implementation_model(self):
        """Assert an implementation model can be added."""
        im_item_model = IMItemModel(PARENT)
        result = im_item_model.add_implementation_model(get_implementation_model())
        self.assertTrue(result)

    def test_model_has_items(self):
        """Assert the item model actually contains items."""
        im_item_model = IMItemModel(PARENT)
        _ = im_item_model.add_implementation_model(get_implementation_model())
        models = im_item_model.models()
        self.assertEqual(len(models), 1)

    def test_remove_implementation_model(self):
        """Assert an implementation model can be removed."""
        im_item_model = IMItemModel(PARENT)
        _ = im_item_model.add_implementation_model(get_implementation_model())
        result = im_item_model.remove_implementation_model(
            IMPLEMENTATION_MODEL_UUID_STR
        )
        self.assertTrue(result)

    def test_add_implementation_model_with_layer(self):
        """Assert can add map layer to implementation model."""
        im_item_model = IMItemModel(PARENT)
        im_model = get_implementation_model()
        layer = get_test_layer()
        result = im_item_model.add_implementation_model(im_model, layer)
        self.assertTrue(result)

    def test_remove_implementation_model_with_layer(self):
        """Assert an implementation model with layer can be removed."""
        im_item_model = IMItemModel(PARENT)
        im_model = get_implementation_model()
        layer = get_test_layer()
        _ = im_item_model.add_implementation_model(im_model, layer)
        result = im_item_model.remove_implementation_model(
            IMPLEMENTATION_MODEL_UUID_STR
        )
        self.assertTrue(result)
