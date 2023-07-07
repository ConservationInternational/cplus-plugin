# -*- coding: utf-8 -*-
"""
Unit tests for data model helpers
"""

from unittest import TestCase

from cplus_plugin.models.helpers import create_ncs_pathway, ncs_pathway_to_dict

from model_data_for_testing import get_valid_ncs_pathway, NCS_PATHWAY_DICT


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
