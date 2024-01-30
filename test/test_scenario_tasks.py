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
            f'scenario_{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
            f"{str(uuid.uuid4())[:4]}",
        )

        analysis_task.scenario_directory = scenario_directory

        settings_manager.set_value(Settings.BASE_DIR, base_dir)
        settings_manager.set_value(Settings.PATHWAY_SUITABILITY_INDEX, 1.0)
        settings_manager.set_value(Settings.CARBON_COEFFICIENT, 1.0)

        past_stat = test_layer.dataProvider().bandStatistics(1)

        self.assertEqual(past_stat.minimumValue, 1.0)
        self.assertEqual(past_stat.maximumValue, 10.0)

        results = analysis_task.run_pathways_analysis(
            [test_model],
            [],
            extent_string,
            temporary_output=True,
        )

        self.assertTrue(results)

        result_layer = QgsRasterLayer(test_pathway.path, test_pathway.name)

        stat = result_layer.dataProvider().bandStatistics(1)

        self.assertEqual(stat.minimumValue, 2.0)
        self.assertEqual(stat.maximumValue, 20.0)

    def test_scenario_pathways_normalization(self):
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
            "test_scenario_pathways_normalization",
            "test_scenario_pathways_normalization_description",
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
            f'scenario_{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
            f"_{str(uuid.uuid4())[:4]}",
        )

        analysis_task.scenario_directory = scenario_directory

        settings_manager.set_value(Settings.BASE_DIR, base_dir)
        settings_manager.set_value(Settings.PATHWAY_SUITABILITY_INDEX, 1.0)
        settings_manager.set_value(Settings.CARBON_COEFFICIENT, 1.0)

        past_stat = test_layer.dataProvider().bandStatistics(1)

        self.assertEqual(past_stat.minimumValue, 1.0)
        self.assertEqual(past_stat.maximumValue, 10.0)

        results = analysis_task.run_pathways_normalization(
            [test_model],
            [],
            extent_string,
            temporary_output=True,
        )

        self.assertTrue(results)

        result_layer = QgsRasterLayer(test_pathway.path, test_pathway.name)

        stat = result_layer.dataProvider().bandStatistics(1)

        self.assertEqual(stat.minimumValue, 0.0)
        self.assertEqual(stat.maximumValue, 2.0)

    def test_scenario_models_creation(self):
        pathway_layer_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "pathways", "layers"
        )

        pathway_layer_path_1 = os.path.join(
            pathway_layer_directory, "test_pathway_1.tif"
        )

        first_test_pathway = NcsPathway(
            uuid=uuid.uuid4(),
            name="first_test_pathway",
            description="first_test_description",
            path=pathway_layer_path_1,
            carbon_paths=[],
        )

        pathway_layer_path_2 = os.path.join(
            pathway_layer_directory, "test_pathway_2.tif"
        )

        second_test_pathway = NcsPathway(
            uuid=uuid.uuid4(),
            name="second_test_pathway",
            description="second_test_description",
            path=pathway_layer_path_2,
            carbon_paths=[],
        )

        first_test_layer = QgsRasterLayer(
            first_test_pathway.path, first_test_pathway.name
        )
        second_test_layer = QgsRasterLayer(
            second_test_pathway.path, second_test_pathway.name
        )

        test_extent = first_test_layer.extent()

        test_model = ImplementationModel(
            uuid=uuid.uuid4(),
            name="test_model",
            description="test_description",
            pathways=[first_test_pathway, second_test_pathway],
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
            "test_scenario_models_creation",
            "test_scenario_models_creation_description",
            [test_model],
            [],
            test_extent,
            scenario,
        )

        extent_string = (
            f"{test_extent.xMinimum()},{test_extent.xMaximum()},"
            f"{test_extent.yMinimum()},{test_extent.yMaximum()}"
            f" [{first_test_layer.crs().authid()}]"
        )

        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data",
            "pathways",
        )

        scenario_directory = os.path.join(
            f"{base_dir}",
            f'scenario_{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
            f"_{str(uuid.uuid4())[:4]}",
        )

        analysis_task.scenario_directory = scenario_directory

        settings_manager.set_value(Settings.BASE_DIR, base_dir)
        settings_manager.set_value(Settings.PATHWAY_SUITABILITY_INDEX, 1.0)
        settings_manager.set_value(Settings.CARBON_COEFFICIENT, 1.0)

        first_layer_stat = first_test_layer.dataProvider().bandStatistics(1)
        second_layer_stat = second_test_layer.dataProvider().bandStatistics(1)

        self.assertEqual(first_layer_stat.minimumValue, 1.0)
        self.assertEqual(first_layer_stat.maximumValue, 10.0)

        self.assertEqual(second_layer_stat.minimumValue, 7.0)
        self.assertEqual(second_layer_stat.maximumValue, 10.0)

        results = analysis_task.run_models_analysis(
            [test_model],
            [],
            extent_string,
            temporary_output=True,
        )

        self.assertTrue(results)

        result_layer = QgsRasterLayer(test_model.path, test_model.name)

        stat = result_layer.dataProvider().bandStatistics(1)

        self.assertEqual(stat.minimumValue, 1.0)
        self.assertEqual(stat.maximumValue, 19.0)

    def test_scenario_models_normalization(self):
        models_layer_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "models", "layers"
        )

        model_layer_path_1 = os.path.join(models_layer_directory, "test_model_1.tif")

        test_model = ImplementationModel(
            uuid=uuid.uuid4(),
            name="test_model",
            description="test_description",
            pathways=[],
            path=model_layer_path_1,
        )

        model_layer = QgsRasterLayer(test_model.path, test_model.name)

        test_extent = model_layer.extent()

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
            "test_scenario_models_creation",
            "test_scenario_models_creation_description",
            [test_model],
            [],
            test_extent,
            scenario,
        )

        extent_string = (
            f"{test_extent.xMinimum()},{test_extent.xMaximum()},"
            f"{test_extent.yMinimum()},{test_extent.yMaximum()}"
            f" [{model_layer.crs().authid()}]"
        )

        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data",
            "models",
        )

        scenario_directory = os.path.join(
            f"{base_dir}",
            f'scenario_{datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
            f"_{str(uuid.uuid4())[:4]}",
        )

        analysis_task.scenario_directory = scenario_directory

        settings_manager.set_value(Settings.BASE_DIR, base_dir)
        settings_manager.set_value(Settings.PATHWAY_SUITABILITY_INDEX, 1.0)
        settings_manager.set_value(Settings.CARBON_COEFFICIENT, 1.0)

        first_layer_stat = model_layer.dataProvider().bandStatistics(1)

        self.assertEqual(first_layer_stat.minimumValue, 1.0)
        self.assertEqual(first_layer_stat.maximumValue, 19.0)

        results = analysis_task.run_models_normalization(
            [test_model],
            [],
            extent_string,
            temporary_output=True,
        )

        self.assertTrue(results)

        result_layer = QgsRasterLayer(test_model.path, test_model.name)

        stat = result_layer.dataProvider().bandStatistics(1)

        self.assertEqual(stat.minimumValue, 0.0)
        self.assertEqual(round(stat.maximumValue, 2), 1.89)

    def tearDown(self):
        pass
