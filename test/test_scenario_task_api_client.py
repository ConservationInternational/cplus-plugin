# coding=utf-8
"""Tests for the plugin processing tasks in server side

"""

import unittest

import os
import uuid
import datetime

from processing.core.Processing import Processing

from cplus_plugin.conf import settings_manager, Settings
from cplus_plugin.api.scenario_task_api_client import (
    ScenarioAnalysisTaskApiClient,
    generate_layer_mapping_identifier,
    generate_client_id,
)
from model_data_for_testing import get_valid_ncs_pathway, get_test_scenario


class ScenarioAnalysisTaskApiClientTest(unittest.TestCase):
    def setUp(self):
        Processing.initialize()
        self.pathway = get_valid_ncs_pathway()
        self.base_dir = os.path.dirname(__file__)

    def test_generate_layer_mapping_id(self):
        mapping_id = generate_layer_mapping_identifier(
            os.path.join("data", "cplus", "test.tiff")
        )
        self.assertEqual(mapping_id, "data--cplus--test.tiff")

    def test_generate_client_id(self):
        client_id = generate_client_id(self.pathway.path, "ncs_pathway", self.base_dir)
        self.assertEqual(client_id, "--tenbytenraster.tif_4326_10_10_1542")

    def tearDown(self):
        pass
