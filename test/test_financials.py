# -*- coding: utf-8 -*-
"""
Unit tests for financial NPV computations.
"""

from unittest import TestCase

from cplus_plugin.lib.financials import compute_discount_value

from model_data_for_testing import ACTIVITY_UUID_STR, get_activity_npv_collection
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestFinancialNpv(TestCase):
    """Tests for financial NPV computations."""

    def test_get_activity_npv_in_collection(self):
        """Test getting the activity NPV in the NPV collection."""
        npv_collection = get_activity_npv_collection()
        activity_npv = npv_collection.activity_npv(ACTIVITY_UUID_STR)

        self.assertIsNotNone(activity_npv)

    def test_discount_rate_calculation(self):
        """Test the computation of the discount rate."""
        discount_rate = compute_discount_value(70000, 48000, 3, 7.0)

        self.assertEqual(round(discount_rate, 2), 19215.65)

    def test_npv_min_max_calculation(self):
        """Test the computation of min/max NPV values in the collection."""
        npv_collection = get_activity_npv_collection()
        npv_collection.update_computed_normalization_range()

        self.assertEqual(round(npv_collection.minimum_value, 2), 38767.05)
        self.assertEqual(round(npv_collection.maximum_value, 2), 102307.69)

    def test_npv_normalization_status(self):
        """Test the status of NPV normalization."""
        npv_collection = get_activity_npv_collection()
        npv_collection.update_computed_normalization_range()
        normalization_status = npv_collection.normalize_npvs()

        self.assertTrue(normalization_status)

    def test_npv_normalization_value(self):
        """Test the status of NPV normalization."""
        npv_collection = get_activity_npv_collection()
        npv_collection.update_computed_normalization_range()
        _ = npv_collection.normalize_npvs()

        activity_npv_1 = npv_collection.activity_npv(ACTIVITY_UUID_STR)
        normalized_npv = round(activity_npv_1.params.normalized_npv, 4)
        self.assertEqual(normalized_npv, 0.0259)
