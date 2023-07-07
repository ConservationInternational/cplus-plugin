# -*- coding: utf-8 -*-
"""
Unit tests for GUI item models for model components.
"""


from unittest import TestCase

from cplus_plugin.models.helpers import create_ncs_pathway, ncs_pathway_to_dict

from model_data_for_testing import get_valid_ncs_pathway, NCS_PATHWAY_DICT


class TestDataModelHelpers(TestCase):
    def setUp(self):
        self.ncs = get_valid_ncs_pathway()
