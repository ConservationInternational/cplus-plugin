# -*- coding: utf-8 -*-
"""
Unit tests for base data models.
"""

from unittest import TestCase

from test.model_data_for_testing import (
    get_invalid_ncs_pathway,
    get_valid_ncs_pathway
)
from test.utilities_for_testing import get_qgis_app


QGIS_APP = get_qgis_app()


class TestNcsPathway(TestCase):
    def setUp(self):
        self.ncs = get_valid_ncs_pathway()

    def test_to_map_layer(self):
        """Confirm that the map layer is not None."""
        map_layer = self.ncs.to_map_layer()
        self.assertIsNotNone(map_layer)

    def test_ncs_is_valid(self):
        """Confirm NCS item is valid."""
        self.assertTrue(self.ncs.is_valid())

    def test_ncs_is_not_valid(self):
        """Confirm NCS item is not valid."""
        invalid_ncs = get_invalid_ncs_pathway()
        self.assertFalse(invalid_ncs.is_valid())
