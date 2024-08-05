# coding=utf-8
"""
 Plugin tasks related to the scenario history

"""

import os
import datetime
import concurrent.futures
from typing import List
from qgis.core import QgsTask
from qgis.PyQt import QtCore
import shutil
import requests

from ..models.base import Scenario, ScenarioResult, NcsPathway, Activity
from ..conf import settings_manager, Settings
from ..utils import log
from .request import CplusApiRequest


class BaseScenarioTask(QgsTask):
    """Base Qgs task for Scenario API Operation."""

    task_finished = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.request = CplusApiRequest()


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


class FetchScenarioOutputTask(BaseScenarioTask):
    """Fetch scenario output from API."""

    def __init__(self, scenario: Scenario):
        """Task initialization.

        :param scenario: scenario object to fetch the output.
        :type scenario: Scenario
        """
        super().__init__()
        self.scenario = scenario
        self.total_file_output = 0
        self.downloaded_output = 0
        self.created_datetime = datetime.datetime.now()
        self.scenario_directory = None
        self.processing_cancelled = False
        self.scenario_result = None

    def get_scenario_directory(self):
        """Generate scenario directory from output datetime.

        :return: Path to scenario directory
        :rtype: str
        """
        base_dir = settings_manager.get_value(Settings.BASE_DIR)
        return os.path.join(
            f"{base_dir}",
            "scenario_" f'{self.created_datetime.strftime("%Y_%m_%d_%H_%M_%S")}',
        )

    def run(self):
        """Execute the task logic.

        :return: True if task runs successfully
        :rtype: bool
        """
        try:
            scenario_data = self.fetch_scenario_detail()
            self.created_datetime = datetime.datetime.strptime(
                scenario_data["submitted_on"], "%Y-%m-%dT%H:%M:%SZ"
            )
            self.scenario_directory = self.get_scenario_directory()
            if os.path.exists(self.scenario_directory):
                shutil.rmtree(self.scenario_directory)
            self.fetch_scenario_output(scenario_data["updated_detail"])
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
        self.task_finished.emit(self.scenario_result)

    def fetch_scenario_detail(self):
        """Fetch scenario detail from API.

        :return: scenario detail dictionary
        :rtype: dict
        """
        return self.request.fetch_scenario_detail(self.scenario.server_uuid)

    def fetch_scenario_output(self, scenario_detail):
        """Fetch scenario outputs from API.

        :param scenario_detail: scenario detail dictionary
        :type scenario_detail: dict
        """
        output_list = self.request.fetch_scenario_output_list(self.scenario.server_uuid)
        self.total_file_output = len(output_list["results"])
        self.downloaded_output = 0
        urls_to_download = []
        download_paths = []
        final_output = None
        for output in output_list["results"]:
            urls_to_download.append(output["url"])
            if output["is_final_output"]:
                download_path = os.path.join(
                    self.scenario_directory, output["filename"]
                )
                final_output_path = download_path
                final_output = output["output_meta"]
                final_output["OUTPUT"] = final_output_path
            else:
                download_path = os.path.join(
                    self.scenario_directory, output["group"], output["filename"]
                )
            download_paths.append(download_path)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=3 if os.cpu_count() > 3 else 1
        ) as executor:
            executor.map(self.download_file, urls_to_download, download_paths)
        if self.processing_cancelled:
            return

        self.__set_scenario(scenario_detail, output_list, download_paths)

        self.scenario_result = ScenarioResult(
            scenario=self.scenario,
            created_date=self.created_datetime,
            scenario_directory=self.scenario_directory,
            analysis_output=final_output,
        )

    def download_file(self, url, local_filename):
        """Download file output.

        :param url: URL to the file output
        :type url: str
        :param local_filename: output filepath
        :type local_filename: str
        """
        parent_dir = os.path.dirname(local_filename)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            if self.processing_cancelled:
                return
            with open(local_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                    if self.processing_cancelled:
                        return
        self.downloaded_output += 1

    def __create_activity(self, activity: dict, download_dict: list):
        """
        Create activity object from activity dictionary and downloaded
        file dictionary
        :param activity: activity dictionary
        :download_dict: downloaded file dictionary
        """
        ncs_pathways = []
        for pathway in activity["pathways"]:
            if "layer_uuid" in pathway:
                del pathway["layer_uuid"]
            if "carbon_uuids" in pathway:
                del pathway["carbon_uuids"]
            pathway_filename = os.path.basename(pathway["path"])
            if pathway_filename in download_dict:
                pathway["path"] = download_dict[pathway_filename]
                ncs_pathways.append(NcsPathway(**pathway))
        activity["pathways"] = ncs_pathways
        activity_filename = os.path.basename(activity["path"])
        if activity_filename in download_dict:
            activity["path"] = download_dict[activity_filename]
        activity_obj = Activity(**activity)
        activity_obj.pathways = ncs_pathways
        return activity_obj

    def __set_scenario(self, scenario_detail, output_list, download_paths):
        """
        Set scenario object based on output list and downloaded file paths
        to be used in generating report
        :param output_list: List of output from CPLUS API
        :download_paths: List of downloaded file paths
        """
        output_fnames = []
        for output in output_list["results"]:
            if "_cleaned" in output["filename"]:
                output_fnames.append(output["filename"])

        weighted_activities = []
        activities = []

        download_dict = {os.path.basename(d): d for d in download_paths}

        for activity in scenario_detail["activities"]:
            activities.append(self.__create_activity(activity, download_dict))
        for activity in scenario_detail["weighted_activities"]:
            weighted_activities.append(self.__create_activity(activity, download_dict))

        self.scenario.activities = activities
        self.scenario.weighted_activities = weighted_activities
        self.scenario.priority_layer_groups = scenario_detail["priority_layer_groups"]


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
