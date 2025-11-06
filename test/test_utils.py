# coding=utf-8
"""Tests for the CPLUS plugin utilities.

"""
import os
import unittest
import uuid

from cplus_plugin.utils import open_documentation, create_connectivity_raster
from qgis.core import QgsRasterLayer


class CplusPluginUtilTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_open_documentation(self):
        # Checks function for opening documentation in a browser
        result = open_documentation()

        # TODO work out a web browser for testing this utility
        # at the moment only these checks will pass
        self.assertIsNotNone(result)
        self.assertFalse(result)

    def test_create_connectivity_layer(self):
        activities_layer_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "activities", "layers"
        )

        activity_layer_path_1 = os.path.join(
            activities_layer_directory, "test_activity_2.tif"
        )

        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "activities"
        )

        connectivity_path = os.path.join(
            f"{base_dir}",
            f"connectivity_{str(uuid.uuid4())[:4]}.tif",
        )

        # Before normalization, check if the activity layer stats are correct
        activity_layer = QgsRasterLayer(activity_layer_path_1, "test_activity_2")
        first_layer_stat = activity_layer.dataProvider().bandStatistics(1)

        self.assertEqual(first_layer_stat.minimumValue, 0.0)
        self.assertEqual(first_layer_stat.maximumValue, 1.0)

        ok, logs = create_connectivity_raster(
            activity_layer_path_1, output_raster_path=connectivity_path
        )

        self.assertTrue(ok)
        self.assertTrue(os.path.exists(connectivity_path))

        connectivity_layer = QgsRasterLayer(connectivity_path, "Layer")

        result_stat = connectivity_layer.dataProvider().bandStatistics(1)
        self.assertAlmostEqual(result_stat.minimumValue, 0.064631, places=6)
        self.assertEqual(result_stat.maximumValue, 1.0)
