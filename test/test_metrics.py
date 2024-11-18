# -*- coding: utf-8 -*-
"""
Unit tests for metrics operations.
"""

import os
import typing
from unittest import TestCase

from qgis.core import (
    QgsRasterLayer,
)

from cplus_plugin.conf import settings_manager, Settings
from cplus_plugin.gui.metrics_builder_dialog import ActivityMetricsBuilder
from cplus_plugin.gui.metrics_builder_model import MetricColumnListItem
from cplus_plugin.models.helpers import create_metric_configuration

from model_data_for_testing import (
    ACTIVITY_1_NPV,
    ACTIVITY_UUID_STR,
    get_activity,
    get_activity_npv_collection,
    get_metric_column,
    METRIC_COLUMN_NAME,
    METRIC_CONFIGURATION_DICT,
)
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestMetricsBuilder(TestCase):
    """Tests for metrics builder."""

    def test_metrics_wizard_add_column(self):
        """Test adding a new column in the metrics wizard."""
        metrics_builder = ActivityMetricsBuilder(PARENT, [get_activity()])
        column_item = MetricColumnListItem(get_metric_column())
        metrics_builder.add_column_item(column_item)

        list_model = metrics_builder.column_list_model
        # By default the builder adds an area column
        self.assertEqual(len(list_model.column_items), 2)

    def test_metrics_wizard_remove_column(self):
        """Test removing a column in the metrics wizard."""
        metrics_builder = ActivityMetricsBuilder(PARENT, [get_activity()])
        column_item = MetricColumnListItem(get_metric_column())
        metrics_builder.add_column_item(column_item)

        metrics_builder.remove_column(METRIC_COLUMN_NAME)

        list_model = metrics_builder.column_list_model
        # Area column still remains
        self.assertEqual(len(list_model.column_items), 1)

    def test_get_metric_configuration(self):
        """Test fetching of a metric configuration from the metrics builder."""
        metrics_builder = ActivityMetricsBuilder(PARENT, [get_activity()])
        column_item = MetricColumnListItem(get_metric_column())
        metrics_builder.add_column_item(column_item)

        configuration = metrics_builder.metric_configuration
        self.assertTrue(configuration.is_valid())

    def test_load_metric_configuration(self):
        """Test loading of a metric configuration in the metrics builder."""
        metrics_builder = ActivityMetricsBuilder(PARENT, [get_activity()])

        configuration = create_metric_configuration(
            METRIC_CONFIGURATION_DICT, [get_activity()]
        )

        self.assertTrue(configuration.is_valid())

        metrics_builder.load_configuration(configuration)
        list_model = metrics_builder.column_list_model
        self.assertEqual(len(list_model.column_items), 2)
