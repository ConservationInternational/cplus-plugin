import concurrent.futures
import json
import os
import traceback
import typing
from zipfile import ZipFile

from qgis.core import Qgis
from .request import (
    CplusApiRequest,
    JOB_COMPLETED_STATUS,
    JOB_STOPPED_STATUS,
    CHUNK_SIZE,
)
from ..conf import settings_manager, Settings
from cplus_core.models.base import Activity, NcsPathway, Scenario
from cplus_core.models.base import ScenarioResult
from cplus_core.analysis import ScenarioAnalysisTask, TaskConfig
from ..utils import FileUtils, CustomJsonEncoder, todict


def clean_filename(filename):
    """Creates a safe filename by removing operating system
    invalid filename characters.

    :param filename: File name
    :type filename: str

    :returns A clean file name
    :rtype str
    """
    characters = " %:/,\[]<>*?"

    for character in characters:
        if character in filename:
            filename = filename.replace(character, "_")

    return filename


class ScenarioAnalysisTaskApiClient(ScenarioAnalysisTask):
    """Prepares and runs the scenario analysis in Cplus API

    :param analysis_scenario_name: Scenario name
    :type analysis_scenario_name: str

    :param analysis_scenario_description: Scenario description
    :type analysis_scenario_description: str

    :param analysis_activities: List of activity to be processed
    :type analysis_activities: typing.List[Activity]

    :param analysis_priority_layers_groups: List of priority layer groups
    :type analysis_priority_layers_groups: typing.List[dict]

    :param analysis_extent: Extents of the Scenario
    :type analysis_extent: typing.List[float]

    :param scenario: Scenario object
    :type scenario: Scenario
    """

    def __init__(self, task_config: TaskConfig):
        super().__init__(task_config)
        self.total_file_upload_size = 0
        self.total_file_upload_chunks = 0
        self.uploaded_chunks = 0
        self.path_to_layer_mapping = {}
        self.scenario_api_uuid = None
        self.status_pooling = None
        self.logs = []
        self.total_file_output = 0
        self.downloaded_output = 0
        self.scenario_status = None
        self.__post_init__()

    def __post_init__(self):
        self.analysis_activities = [
            settings_manager.get_activity(str(activity.uuid))
            for activity in self.analysis_activities
        ]
        self.scenario.activities = self.analysis_activities

    def cancel_task(self, exception: Exception = None):
        """
        Cancel QGIS task and cancel scenario processing on API.

        :param exception: Exception to be added to cancel log
        :type exception: Exception
        """
        if self.status_pooling:
            self.status_pooling.cancelled = True
        super().cancel_task(exception)

    def on_terminated(self):
        """Function to call when the task is terminated."""
        # check if there is ongoing upload
        layer_mapping = settings_manager.get_all_layer_mapping()
        for identifier, layer in layer_mapping.items():
            upload_id = layer.get("upload_id", None)
            if not upload_id:
                continue
            self.log_message(f"Cancelling upload file: {layer['path']} ")
            try:
                self.request.abort_upload_layer(layer["uuid"], upload_id)
                settings_manager.remove_layer_mapping(identifier)
            except Exception as ex:
                self.log_message(f"Problem aborting upload layer: {ex}")
        self.log_message(f"Cancel scenario {self.scenario_api_uuid}")
        if self.scenario_api_uuid and self.scenario_status not in [
            JOB_COMPLETED_STATUS,
            JOB_STOPPED_STATUS,
        ]:
            self.request.cancel_scenario(self.scenario_api_uuid)
        super().on_terminated()

    def run(self) -> bool:
        """Run scenario analysis using API.

        :return: True if successful, False otherwise
        :rtype: bool
        """
        self.request = CplusApiRequest()
        self.scenario_directory = self.task_config.base_dir
        FileUtils.create_new_dir(self.scenario_directory)

        try:
            self.upload_layers()
        except Exception as e:
            self.log_message(str(e))
            err = f"Problem uploading layer to the server: {e}\n"
            self.log_message(err, info=False)
            self.set_info_message(err, level=Qgis.Critical)
            self.cancel_task(e)
            return False
        if self.processing_cancelled:
            return False

        try:
            self.build_scenario_detail_json()
        except Exception as ex:
            self.log_message(traceback.format_exc(), info=False)
            err = f"Problem building scenario JSON: {ex}\n"
            self.log_message(err, info=False)
            self.set_info_message(err, level=Qgis.Critical)
            self.cancel_task(ex)
            return False

        try:
            self.__execute_scenario_analysis()
        except Exception as ex:
            self.log_message(traceback.format_exc(), info=False)
            err = f"Problem executing scenario analysis in the server side: {ex}\n"
            self.log_message(err, info=False)
            self.set_info_message(err, level=Qgis.Critical)
            self.cancel_task(ex)
            return False
        return not self.processing_cancelled

    def run_upload(self, file_path, component_type) -> typing.Dict:
        """Upload a file as component type to the S3.

        :param file_path: Path of the file to be uploaded
        :type file_path: str

        :param component_type: Input layer type of the upload file (ncs_pathway, ncs_carbon, etc.)
        :type component_type: str

        :return: result, containing UUID of the uploaded file, size, and final filename
        :rtype: typing.Dict
        """

        self.log_message(f"Uploading {file_path} as {component_type}")
        upload_params = self.request.start_upload_layer(file_path, component_type)
        upload_id = upload_params["multipart_upload_id"]
        layer_uuid = upload_params["uuid"]
        upload_urls = upload_params["upload_urls"]
        if self.processing_cancelled:
            return False
        # store temporary layer
        temp_layer = {
            "uuid": layer_uuid,
            "size": os.stat(file_path).st_size,
            "name": os.path.basename(file_path),
            "upload_id": upload_id,
            "path": file_path,
        }
        settings_manager.save_layer_mapping(temp_layer)

        # do upload by chunks
        items = []
        idx = 0
        with open(file_path, "rb") as f:
            while True:
                if self.processing_cancelled:
                    break
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                url_item = upload_urls[idx]
                part_item = self.request.upload_file_part(
                    url_item["url"], chunk, url_item["part_number"]
                )
                if part_item:
                    items.append(part_item)
                else:
                    raise Exception(
                        f"Error while uploading {file_path} as " f"{component_type}"
                    )
                self.uploaded_chunks += 1
                self.__update_scenario_status(
                    {
                        "progress_text": "Uploading layers with concurrent request",
                        "progress": int(
                            (self.uploaded_chunks / self.total_file_upload_chunks) * 100
                        ),
                    }
                )
                idx += 1

        # finish upload
        result = {"uuid": None}
        if self.processing_cancelled:
            return result
        result = self.request.finish_upload_layer(layer_uuid, upload_id, items)
        return result

    def run_parallel_upload(self, upload_dict) -> typing.List[typing.Dict]:
        """Upload file concurrently using ThreadPoolExecutor

        :param upload_dict: Dictionary with file path as key and component type
        (ncs_pathway, ncs_carbon, etc.) as value.
        :type upload_dict: dict

        :return: final_result, a list of dictionary containing UUID
            of the uploaded file, size, and final filename
        :rtype: typing.List[dict]
        """

        self.__update_scenario_status(
            {
                "progress_text": "Uploading layers with concurrent request",
                "progress": 0,
            }
        )
        file_paths = list(upload_dict.keys())
        component_types = list(upload_dict.values())

        final_result = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=3 if os.cpu_count() > 3 else 1
        ) as executor:
            final_result.extend(
                list(executor.map(self.run_upload, file_paths, component_types))
            )
        return list(final_result)

    def __zip_shapefiles(self, shapefile_path: str) -> str:
        """Zip shapefiles to an object with same name.
        For example, the .shp filename is `test_file.shp`, then the zip file
        name would be `test_file.zip`

        :param shapefile_path: Path of the shapefile
        :type shapefile_path: str

        :return: Zip file path if the specified `shapefile_path`
            ends with .shp, return shapefile_path otherwise
        :rtype: str
        """

        if shapefile_path.endswith(".shp"):
            output_dir = os.path.dirname(shapefile_path)
            filename_without_ext = os.path.splitext(os.path.basename(shapefile_path))[0]
            zip_name = shapefile_path.replace(".shp", ".zip")
            with ZipFile(zip_name, "w") as zip:
                # writing each file one by one
                for file in [
                    f
                    for f in os.listdir(output_dir)
                    if filename_without_ext in f and not f.endswith("zip")
                ]:
                    zip.write(os.path.join(output_dir, file), file)
            return zip_name
        return shapefile_path

    def upload_layers(self) -> typing.Union[bool, None]:
        """Check whether layer has been uploaded. If not, then upload it to S3.
        The mapping between local file path and remote layer will then be
        added to QGIS settings.

        :return: None if upload was successful, False otherwise
        :rtype: typing.Union[bool, None]
        """

        files_to_upload = {}

        self.__update_scenario_status(
            {"progress_text": "Checking layers to be uploaded", "progress": 0}
        )
        masking_layers = self.get_masking_layers()

        # 2 comes from sieve_mask_layer and snap layer
        check_counts = len(self.analysis_activities) + 2 + len(masking_layers)
        items_to_check = {}

        activity_pwl_uuids = set()
        for idx, activity in enumerate(self.analysis_activities):
            for pathway in activity.pathways:
                if pathway:
                    if pathway.path and os.path.exists(pathway.path):
                        items_to_check[pathway.path] = "ncs_pathway"

                    for carbon_path in pathway.carbon_paths:
                        if os.path.exists(carbon_path):
                            items_to_check[carbon_path] = "ncs_carbon"

            for priority_layer in activity.priority_layers:
                if priority_layer:
                    activity_pwl_uuids.add(priority_layer.get("uuid", ""))

            self.__update_scenario_status(
                {
                    "progress_text": "Checking Activity layers to be uploaded",
                    "progress": (idx + 1 / check_counts) * 100,
                }
            )

        sieve_enabled = self.get_settings_value(
            Settings.SIEVE_ENABLED, default=False, setting_type=bool
        )

        priority_layers = self.get_priority_layers()
        for priority_layer in priority_layers:
            if priority_layer.get("uuid", "") in activity_pwl_uuids and os.path.exists(
                priority_layer.get("path", "")
            ):
                for group in priority_layer.get("groups", []):
                    if int(group.get("value", 0)) > 0:
                        items_to_check[
                            priority_layer.get("path", "")
                        ] = "priority_layer"
                        break

        if sieve_enabled:
            sieve_mask_layer = self.get_settings_value(
                Settings.SIEVE_MASK_PATH, default=""
            )

            if sieve_mask_layer:
                zip_path = self.__zip_shapefiles(sieve_mask_layer)
                items_to_check[zip_path] = "sieve_mask_layer"
            self.__update_scenario_status(
                {
                    "progress_text": "Checking layers to be uploaded",
                    "progress": (3 / check_counts) * 100,
                }
            )

        snapping_enabled = self.get_settings_value(
            Settings.SNAPPING_ENABLED, default=False, setting_type=bool
        )
        if snapping_enabled:
            reference_layer = self.get_settings_value(Settings.SNAP_LAYER, default="")
            if reference_layer:
                zip_path = self.__zip_shapefiles(reference_layer)
                items_to_check[zip_path] = "snap_layer"
        self.__update_scenario_status(
            {
                "progress_text": "Checking layers to be uploaded",
                "progress": (4 / check_counts) * 100,
            }
        )

        for idx, masking_layer in enumerate(masking_layers):
            zip_path = self.__zip_shapefiles(masking_layer)
            items_to_check[zip_path] = "mask_layer"

            self.__update_scenario_status(
                {
                    "progress_text": "Checking layers to be uploaded",
                    "progress": (idx + 5 / check_counts) * 100,
                }
            )

        files_to_upload.update(self.check_layer_uploaded(items_to_check))

        if self.processing_cancelled:
            return False

        self.total_file_upload_size = sum(os.stat(fp).st_size for fp in files_to_upload)
        self.total_file_upload_chunks = self.total_file_upload_size / CHUNK_SIZE
        final_results = self.run_parallel_upload(files_to_upload)

        if self.processing_cancelled:
            return False

        new_uploaded_layer = {}

        if len(files_to_upload) == 0:
            self.__update_scenario_status(
                {"progress_text": "All layers have been uploaded", "progress": 100}
            )
        else:
            for file_path in files_to_upload:
                filename_without_ext = ".".join(
                    os.path.basename(file_path).split(".")[0:-1]
                )
                for res in final_results:
                    if res["uuid"] is None:
                        continue
                    if res["name"].startswith(filename_without_ext):
                        res["path"] = file_path
                        new_uploaded_layer[file_path] = res
                        break
            self.__update_scenario_status(
                {"progress_text": "All layers have been uploaded", "progress": 100}
            )

        for uploaded_layer in new_uploaded_layer.values():
            identifier = uploaded_layer["path"].replace(os.sep, "--")
            self.path_to_layer_mapping[uploaded_layer["path"]] = uploaded_layer
            settings_manager.save_layer_mapping(uploaded_layer, identifier)

    def check_layer_uploaded(self, items_to_check: typing.List[dict]) -> dict:
        """Check whether a layer has been uploaded to CPLUS API

        :param items_to_check: Dictionary with file path as key and group as value
        :type items_to_check: typing.List[dict]

        :return: Dictionary with file path as key and layer availability as value
        :rtype: dict
        """
        output = {}
        uuid_to_path = {}

        for layer_path, group in items_to_check.items():
            identifier = layer_path.replace(os.sep, "--")
            uploaded_layer_dict = settings_manager.get_layer_mapping(identifier)
            if uploaded_layer_dict:
                existing_upload_id = uploaded_layer_dict.get("upload_id", None)
                existing_uuid = uploaded_layer_dict.get("uuid", None)
                if existing_upload_id and existing_uuid:
                    # if upload_id exists, then upload is not finished
                    try:
                        self.request.abort_upload_layer(
                            existing_uuid, existing_upload_id
                        )
                    except Exception as ex:
                        pass
                    output[layer_path] = items_to_check[layer_path]
                if layer_path == uploaded_layer_dict["path"]:
                    uuid_to_path[uploaded_layer_dict["uuid"]] = layer_path
                    self.path_to_layer_mapping[layer_path] = uploaded_layer_dict
            else:
                output[layer_path] = items_to_check[layer_path]
        layer_check_result = self.request.check_layer(list(uuid_to_path))
        for layer_uuid in (
            layer_check_result["unavailable"] + layer_check_result["invalid"]
        ):
            layer_path = uuid_to_path[layer_uuid]
            output[layer_path] = items_to_check[layer_path]
        return output

    def build_scenario_detail_json(self) -> None:
        """Build scenario detail JSON to be sent to CPLUS API"""

        old_scenario_dict = json.loads(
            json.dumps(todict(self.scenario), cls=CustomJsonEncoder)
        )
        sieve_enabled = self.get_settings_value(
            Settings.SIEVE_ENABLED, default=False, setting_type=bool
        )
        sieve_threshold = float(
            self.get_settings_value(Settings.SIEVE_THRESHOLD, default=10.0)
        )
        sieve_mask_path = (
            self.get_settings_value(Settings.SIEVE_MASK_PATH, default="")
            if sieve_enabled
            else ""
        )
        snapping_enabled = self.get_settings_value(
            Settings.SNAPPING_ENABLED, default=False, setting_type=bool
        )
        snap_layer_path = (
            self.get_settings_value(Settings.SNAP_LAYER, default="", setting_type=str)
            if snapping_enabled
            else ""
        )
        suitability_index = float(
            self.get_settings_value(Settings.PATHWAY_SUITABILITY_INDEX, default=0)
        )
        carbon_coefficient = float(
            self.get_settings_value(Settings.CARBON_COEFFICIENT, default=0.0)
        )
        snap_rescale = self.get_settings_value(
            Settings.RESCALE_VALUES, default=False, setting_type=bool
        )
        resampling_method = self.get_settings_value(
            Settings.RESAMPLING_METHOD, default=0
        )
        ncs_with_carbon = self.get_settings_value(
            Settings.NCS_WITH_CARBON, default=False, setting_type=bool
        )
        landuse_project = self.get_settings_value(
            Settings.LANDUSE_PROJECT, default=True, setting_type=bool
        )
        landuse_normalized = self.get_settings_value(
            Settings.LANDUSE_NORMALIZED, default=True, setting_type=bool
        )
        landuse_weighted = self.get_settings_value(
            Settings.LANDUSE_WEIGHTED, default=True, setting_type=bool
        )
        highest_position = self.get_settings_value(
            Settings.HIGHEST_POSITION, default=True, setting_type=bool
        )

        masking_layers = self.get_masking_layers()
        masking_layers = [ml.replace(".shp", ".zip") for ml in masking_layers]
        mask_layer_uuids = [
            obj["uuid"]
            for fp, obj in self.path_to_layer_mapping.items()
            if fp in masking_layers
        ]

        sieve_mask_uuid = (
            self.path_to_layer_mapping.get(sieve_mask_path, "")["uuid"]
            if sieve_mask_path
            else ""
        )
        snap_layer_uuid = (
            self.path_to_layer_mapping.get(snap_layer_path, "")["uuid"]
            if snap_layer_path
            else ""
        )

        priority_layers = self.get_priority_layers()
        for priority_layer in priority_layers:
            if priority_layer.get("path", "") in self.path_to_layer_mapping:
                priority_layer["layer_uuid"] = self.path_to_layer_mapping[
                    priority_layer.get("path", "")
                ]["uuid"]
            else:
                priority_layer["layer_uuid"] = ""
            priority_layer["path"] = ""

        for activity in old_scenario_dict["activities"]:
            activity["layer_type"] = 0
            activity["path"] = ""
            for pathway in activity["pathways"]:
                if pathway:
                    if pathway["path"] and os.path.exists(pathway["path"]):
                        if self.path_to_layer_mapping.get(pathway["path"], None):
                            pathway["uuid"] = self.path_to_layer_mapping.get(
                                pathway["path"]
                            )["uuid"]
                            pathway["layer_uuid"] = pathway["uuid"]
                            pathway["layer_type"] = 0

                    carbon_uuids = []
                    for carbon_path in pathway["carbon_paths"]:
                        if os.path.exists(carbon_path):
                            if self.path_to_layer_mapping.get(carbon_path, None):
                                carbon_uuids.append(
                                    self.path_to_layer_mapping.get(carbon_path)["uuid"]
                                )
                    pathway["carbon_paths"] = []
                    pathway["carbon_uuids"] = carbon_uuids
                    pathway["path"] = ""
            new_priority_layers = []
            for priority_layer in activity["priority_layers"]:
                if priority_layer:
                    priority_layer["path"] = ""
                    new_priority_layers.append(priority_layer)
            activity["priority_layers"] = new_priority_layers

        self.scenario_detail = {
            "scenario_name": old_scenario_dict["name"],
            "scenario_desc": old_scenario_dict["description"],
            "snapping_enabled": snapping_enabled if sieve_enabled else False,
            "snap_layer": snap_layer_path,
            "snap_layer_uuid": snap_layer_uuid,
            "pathway_suitability_index": suitability_index,
            "carbon_coefficient": carbon_coefficient,
            "snap_rescale": snap_rescale,
            "snap_method": resampling_method,
            "sieve_enabled": sieve_enabled,
            "sieve_threshold": sieve_threshold,
            "sieve_mask_path": sieve_mask_path,
            "sieve_mask_uuid": sieve_mask_uuid,
            "ncs_with_carbon": ncs_with_carbon,
            "landuse_project": landuse_project,
            "landuse_normalized": landuse_normalized,
            "landuse_weighted": landuse_weighted,
            "highest_position": highest_position,
            "mask_path": ", ".join(masking_layers),
            "mask_layer_uuids": mask_layer_uuids,
            "extent": old_scenario_dict["extent"]["bbox"],
            "priority_layer_groups": old_scenario_dict.get("priority_layer_groups", []),
            "priority_layers": json.loads(
                json.dumps(priority_layers, cls=CustomJsonEncoder)
            ),
            "activities": json.loads(
                json.dumps(old_scenario_dict["activities"], cls=CustomJsonEncoder)
            ),
        }

    def __execute_scenario_analysis(self) -> None:
        """Execute scenario analysis"""
        # submit scenario detail to the API
        self.__update_scenario_status(
            {"progress_text": "Submit and execute Scenario to CPLUS API", "progress": 0}
        )
        scenario_uuid = self.request.submit_scenario_detail(self.scenario_detail)
        self.scenario_api_uuid = scenario_uuid

        # execute scenario detail
        self.request.execute_scenario(scenario_uuid)

        if self.processing_cancelled:
            return

        # fetch status by interval
        self.status_pooling = self.request.fetch_scenario_status(scenario_uuid)
        self.status_pooling.on_response_fetched = self.__update_scenario_status
        status_response = self.status_pooling.results()

        if self.processing_cancelled:
            return

        # if success, fetch output list
        self.scenario_status = status_response.get("status", "")
        self.new_scenario_detail = self.request.fetch_scenario_detail(scenario_uuid)

        if self.scenario_status == JOB_COMPLETED_STATUS:
            self.__retrieve_scenario_outputs(scenario_uuid)
        elif self.scenario_status == JOB_STOPPED_STATUS:
            scenario_error = status_response.get("errors", "Unknown error")
            raise Exception(scenario_error)

    def __update_scenario_status(self, response: dict) -> None:
        """Update processing status in QGIS modal.

        :param response: Response dictionary from Cplus API
        :type response: dict
        """
        self.set_status_message(response.get("progress_text", ""))
        self.update_progress(response.get("progress", 0))
        if "logs" in response:
            new_logs = response.get("logs")
            for log in new_logs:
                if log not in self.logs:
                    log = json.dumps(log)
                    self.log_message(log)
            self.logs = new_logs

    def __create_activity(self, activity: dict, download_dict: dict) -> Activity:
        """Create activity object from activity dictionary and downloaded
        file dictionary

        :param activity: Activity dictionary
        :type activity: dict
        :download_dict: Downloaded file dictionary
        :type download_dict: dict

        :return: Activity object
        :rtype: Activity
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
        return activity_obj

    def __set_scenario(
        self, output_list: typing.List[dict], download_paths: list
    ) -> None:
        """Set scenario object based on output list and downloaded file paths
        to be used in generating report

        :param output_list: List of Scenario output from Cplus API
        :type output_list: typing.List[dict]
        :download_paths: List of downloaded file paths
        :type download_paths: list
        """
        output_fnames = []
        for output in output_list["results"]:
            if "_cleaned" in output["filename"]:
                output_fnames.append(output["filename"])

        weighted_activities = []
        activities = []

        download_dict = {os.path.basename(d): d for d in download_paths}

        for activity in self.new_scenario_detail["updated_detail"]["activities"]:
            activities.append(self.__create_activity(activity, download_dict))
        for activity in self.new_scenario_detail["updated_detail"][
            "weighted_activities"
        ]:
            weighted_activities.append(self.__create_activity(activity, download_dict))

        self.analysis_weighted_activities = weighted_activities
        self.analysis_activities = activities
        self.scenario.activities = activities
        self.scenario.weighted_activities = weighted_activities
        self.scenario.priority_layer_groups = self.new_scenario_detail[
            "updated_detail"
        ]["priority_layer_groups"]

    def _on_download_file_progress(self, downloaded: int, total: int):
        """Callback to update download file progreses

        :param downloaded: total bytes of downloaded file
        :type downloaded: int
        :param total: size of downloaded file
        :type total: int
        """
        part = (downloaded * 100 / total) if total > 0 else 0
        downloaded_output = self.downloaded_output + part
        self.__update_scenario_status(
            {
                "progress_text": "Downloading output files",
                "progress": int((downloaded_output / self.total_file_output) * 90) + 5,
            }
        )

    def _download_progress(self, value):
        """Tracks the download progress of value and updates
        the info message when the download has finished

        :param value: Download progress value
        :type value: int
        """
        self.__update_scenario_status(
            {
                "progress_text": "Downloading output files",
                "progress": value,
            }
        )

    def download_file(self, url: str, local_filename: str) -> None:
        """Download an output file from S3 to the local destination

        :param url: URL of the file to download
        :type url: str
        :param local_filename: str
        :type local_filename: str
        """
        parent_dir = os.path.dirname(local_filename)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        self.request.download_file(url, local_filename, self._download_progress)
        self.downloaded_output += 1
        self.__update_scenario_status(
            {
                "progress_text": "Downloading output files",
                "progress": int((self.downloaded_output / self.total_file_output) * 90)
                + 5,
            }
        )

    def __retrieve_scenario_outputs(self, scenario_uuid: str):
        """Set scenario output object based on scenario UUID
        to be used in generating report

        :param scenario_uuid: Scenario UUID
        :type scenario_uuid: str
        """
        self.__update_scenario_status(
            {"progress_text": "Downloading output files", "progress": 0}
        )
        output_list = self.request.fetch_scenario_output_list(scenario_uuid)
        self.__update_scenario_status(
            {"progress_text": "Downloading output files", "progress": 5}
        )
        self.total_file_output = len(output_list["results"])
        self.downloaded_output = 0
        urls_to_download = []
        download_paths = []
        for output in output_list["results"]:
            urls_to_download.append(output["url"])
            if output["is_final_output"]:
                download_path = os.path.join(
                    self.scenario_directory, output["filename"]
                )
                final_output_path = download_path
                self.output = output["output_meta"]
                self.output["OUTPUT"] = final_output_path
            else:
                download_path = os.path.join(
                    self.scenario_directory, output["group"], output["filename"]
                )
            download_paths.append(download_path)

        for idx, url in enumerate(urls_to_download):
            self.download_file(url, download_paths[idx])
            if self.processing_cancelled:
                return

        self.__set_scenario(output_list, download_paths)

        self.scenario_result = ScenarioResult(
            scenario=self.scenario,
            scenario_directory=self.scenario_directory,
            analysis_output=self.output,
        )

        self.__update_scenario_status(
            {"progress_text": "Finished downloading output files", "progress": 100}
        )
