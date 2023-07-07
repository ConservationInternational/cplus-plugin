# -*- coding: utf-8 -*-
"""
Unit tests for model component widgets.
"""

from unittest import TestCase

from cplus_plugin.gui.model_component_widget import (
    ImplementationModelComponentWidget,
    NcsComponentWidget,
)


from model_data_for_testing import (
    get_implementation_model,
    get_invalid_ncs_pathway,
    get_valid_ncs_pathway,
    IMPLEMENTATION_MODEL_UUID_STR,
    VALID_NCS_UUID_STR,
)
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestNcsComponentWidget(TestCase):
    """Tests for the NcsPathwayItemModel."""

    def test_add_valid_ncs_pathway(self):
        """Assert a valid NCS pathway can be added to the widget."""
        ncs = get_valid_ncs_pathway()
        ncs_widget = NcsComponentWidget(PARENT)
        result = ncs_widget.add_ncs_pathway(ncs)
        self.assertTrue(result)

    def test_add_invalid_ncs_pathway(self):
        """Assert an invalid NCS pathway cannot be added to the widget."""
        ncs = get_invalid_ncs_pathway()
        ncs_widget = NcsComponentWidget(PARENT)
        result = ncs_widget.add_ncs_pathway(ncs)
        self.assertFalse(result)

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
