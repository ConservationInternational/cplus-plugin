import concurrent.futures
import datetime
import json
import os
import traceback
import typing
from zipfile import ZipFile

import requests
from qgis.core import Qgis
from .multipart_upload import upload_part
from .request import (
    CplusApiRequest,
    JOB_COMPLETED_STATUS,
    JOB_STOPPED_STATUS,
    CHUNK_SIZE,
)
from .scenario_task_api_client import ScenarioAnalysisTaskApiClient
from ..conf import settings_manager, Settings
from ..models.base import Activity, NcsPathway
from ..models.base import ScenarioResult
from ..tasks import ScenarioAnalysisTask
from ..utils import FileUtils, CustomJsonEncoder, todict


class ScenarioTaskViewStatus(ScenarioAnalysisTaskApiClient):
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
        scenario_uuid = scenario.uuid
        super().__init__(
            analysis_scenario_name,
            analysis_scenario_description,
            analysis_activities,
            analysis_priority_layers_groups,
            analysis_extent,
            scenario,
        )
        self.status_pooling = None
        self.logs = []
        self.total_file_output = 0
        self.downloaded_output = 0
        self.scenario_status = None
        self.status_pooling = None
        self.scenario_directory = scenario_directory
        self.scenario_api_uuid = scenario.uuid
        self.new_scenario_detail = {}

    def run(self) -> bool:
        """Run scenario analysis using API."""
        self.request = CplusApiRequest()
        # fetch status by interval
        self.status_pooling = self.request.fetch_scenario_status(self.scenario_api_uuid)
        self.status_pooling.on_response_fetched = self._update_scenario_status
        status_response = self.status_pooling.results()

        if self.processing_cancelled:
            return

        # if success, fetch output list
        self.scenario_status = status_response.get("status", "")
        self.new_scenario_detail = self.request.fetch_scenario_detail(
            self.scenario_api_uuid
        )

        if self.scenario_status == JOB_COMPLETED_STATUS:
            self._retrieve_scenario_outputs(self.scenario_api_uuid)
            settings_manager.delete_online_task()
        elif self.scenario_status == JOB_STOPPED_STATUS:
            scenario_error = status_response.get("errors", "Unknown error")
            raise Exception(scenario_error)

        return not self.processing_cancelled
