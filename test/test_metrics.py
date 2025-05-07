# -*- coding: utf-8 -*-
"""
Unit tests for metrics operations.
"""

import unittest
from unittest import TestCase

from qgis.core import QgsExpression

from processing.core.Processing import Processing

from cplus_plugin.conf import settings_manager, Settings
from cplus_plugin.definitions.defaults import BASE_PLUGIN_NAME
from cplus_plugin.gui.metrics_builder_dialog import ActivityMetricsBuilder
from cplus_plugin.gui.metrics_builder_model import MetricColumnListItem
from cplus_plugin.lib.reports.metrics import (
    create_metrics_expression_context,
    evaluate_activity_metric,
    FUNC_ACTIVITY_NPV,
    FUNC_PWL_IMPACT,
    FUNC_MEAN_BASED_IC,
    register_metric_functions,
    unregister_metric_functions,
)
from cplus_plugin.models.base import DataSourceType
from cplus_plugin.models.helpers import create_metric_configuration
from cplus_plugin.models.report import ActivityContextInfo

from model_data_for_testing import (
    NCS_PATHWAY_1_NPV,
    get_activity,
    get_ncs_pathway_npv_collection,
    get_metric_column,
    get_protected_ncs_pathways,
    get_reference_irrecoverable_carbon_path,
    METRIC_COLUMN_NAME,
    METRIC_CONFIGURATION_DICT,
)
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


@unittest.skip("Disabled as metrics builder logic will be refactored.")
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


@unittest.skip(
    "Disabled as metrics builder logic, including expressions, will be refactored."
)
class TestMetricExpressions(TestCase):
    """Testing management of metrics in QGIS expression environment."""

    def setUp(self):
        Processing.initialize()

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

        npv_collection = get_ncs_pathway_npv_collection()
        npv_collection.update_computed_normalization_range()
        _ = npv_collection.normalize_npvs()
        settings_manager.save_npv_collection(npv_collection)

        reference_area = 2000
        reference_activity_npv = NCS_PATHWAY_1_NPV * reference_area

        register_metric_functions()
        context = create_metrics_expression_context()
        activity_context_info = ActivityContextInfo(get_activity(), reference_area)

        result = evaluate_activity_metric(
            context, activity_context_info, f"{FUNC_ACTIVITY_NPV}()"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.value, reference_activity_npv)

    def test_activity_pwl_impact_expression_function(self):
        """Test the calculation of the PWL impact of an activity
        using an expression function.
        """
        reference_area = 2000
        custom_jobs_per_ha = 1.5

        register_metric_functions()
        context = create_metrics_expression_context()
        activity_context_info = ActivityContextInfo(get_activity(), reference_area)

        result = evaluate_activity_metric(
            context, activity_context_info, f"{FUNC_PWL_IMPACT}({custom_jobs_per_ha!s})"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.value, reference_area * custom_jobs_per_ha)

    def test_activity_irrecoverable_carbon_expression_function(self):
        """Test the calculation of an activity's irrecoverable carbon
        using an expression function.
        """
        # We first need to configure and save the activity
        activity = get_activity()
        for protected_pathway in get_protected_ncs_pathways():
            settings_manager.save_ncs_pathway(protected_pathway)
            activity.add_ncs_pathway(protected_pathway)

        settings_manager.save_activity(activity)

        # Save the project extent for analyzing irrecoverable carbon
        extent_box = [
            30.897412864,
            30.902802731,
            -24.699751899,
            -24.694362032,
        ]
        settings_manager.set_value(Settings.SCENARIO_EXTENT, extent_box)

        # Save data source type and path to the reference irrecoverable carbon dataset
        ic_reference_path = get_reference_irrecoverable_carbon_path()
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_SOURCE_TYPE, DataSourceType.LOCAL.value
        )
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_LOCAL_SOURCE, ic_reference_path
        )

        register_metric_functions()
        context = create_metrics_expression_context()
        activity_context_info = ActivityContextInfo(activity, 3000)

        result = evaluate_activity_metric(
            context, activity_context_info, f"{FUNC_MEAN_BASED_IC}()"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.value, 1224)
