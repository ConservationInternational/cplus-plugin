# -*- coding: utf-8 -*-
"""
Unit test for pilot extent check.
"""
import os
from unittest import TestCase

from qgis.core import QgsRectangle

from cplus_plugin.lib.extent_check import PilotExtentCheck

from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestPilotExtentCheck(TestCase):
    """Tests for pilot extent check."""

    def test_aoi_outside_pilot_area(self):
        """Assert a false result when canvas AOI is outside pilot area."""
        extent_check = PilotExtentCheck()
        test_extent = QgsRectangle(30, -25, 33, -22)
        CANVAS.zoomToFeatureExtent(test_extent)
        self.assertFalse(extent_check.is_within_pilot_area())

    def test_aoi_within_pilot_area(self):
        """Assert a true result when canvas AOI is within pilot area."""
        extent_check = PilotExtentCheck()
        test_extent = QgsRectangle(31.5, -24.8, 31.8, -24.5)
        CANVAS.zoomToFeatureExtent(test_extent)
        self.assertTrue(extent_check.is_within_pilot_area())
