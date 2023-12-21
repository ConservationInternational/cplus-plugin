# coding=utf-8
"""Tests for the plugin processing tasks

"""

import unittest

import os
import uuid
import logging
import datetime

from qgis.core import QgsRasterLayer

from cplus_plugin.conf import settings_manager, Settings

from cplus_plugin.tasks import ScenarioAnalysisTask
from cplus_plugin.models.base import Scenario, NcsPathway, ImplementationModel


class ScenarioAnalysisTaskTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_scenario_pathways_analysis(self):
        pathway_layer_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "pathways", "layers"
        )

        carbon_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "carbon", "layers"
        )

        carbon_layer_path = os.path.join(carbon_directory, "carbon_layer_1.tif")

        pathway_layer_path = os.path.join(pathway_layer_directory, "test_pathway_1.tif")

        test_pathway = NcsPathway(
            uuid=uuid.uuid4(),
            name="test_pathway",
            description="test_description",
            path=pathway_layer_path,
            carbon_paths=[carbon_layer_path],
        )

        test_layer = QgsRasterLayer(test_pathway.path, test_pathway.name)

        test_extent = test_layer.extent()

        test_model = ImplementationModel(
            uuid=uuid.uuid4(),
            name="test_model",
            description="test_description",
            pathways=[test_pathway],
        )

        scenario = Scenario(
            uuid=uuid.uuid4(),
            name="Scenario",
            description="Scenario description",
            models=[test_model],
            extent=test_extent,
            weighted_models=[],
            priority_layer_groups=[],
        )

        analysis_task = ScenarioAnalysisTask(
            "test_scenario_pathways_analysis",
            "test_scenario_pathways_analysis_description",
            [test_model],
            [],
            test_layer.extent(),
            scenario,
        )

        extent_string = (
            f"{test_extent.xMinimum()},{test_extent.xMaximum()},"
            f"{test_extent.yMinimum()},{test_extent.yMaximum()}"
            f" [{test_layer.crs().authid()}]"
        )

        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data",
            "pathways",
        )

        scenario_directory = os.path.join(
            f"{base_dir}",
            f'scenario_{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}',
        )

        analysis_task.scenario_directory = scenario_directory

        settings_manager.set_value(Settings.BASE_DIR, base_dir)

        settings_manager.set_value(Settings.PATHWAY_SUITABILITY_INDEX, 1.0)

        settings_manager.set_value(Settings.CARBON_COEFFICIENT, 1.0)

        print(f"before tests {test_pathway.path}")

        print(f" base dir {base_dir}")
        print(f" base dir {settings_manager.get_value(Settings.BASE_DIR)}")

        past_stat = test_layer.dataProvider().bandStatistics(1)

        print(f"Past min {past_stat.minimumValue}, max {past_stat.maximumValue}")

        results = analysis_task.run_pathways_analysis(
            [test_model],
            [],
            extent_string,
        )

        self.assertTrue(results)

        print(f"after tests {test_pathway.path}")
        print(f"Error {analysis_task.error}")

        result_layer = QgsRasterLayer(test_pathway.path, test_pathway.name)

        stat = result_layer.dataProvider().bandStatistics(1)

        print(f"New min {stat.minimumValue}, max {stat.maximumValue}")

        # self.assertEqual(len(analysis_task.analysis_weighted_ims), 1)
        # self.assertEqual(analysis_task.analysis_weighted_ims, scenario.weighted_models)

    def tearDown(self):
        pass
