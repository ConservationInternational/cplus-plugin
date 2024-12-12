# -*- coding: utf-8 -*-
"""
Unit tests for metrics operations.
"""

import os
import typing
from unittest import TestCase

from qgis.core import QgsExpression

from cplus_plugin.conf import settings_manager, Settings
from cplus_plugin.definitions.defaults import BASE_PLUGIN_NAME
from cplus_plugin.gui.metrics_builder_dialog import ActivityMetricsBuilder
from cplus_plugin.gui.metrics_builder_model import MetricColumnListItem
from cplus_plugin.lib.reports.metrics import (
    create_metrics_expression_context,
    evaluate_activity_metric,
    FUNC_ACTIVITY_NPV,
    register_metric_functions,
    unregister_metric_functions,
)
from cplus_plugin.models.helpers import create_metric_configuration
from cplus_plugin.models.report import ActivityContextInfo

from model_data_for_testing import (
    ACTIVITY_1_NPV,
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
        # By default, the builder adds an area column
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


class TestMetricExpressions(TestCase):
    """Testing management of metrics in QGIS expression environment."""

    def test_metrics_scope_in_expression_context(self):
        """Verify the metrics scope exists in a metrics expression context."""
        context = create_metrics_expression_context()
        metrics_scope_index = context.indexOfScope(BASE_PLUGIN_NAME)

        self.assertNotEqual(metrics_scope_index, -1)

    def test_metric_expression_function_registration(self):
        """Testing the registration of expression functions."""
        register_metric_functions()

        self.assertTrue(QgsExpression.isFunctionName(FUNC_ACTIVITY_NPV))

    def test_unregister_metric_expression_functions(self):
        """Test unregister of expression functions."""
        register_metric_functions()

        unregister_metric_functions()

        self.assertFalse(QgsExpression.isFunctionName(FUNC_ACTIVITY_NPV))

    def test_activity_npv_expression_function(self):
        """Test the calculation of an activity's NPV using the expression function."""
        # We first need to save the activity and corresponding NPV in settings
        settings_manager.save_activity(get_activity())

        npv_collection = get_activity_npv_collection()
        npv_collection.update_computed_normalization_range()
        _ = npv_collection.normalize_npvs()
        settings_manager.save_npv_collection(npv_collection)

        reference_area = 2000
        reference_activity_npv = ACTIVITY_1_NPV * reference_area

        register_metric_functions()
        context = create_metrics_expression_context()
        activity_context_info = ActivityContextInfo(get_activity(), reference_area)

        result = evaluate_activity_metric(
            context, activity_context_info, f"{FUNC_ACTIVITY_NPV}()"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.value, reference_activity_npv)
