# coding=utf-8
"""
 Plugin tasks related to the scenario history

"""
import datetime
import json
import os
import shutil
from typing import List

from qgis.PyQt import QtCore

from .base import BaseScenarioTask, BaseFetchScenarioOutput
from .request import CplusApiRequest
from .scenario_task_api_client import ScenarioAnalysisTaskApiClient
from ..conf import settings_manager, Settings
from ..models.base import Scenario
from ..models.base import SpatialExtent
from ..utils import log


class FetchScenarioHistoryTask(BaseScenarioTask):
    """Task to fetch scenario history from API."""

    def __init__(self):
        """Task initialization."""
        super().__init__()
        self.result = []

    def run(self):
        """Execute the task logic.

        :return: True if task runs successfully
        :rtype: bool
        """
        try:
            self.result = self.fetch_scenario_history()
            return True
        except Exception as ex:
            log(f"Error during fetch scenario history: {ex}", info=False)
            return False

    def finished(self, is_success):
        """Handler when task has been executed.

        :param is_success: True if task runs successfully.
        :type is_success: bool
        """
        if is_success:
            self.store_scenario_list(self.result)
        self.task_finished.emit(is_success)

    def store_scenario_list(self, result: List[Scenario]):
        """Store scenario history into settings_manager.

        :param result: Scenario history list from API
        :type result: List[Scenario]
        """
        scenarios: List[Scenario] = settings_manager.get_scenarios()
        existing_scenarios = [s for s in scenarios if s.server_uuid is not None]
        for scenario in result:
            exist = [
                s for s in existing_scenarios if s.server_uuid == scenario.server_uuid
            ]
            if len(exist) > 0:
                continue
            settings_manager.save_scenario(scenario)
        for scenario in existing_scenarios:
            exist = [s for s in result if s.server_uuid == scenario.server_uuid]
            if len(exist) > 0:
                continue
            # check if the scenario has been downloaded
            scenario_result = settings_manager.get_scenario_result(scenario.uuid)
            if scenario_result is None:
                settings_manager.delete_scenario(scenario.uuid)

    def fetch_scenario_history(self):
        """Fetch scenario history list from API.

        :return: latest 10 scenario history.
        :rtype: List[Scenario]
        """
        return self.request.fetch_scenario_history()


class DeleteScenarioTask(BaseScenarioTask):
    """Task to delete Scenario from API."""

    def __init__(self, scenario_server_uuid):
        """Initialize the task.

        :param scenario_server_uuid: scenario server uuid
        :type scenario_server_uuid: str
        """
        super().__init__()
        self.scenario_server_uuid = scenario_server_uuid

    def run(self):
        """Execute the task logic.

        :return: True if task runs successfully
        :rtype: bool
        """
        try:
            self.request.delete_scenario(self.scenario_server_uuid)
            return True
        except Exception as ex:
            log(f"Error during delete scenario: {ex}", info=False)
            return False

    def finished(self, is_success):
        """Handler when task has been executed.

        :param is_success: True if task runs successfully.
        :type is_success: bool
        """
        self.task_finished.emit(is_success)


class FetchScenarioOutputTask(ScenarioAnalysisTaskApiClient):
    """Fetch scenario output from API."""

    task_finished = QtCore.pyqtSignal()

    def __init__(
        self,
        analysis_scenario_name,
        analysis_scenario_description,
        analysis_activities,
        analysis_priority_layers_groups,
        analysis_extent,
        scenario,
        scenario_directory,
    ):
        super(FetchScenarioOutputTask, self).__init__(
            analysis_scenario_name,
            analysis_scenario_description,
            analysis_activities,
            analysis_priority_layers_groups,
            analysis_extent,
            scenario,
            SpatialExtent(scenario.extent.bbox),
        )
        self.request = CplusApiRequest()
        self.status_pooling = None
        self.logs = []
        self.total_file_output = 0
        self.downloaded_output = 0
        self.scenario_status = None
        self.scenario_directory = scenario_directory
        self.scenario_api_uuid = scenario.uuid
        self.scenario = scenario

        self.scenario_directory = None
        self.processing_cancelled = False
        self.scenario_result = None
        self.output_list = None
        self.created_datetime

    def run(self):
        """Execute the task logic.

        :return: True if task runs successfully
        :rtype: bool
        """
        try:
            self.status_pooling = self.request.fetch_scenario_status(
                self.scenario_api_uuid
            )
            self.status_pooling.on_response_fetched = self._update_scenario_status
            status_response = self.status_pooling.results()
            self._update_scenario_status(status_response)
            self.new_scenario_detail = self.fetch_scenario_detail()
            self.created_datetime = datetime.datetime.strptime(
                self.new_scenario_detail["submitted_on"], "%Y-%m-%dT%H:%M:%SZ"
            )
            self.scenario_directory = self.get_scenario_directory()
            if os.path.exists(self.scenario_directory):
                for file in os.listdir(self.scenario_directory):
                    if file != "processing.log":
                        path = os.path.join(self.scenario_directory, file)
                        if os.path.isdir(path):
                            shutil.rmtree(os.path.join(self.scenario_directory, file))
                        else:
                            os.remove(path)

            self._retrieve_scenario_outputs(self.scenario_api_uuid)
            return True
        except Exception as ex:
            log(f"Error during fetch scenario output list: {ex}", info=False)
            return False

    def finished(self, is_success):
        """Handler when task has been executed.

        :param is_success: True if task runs successfully.
        :type is_success: bool
        """
        if is_success:
            settings_manager.save_scenario(self.scenario)
            if self.scenario_result:
                settings_manager.save_scenario_result(
                    self.scenario_result, str(self.scenario.uuid)
                )
        elif not self.processing_cancelled:
            log("Failed download scenario outputs!", info=False)
        self.task_finished.emit()

    def fetch_scenario_detail(self):
        """Fetch scenario detail from API.

        :return: scenario detail dictionary
        :rtype: dict
        """
        return self.request.fetch_scenario_detail(self.scenario.server_uuid)
