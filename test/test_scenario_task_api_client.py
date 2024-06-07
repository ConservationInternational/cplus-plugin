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


class MockCplusApiRequest:
    mocked_response = None

    def get_layer_by_client_ids(self, payload):
        if self.mocked_response:
            return self.mocked_response
        return [
            {"uuid": "37e36503-9136-4470-8537-e672db4f2662", "client_id": "random-id"}
        ]


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

    def test_sync_input_layers(self):
        settings_manager.set_value(Settings.BASE_DIR, self.base_dir)
        scenario = get_test_scenario()
        mocked_request = MockCplusApiRequest()
        client = ScenarioAnalysisTaskApiClient(
            "test",
            "test",
            scenario.activities,
            scenario.priority_layer_groups,
            scenario.extent,
            scenario,
        )
        client.request = mocked_request
        items_to_check = {self.pathway.path: "ncs_pathway"}
        mapping_id = generate_layer_mapping_identifier(self.pathway.path)
        mocked_request.mocked_response = []
        client.sync_input_layers(items_to_check)
        layer_mapping = settings_manager.get_layer_mapping(mapping_id)
        self.assertFalse(layer_mapping)
        mocked_request.mocked_response = [
            {
                "uuid": "37e36503-9136-4470-8537-e672db4f2662",
                "client_id": generate_client_id(
                    self.pathway.path, "ncs_pathway", self.base_dir
                ),
            }
        ]
        client.sync_input_layers(items_to_check)
        layer_mapping = settings_manager.get_layer_mapping(mapping_id)
        self.assertTrue(layer_mapping)
        self.assertEqual(
            layer_mapping.get("uuid"), mocked_request.mocked_response[0].get("uuid")
        )

    def tearDown(self):
        pass
