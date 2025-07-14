# -*- coding: utf-8 -*-
"""
Unit tests for data model helpers
"""

from unittest import TestCase

from cplus_core.models.base import NcsPathway
from cplus_plugin.models.helpers import (
    clone_layer_component,
    create_metric_configuration,
    create_ncs_pathway,
    metric_configuration_to_dict,
    ncs_pathway_to_dict,
)

from model_data_for_testing import (
    get_activity,
    get_metric_configuration,
    get_valid_ncs_pathway,
    METRIC_CONFIGURATION_DICT,
    NCS_PATHWAY_DICT,
)


class TestDataModelHelpers(TestCase):
    def setUp(self):
        self.ncs = get_valid_ncs_pathway()

    def test_ncs_pathway_to_dict(self):
        """Assert an NcsPathway object can be converted into
        the corresponding dictionary.
        """
        ncs_dict = ncs_pathway_to_dict(self.ncs, False)
        self.assertDictEqual(ncs_dict, NCS_PATHWAY_DICT)

    def test_create_ncs_pathway(self):
        """Compare two NcsPathway objects for equality."""
        ref_ncs = create_ncs_pathway(NCS_PATHWAY_DICT)
        self.assertTrue(ref_ncs == self.ncs)

    def test_clone_ncs_pathway(self):
        """Assert cloning of an NCS pathway object."""
        cloned_ncs = clone_layer_component(self.ncs, NcsPathway)
        self.assertIsNotNone(cloned_ncs)
        self.assertTrue(self.ncs.uuid == cloned_ncs.uuid)
        self.assertTrue(cloned_ncs.to_map_layer().isValid())

    def test_deserialize_metric_configuration(self):
        """Test the creation of a metric configuration from
        the equivalent dict representation.
        """
        metric_configuration = create_metric_configuration(
            METRIC_CONFIGURATION_DICT, [get_activity()]
        )

        self.assertIsNotNone(metric_configuration)
        self.assertTrue(metric_configuration.is_valid())
        self.assertEqual(len(metric_configuration.metric_columns), 2)

    def test_serialize_metric_configuration(self):
        """Test serializing a metric configuration object to a dict."""
        metric_configuration = get_metric_configuration()

        metric_configuration_dict = metric_configuration_to_dict(metric_configuration)

        self.assertEqual(len(metric_configuration_dict["metric_columns"]), 2)
        self.assertEqual(len(metric_configuration_dict["activity_metrics"]), 1)
        self.assertEqual(len(metric_configuration_dict["activity_identifiers"]), 1)
