# -*- coding: utf-8 -*-
"""
Unit tests for model component widgets.
"""

from unittest import TestCase

from qgis.PyQt import QtCore


from cplus_plugin.gui.component_item_model import NcsPathwayItem
from cplus_plugin.gui.model_component_widget import (
    ImplementationModelComponentWidget,
    NcsComponentWidget,
)


from model_data_for_testing import (
    get_implementation_model,
    get_test_layer,
    get_valid_ncs_pathway,
    IMPLEMENTATION_MODEL_UUID_STR,
)
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestNcsComponentWidget(TestCase):
    """Tests for NcsComponentWidget."""

    def test_add_valid_ncs_pathway(self):
        """Assert a valid NCS pathway can be added to the widget."""
        ncs = get_valid_ncs_pathway()
        ncs_widget = NcsComponentWidget(PARENT)
        result = ncs_widget.add_ncs_pathway(ncs)
        self.assertTrue(result)

    def test_get_valid_ncs_pathways(self):
        """Assert number of NcsPathway objects retrieved."""
        valid_ncs = get_valid_ncs_pathway()
        ncs_widget = NcsComponentWidget(PARENT)
        _ = ncs_widget.add_ncs_pathway(valid_ncs)
        pathways = ncs_widget.pathways()
        self.assertEqual(len(pathways), 1)

    def test_clear_ncs_pathways(self):
        """Assert NcsPathway objects are cleared."""
        valid_ncs = get_valid_ncs_pathway()
        ncs_widget = NcsComponentWidget(PARENT)
        _ = ncs_widget.add_ncs_pathway(valid_ncs)
        ncs_widget.clear()
        pathways = ncs_widget.pathways()
        self.assertEqual(len(pathways), 0)


class TestImplementationModelComponentWidget(TestCase):
    """Tests for ImplementationModelComponentWidget."""

    def test_add_implementation_model(self):
        """Assert an ImplementationModel object can be added
        to the widget.
        """
        im_model = get_implementation_model()
        im_widget = ImplementationModelComponentWidget(PARENT)
        result = im_widget.add_implementation_model(im_model)
        self.assertTrue(result)

    def test_add_implementation_model_with_layer(self):
        """Assert an ImplementationModel object with a layer
        can be added to the widget.
        """
        im_model = get_implementation_model()
        layer = get_test_layer()
        im_widget = ImplementationModelComponentWidget(PARENT)
        result = im_widget.add_implementation_model(im_model, layer)
        self.assertTrue(result)

    def test_get_implementation_models(self):
        """Assert number of ImplementationModel objects retrieved."""
        im_model = get_implementation_model()
        im_widget = ImplementationModelComponentWidget(PARENT)
        _ = im_widget.add_implementation_model(im_model)
        imp_models = im_widget.models()
        self.assertEqual(len(imp_models), 1)

    def test_clear_implementation_models(self):
        """Assert ImplementationModel objects are cleared."""
        im_model = get_implementation_model()
        im_widget = ImplementationModelComponentWidget(PARENT)
        _ = im_widget.add_implementation_model(im_model)
        im_widget.clear()
        imp_models = im_widget.models()
        self.assertEqual(len(imp_models), 0)

    def test_can_add_ncs_pathway_items(self):
        """Assert ncsPathwayItem objects can be added to the
        widget to an implementation model without a layer.
        """
        im_model = get_implementation_model()
        im_model.clear_layer()
        im_widget = ImplementationModelComponentWidget(PARENT)
        _ = im_widget.add_implementation_model(im_model)

        # Select the added implementation model.
        sel_model = im_widget.selection_model
        item_model = im_widget.item_model
        model_idx = item_model.index_by_uuid(IMPLEMENTATION_MODEL_UUID_STR)
        sel_model.select(model_idx, QtCore.QItemSelectionModel.ClearAndSelect)

        # Now we can add the NcsPathwayItem
        ncs = get_valid_ncs_pathway()
        ncs_item = NcsPathwayItem(ncs)
        result = im_widget.add_ncs_pathway_items([ncs_item])
        self.assertTrue(result)

    def test_cannot_add_ncs_pathway_items(self):
        """Assert ncsPathwayItem objects cannot be added to the
        widget as the implementation model has a layer defined.
        """
        im_model = get_implementation_model()
        im_widget = ImplementationModelComponentWidget(PARENT)
        _ = im_widget.add_implementation_model(im_model)

        # Select the added implementation model.
        sel_model = im_widget.selection_model
        item_model = im_widget.item_model
        model_idx = item_model.index_by_uuid(IMPLEMENTATION_MODEL_UUID_STR)
        sel_model.select(model_idx, QtCore.QItemSelectionModel.ClearAndSelect)

        # Now we can add the NcsPathwayItem
        ncs = get_valid_ncs_pathway()
        ncs_item = NcsPathwayItem(ncs)
        result = im_widget.add_ncs_pathway_items([ncs_item])
        self.assertFalse(result)
