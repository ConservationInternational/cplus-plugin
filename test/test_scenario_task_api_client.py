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


class ScenarioAnalysisTaskApiClientTest(unittest.TestCase):
    def setUp(self):
        Processing.initialize()

    def test_generate_layer_mapping_id(self):
        client_id = generate_layer_mapping_identifier(
            os.path.join("data", "cplus", "test.tiff")
        )
        self.assertEqual(client_id, "data--cplus--test.tiff")

    def tearDown(self):
        pass
