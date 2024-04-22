# -*- coding: utf-8 -*-
"""
Unit tests for data validation module.
"""

from unittest import TestCase

from model_data_for_testing import (
    get_activity,
    get_invalid_ncs_pathway,
    get_ncs_pathway_with_invalid_carbon,
    get_ncs_pathway_with_valid_carbon,
    get_valid_ncs_pathway,
    VALID_NCS_UUID_STR,
)


class TestDataValidation(TestCase):
    def setUp(self):
        self.ncs = get_valid_ncs_pathway()
        self.invalid_ncs = get_invalid_ncs_pathway()

    def test_to_map_layer(self):
        """Confirm that the map layer is not None."""
        map_layer = self.ncs.to_map_layer()
        self.assertIsNotNone(map_layer)
