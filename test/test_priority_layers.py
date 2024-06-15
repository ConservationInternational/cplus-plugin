# coding=utf-8
"""Tests for the plugin settings manager logic
 for handling the priority weighting layers.

"""

import unittest
import uuid

from cplus_plugin.conf import settings_manager

from data.priority_weighting_layers import PRIORITY_LAYERS


class PriorityLayersTest(unittest.TestCase):
    """Test the plugins priority layers related operations"""

    def teardown_setup(self):
        self.tearDown()
        self.setUp()

    def test_priority_layers_settings(self):
        """Settings manager can store and retrieve priority layers settings"""

        for layers_list in PRIORITY_LAYERS:
            self.teardown_setup()

            for index, layer in enumerate(layers_list):
                settings_manager.save_priority_layer(layer)
                layer_settings = settings_manager.get_priority_layer(layer.get("uuid"))

                self.assertEqual(layer_settings.get("uuid"), layer.get("uuid"))
                self.assertEqual(layer_settings.get("name"), layer.get("name"))
                self.assertEqual(
                    layer_settings.get("description"), layer.get("description")
                )
                self.assertEqual(layer_settings.get("groups"), layer.get("groups", []))

            self.assertEqual(
                len(settings_manager.get_priority_layers()), len(layers_list)
            )

    def test_priority_layers_groups_with_uuid_obj(self):
        """Test bug when saving groups in priority layer becomes invalid uuid"""
        layer = {
            "uuid": "1f894ea8-32b4-4cac-9b7a-d313db51f816",
            "name": "Test layer",
            "description": "Placeholder text for herding for health",
            "selected": True,
            "path": [],
            "groups": [
                {
                    "uuid": uuid.UUID("02ce3cf4-7bab-44c2-a607-80c08f747b21"),
                    "name": "Biodiversity",
                    "value": "5",
                }
            ],
        }
        settings_manager.save_priority_layer(layer)
        layer_settings = settings_manager.get_priority_layer(layer.get("uuid"))
        self.assertEqual(layer_settings.get("uuid"), layer.get("uuid"))
        self.assertEqual(layer_settings.get("name"), layer.get("name"))
        groups = layer_settings.get("groups")
        self.assertEqual(len(groups), 1)
        self.assertTrue(isinstance(groups[0].get("uuid"), str))
        self.assertEqual(groups[0].get("uuid"), str(layer["groups"][0].get("uuid")))

    def tearDown(self) -> None:
        settings_manager.delete_priority_layers()
