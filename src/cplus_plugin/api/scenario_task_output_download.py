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


class ScenarioTaskOutputDownload(ScenarioAnalysisTaskApiClient):
    def __init__(
        self,
        analysis_scenario_name,
        analysis_scenario_description,
        analysis_activities,
        analysis_priority_layers_groups,
        analysis_extent,
        scenario,
        scenario_directory
    ):
        scenario_uuid = scenario.uuid
        super().__init__(
            analysis_scenario_name,
            analysis_scenario_description,
            analysis_activities,
            analysis_priority_layers_groups,
            analysis_extent,
            scenario
        )
        self.status_pooling = None
        self.logs = []
        self.total_file_output = 0
        self.downloaded_output = 0
        self.scenario_status = None
        self.scenario_directory = scenario_directory
        self.scenario.uuid = scenario_uuid

    def run(self) -> bool:
        """Run scenario analysis using API."""
        self.request = CplusApiRequest()
        self.log_message('RETRIEVE')
        try:
            self.new_scenario_detail = self.request.fetch_scenario_detail(self.scenario.uuid)
            self._retrieve_scenario_outputs(self.scenario.uuid)
            settings_manager.delete_online_task()
        except Exception as ex:
            self.log_message(traceback.format_exc(), info=False)
            err = f"Problem executing scenario analysis in the server side: {ex}\n"
            self.log_message(err, info=False)
            self.set_info_message(err, level=Qgis.Critical)
            self.cancel_task(ex)
            return False
        return not self.processing_cancelled

