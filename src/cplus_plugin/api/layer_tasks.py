# coding=utf-8
"""
Plugin tasks related to the layer
"""

from datetime import datetime
import os
import json
import time
import traceback
import typing

from qgis.core import (
    QgsApplication,
    QgsRectangle,
    QgsTask,
    QgsProcessingFeedback,
    QgsProcessingContext,
    QgsFileDownloader,
    QgsCoordinateReferenceSystem,
    QgsVectorLayer,
)
from qgis.PyQt import QtCore

from ..conf import settings_manager, Settings
from ..definitions.constants import (
    NO_DATA_VALUE,
)
from .base import ApiRequestStatus
from ..models.base import ResultInfo
from ..models.helpers import extent_to_url_param
from ..utils import (
    log,
    tr,
    CustomJsonEncoder,
    todict,
    compress_raster,
    get_layer_type,
    convert_size,
    transform_extent,
)
from .request import (
    CplusApiPooling,
    CplusApiRequest,
    CplusApiRequestError,
    CplusApiUrl,
    JOB_COMPLETED_STATUS,
)


class FetchDefaultLayerTask(QgsTask):
    """Qgs task for fetching default layer."""

    task_finished = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.request = CplusApiRequest()
        self.result = {}

    def run(self):
        """Execute the task logic.
        :return: True if task runs successfully
        :rtype: bool
        """
        try:
            self.result = self.request.fetch_default_layer_list()
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
            settings_manager.remove_default_layers()
            self.store_default_layers(self.result)
        self.task_finished.emit(is_success)

    def store_default_layers(self, result: dict):
        """Store default layers to settings manager.

        :param result: Dictionary of type and layer list
        :type result: dict
        """
        for key, layers in result.items():
            settings_manager.save_default_layers(key, layers)


class DeleteDefaultLayerTask(QgsTask):
    """Qgs task for deleting default layer."""

    task_finished = QtCore.pyqtSignal(object)

    def __init__(self, layer: dict):
        """Initialize the task with the layer.
        :param layer: Layer dictionary containing layer details
        :type layer: dict
        """
        super().__init__()
        self.layer = layer
        self.request = CplusApiRequest()
        self.result = {self.layer.get("layer_uuid"): False}

    def run(self):
        """Execute the task logic.
        :return: True if task runs successfully
        :rtype: bool
        """
        try:
            self.result[self.layer.get("layer_uuid")] = self.request.delete_layer(
                self.layer.get("layer_uuid")
            )
            return True
        except Exception as ex:
            log(f"Error deleting default layer: {ex}", info=False)
            return False

    def finished(self, is_success):
        """Handler when task has been executed.
        :param is_success: True if task runs successfully.
        :type is_success: bool
        """
        if is_success:
            settings_manager.remove_default_layer(self.layer)

        self.task_finished.emit(is_success)


class CreateUpdateDefaultLayerTask(QgsTask):
    """Task for creating or updating default layer in the server"""

    status_message_changed = QtCore.pyqtSignal(str)
    custom_progress_changed = QtCore.pyqtSignal(float)
    task_completed = QtCore.pyqtSignal(object)

    def __init__(self, layer: dict, request, chunk_size: int):
        super().__init__()
        self.layer = layer
        self.request = request
        self.chunk_size = chunk_size

        self.layer_uuid = layer.get("layer_uuid")

        self.is_updated_mode = self.layer_uuid is not None

        self.name = layer.get("name")
        self.description = layer.get("description")
        self.version = layer.get("version")
        self.license = layer.get("license")

        self.component_type = layer.get("component_type", "priority_layer")
        self.privacy_type = layer.get("privacy_type", "common")

        self.file_path = layer.get("file_path")
        self.total_size = (
            os.path.getsize(self.file_path)
            if os.path.exists(self.file_path) is None
            else 0
        )
        self.progress = 0
        self.error = None
        self.upload_id = None
        self.upload_cancelled = False

    def upload_file(self) -> typing.Dict:
        """Upload a file as component type to the S3.

        :return: result, containing UUID of the uploaded file, size, and
            final filename
        :rtype: typing.Dict
        """
        self.uploaded_chunks = 0
        self.total_file_upload_chunks = 0
        self.logs = []
        self.upload_cancelled = False

        self.set_status_message(f"Preparing the layer for upload.....{self.file_path}")

        tmp_file = self.file_path
        # Attempt to compress the file before upload
        if get_layer_type(self.file_path) == 0:
            self.set_status_message(f"Compressing the file.....{self.file_path}")
            tmp_file = compress_raster(
                self.file_path,
                nodata_value=settings_manager.get_value(
                    Settings.NCS_NO_DATA_VALUE, NO_DATA_VALUE
                ),
            )
            if tmp_file:
                self.log_message(
                    f"""Compression completed...... from {convert_size(os.stat(self.file_path).st_size)} 
                    to {convert_size(os.stat(tmp_file).st_size)}"""
                )
            else:
                tmp_file = self.file_path
                self.log_message(f"Compressing the layer failed......")

        self.total_file_upload_size = os.stat(tmp_file).st_size
        self.total_file_upload_chunks = self.total_file_upload_size / self.chunk_size

        self.set_status_message(f"Uploading layer...{self.file_path}")
        self.log_message(f"Uploading {self.file_path}")
        upload_params = self.request.start_upload_layer(
            tmp_file,
            self.component_type,
            privacy_type=self.privacy_type,
            uuid=self.layer_uuid,
            description=self.description,
            license=self.license,
            version=self.version,
        )
        self.layer_uuid = upload_params["uuid"]
        self.upload_id = upload_params["multipart_upload_id"]
        upload_urls = upload_params["upload_urls"]
        if self.upload_cancelled:
            return False
        # store temporary layer
        temp_layer = {
            "uuid": self.layer_uuid,
            "size": os.stat(tmp_file).st_size,
            "name": os.path.basename(tmp_file),
            "upload_id": self.upload_id,
            "path": tmp_file,
        }
        settings_manager.save_layer_mapping(temp_layer)

        # do upload by chunks
        self.upload_items = []
        with open(tmp_file, "rb") as f:
            idx = 0
            while True:
                if self.upload_cancelled:
                    break
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                url_item = upload_urls[idx]
                part_item = self.request.upload_file_part(
                    url_item["url"], chunk, url_item["part_number"]
                )
                if part_item:
                    self.upload_items.append(part_item)
                else:
                    raise Exception(
                        f"""
                        Error while uploading {self.file_path}
                        """
                    )
                self.uploaded_chunks += 1
                self._update_upload_status(
                    {
                        "progress_text": "Uploading layers",
                        "progress": int(
                            (self.uploaded_chunks / self.total_file_upload_chunks) * 100
                        ),
                    }
                )
                idx += 1
                self.progress = int(
                    (self.uploaded_chunks / self.total_file_upload_chunks) * 100
                )
                self.setProgress(self.progress)

        # finish upload
        result = {"uuid": None}
        if self.upload_cancelled:
            return result
        result = self.request.finish_upload_layer(
            self.layer_uuid, self.upload_id, self.upload_items
        )

        self.layer_uuid = result.get("uuid")

        if result:
            if result.get("status", 200) == 200:
                self.log_message(
                    self.tr(
                        f"""
                        Layer uploaded successfully.
                        UUID: {self.layer_uuid}
                        """
                    ),
                )
                self.set_status_message(
                    f"Successfully uploaded layer...{self.file_path}"
                )
            else:
                self.log_message(self.tr(result.get("detail", "")))

        return result

    def _update_upload_status(self, response: dict) -> None:
        """Update upload status in QGIS modal.

        :param response: Response dictionary from Cplus API
        :type response: dict
        """
        self.set_status_message(response.get("progress_text", ""))
        self.update_progress(response.get("progress", 0))

        if "logs" in response:
            new_logs = response.get("logs")
            for log_entry in new_logs:
                if log_entry not in self.logs:
                    log_json = json.dumps(log_entry)
                    self.log_message(log_json)
            self.logs = new_logs

    def run(self):
        """Run the task."""

        # upload file if it is provided

        if os.path.exists(self.file_path):
            try:
                self.upload_file()
                self.set_status_message("Layer file uploaded")
            except Exception as e:
                self.log_message(traceback.format_exc(), info=False)
                err = f"Problem uploading layer file to the server: {e}\n"
                self.log_message(err, info=False)
                self.set_status_message(err)
                self.cancel_task(e)
                return False
        if self.upload_cancelled:
            self.set_status_message("Cleaning up after cancellation...")
            self.handle_upload_cancelled()
            return False
        else:
            try:
                self.request.update_layer_properties(
                    self.layer_uuid,
                    {
                        "name": self.name,
                        "description": self.description,
                        "version": self.version,
                        "license": self.license,
                        "component_type": self.component_type,
                        "privacy_type": self.privacy_type,
                    },
                )
                self.progress = 100
                self.setProgress(self.progress)
                self.update_progress(100)
            except Exception as e:
                self.log_message(traceback.format_exc(), info=False)
                err = f"Problem updating layer properties in the server: {e}\n"
                self.log_message(err, info=False)
                self.set_status_message(err)
                self.cancel_task(e)
                return False

            # Update default layers in the settings
            self.set_status_message("Refreshing layers list")

        default_layers = self.request.fetch_default_layer_list()
        settings_manager.save_default_layers(
            self.component_type, default_layers.get(self.component_type)
        )
        settings_manager.priority_layers_changed.emit()

        self.set_status_message("Layer saved")

        return not self.upload_cancelled

    def cancel_task(self, exception=None):
        """Notifies the task that it should terminate

        :param exception: Exception if stopped with error, defaults to None
        :type exception: Any, optional
        """
        self.error = exception
        self.cancel()

    def log_message(
        self,
        message: str,
        name: str = "qgis_cplus",
        info: bool = True,
        notify: bool = True,
    ):
        """Logs the message into QGIS logs using qgis_cplus as the default
        log instance.
        If notify_user is True, user will be notified about the log.

        :param message: The log message
        :type message: str

        :param name: Name of te log instance, qgis_cplus is the default
        :type message: str

        :param info: Whether the message is about info or a
            warning
        :type info: bool

        :param notify: Whether to notify user about the log
        :type notify: bool
        """
        if not isinstance(message, str):
            if isinstance(message, dict):
                message = json.dumps(message, cls=CustomJsonEncoder)
            else:
                message = json.dumps(todict(message), cls=CustomJsonEncoder)
        log(message, name=name, info=info, notify=notify)

    def finished(self, is_success: bool):
        if not self.upload_cancelled:
            if is_success:
                self.log_message(tr(f"Finished saving layer {self.name} \n"))
            else:
                self.log_message(f"Error while saving the layer: {self.error}")
        self.task_completed.emit(is_success)

    def set_status_message(self, message: str):
        """Set status message in progress dialog

        :param message: Message to be displayed
        :type message: str
        """
        self.status_message = message
        self.status_message_changed.emit(self.status_message)

    def set_custom_progress(self, value: float):
        """Set task progress value.

        :param value: Value to be set on the progress bar
        :type value: float
        """
        self.custom_progress = min(max(0, float(value)), 100)
        self.custom_progress_changed.emit(self.custom_progress)

    def update_progress(self, value):
        """Sets the value of the task progress

        :param value: Value to be set on the progress bar
        :type value: float
        """
        if not self.upload_cancelled:
            self.set_custom_progress(value)
        else:
            self.feedback = QgsProcessingFeedback()
            self.processing_context = QgsProcessingContext()

    def handle_upload_cancelled(self):
        """
        Handles cleanup when an upload is cancelled.

        - If a new layer was being created and upload is cancelled, deletes the layer from the server.
        - If an upload was in progress (either create or update), aborts the multipart upload on the server.

        This ensures that no incomplete or orphaned layers/files remain on the server after cancellation.
        """
        # If creating a new layer and cancelled, delete the incomplete layer
        if self.layer_uuid is not None and not self.is_updated_mode:
            try:
                self.request.delete_layer(self.layer_uuid)
                self.log_message(f"Deleted incomplete layer {self.layer_uuid}")
            except Exception as ex:
                self.log_message(
                    f"Error deleting incomplete layer {self.layer_uuid}: {ex}",
                    info=False,
                )
            return

        # If an upload was in progress (new or update), abort the multipart upload
        if self.upload_id and self.layer_uuid and len(self.upload_items) > 0:
            try:
                # TODO: Aborting deletes the layer. This is wrong
                # TODO: Only the MultipartUpload objects for the given upload id should be deleted
                # TODO: Commented calling the abort until the issue is addressed
                # self.request.abort_upload_layer(self.layer_uuid, self.upload_id)
                self.log_message(
                    f"Aborted upload for layer {self.layer_uuid}, upload_id {self.upload_id}"
                )
            except Exception as ex:
                self.log_message(
                    f"Error aborting upload for layer {self.layer_uuid}: {ex}",
                    info=False,
                )
            return


class DefaultPriorityLayerDownloadTask(QgsTask):
    """Task for downloading the default PWL from the
    online server.

    The required information include download URL, file path for saving
    the downloaded file and extents for clipping the dataset.
    """

    status_message_changed = QtCore.pyqtSignal(ApiRequestStatus, str)
    error_occurred = QtCore.pyqtSignal()
    canceled = QtCore.pyqtSignal()
    completed = QtCore.pyqtSignal(str, str)
    started = QtCore.pyqtSignal()
    exited = QtCore.pyqtSignal()

    def __init__(self, priority_layer, save_file_path):
        super().__init__(tr("Downloading default priority layer"))
        self._downloader = None
        self._event_loop = None
        self._errors = None
        self._exited = False

        self.priority_layer = priority_layer
        self.save_file_path = save_file_path

        self.cplus_api_url = CplusApiUrl()

    @property
    def errors(self) -> typing.List[str]:
        """Gets any errors encountered during the download process.

        :returns: Download errors.
        :rtype: typing.List[str]
        """
        return [] if self._errors is None else self._errors

    @property
    def has_exited(self) -> bool:
        """Indicates whether the downloader has exited.

        :returns: True if the downloader exited, else False.
        :rtype: bool
        """
        return self._exited

    def cancel(self):
        """Cancel the download process."""
        if self._downloader:
            self._downloader.cancelDownload()
            self._update_download_status(ApiRequestStatus.CANCELED, "Download canceled")
            self.disconnect_receivers()

        super().cancel()

        if self._event_loop:
            self._event_loop.quit()

        log("Downloading priority layer task canceled.")

    def _on_error_occurred(self, error_messages: typing.List[str]):
        """Slot raised when the downloader encounters an error.

        :param error_messages: Error messages.
        :type error_messages: typing.List[str]
        """
        self._errors = error_messages

        err_msg = ", ".join(error_messages)
        log(f"Error in downloading priority layer dataset: {err_msg}", info=False)

        self._update_download_status(
            ApiRequestStatus.ERROR, tr("Download error. See logs for details.")
        )

        self._event_loop.quit()

        self.error_occurred.emit()

    def _on_download_canceled(self):
        """Slot raised when the download has been canceled."""
        log(f"Download of priority layer {self.priority_layer.get('name')} canceled.")

        self._event_loop.quit()

        self.canceled.emit()

    def _on_download_exited(self):
        """Slot raised when the download has exited."""
        self._event_loop.quit()

        self._exited = True

        self.exited.emit()

    def _on_download_completed(self, url: QtCore.QUrl):
        """Slot raised when the download is complete.

        :param url: Url of the file resource.
        :type url: QtCore.QUrl
        """
        completion_datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log(
            f"Download of {self.priority_layer.get('name')} successfully completed "
            f"on {completion_datetime_str}."
        )

        self._update_download_status(
            ApiRequestStatus.COMPLETED, tr("Download successful")
        )

        self._event_loop.quit()

        self._successfully_completed = True

        self.completed.emit(self.priority_layer.get("name"), self.save_file_path)

    def _on_progress_changed(self, received: int, total: int):
        """Slot raised indicating progress made by the downloader.

        :param received: Bytes received.
        :type received: int

        :param total: Total size of the file in bytes.
        :type total: int
        """
        total_float = float(total)
        if total_float == 0.0:
            self.setProgress(total_float)
        else:
            self.setProgress(received / total_float * 100)

    def _update_download_status(self, status: ApiRequestStatus, description: str):
        """Updates the settings with the online download status.

        :param status: Download status to save.
        :type status: ApiRequestStatus

        :param description: Brief description of the status.
        :type description: str
        """
        self.status_message_changed.emit(status, description)

    def disconnect_receivers(self):
        """Disconnects all custom signals related to the downloader. This is
        recommended prior to canceling the task.
        """
        self._downloader.downloadError.disconnect(self._on_error_occurred)
        self._downloader.downloadCanceled.disconnect(self._on_download_canceled)
        self._downloader.downloadProgress.disconnect(self._on_progress_changed)
        self._downloader.downloadCompleted.disconnect(self._on_download_completed)
        self._downloader.downloadExited.disconnect(self._on_download_exited)

    def run(self) -> bool:
        """Initiates the download of default priority layer process and
        returns a result indicating whether the process succeeded or failed.

        :returns: True if the download process succeeded or False it if
        failed.
        :rtype: bool
        """
        if self.isCanceled():
            return False

        # Get extents, URL and local path
        clip_to_studyarea = settings_manager.get_value(
            Settings.CLIP_TO_STUDYAREA, default=False, setting_type=bool
        )
        if clip_to_studyarea:
            # From vector layer
            study_area_path = settings_manager.get_value(
                Settings.STUDYAREA_PATH, default="", setting_type=str
            )
            if not study_area_path or not os.path.exists(study_area_path):
                log("Path for determining layer extent is invalid.", info=False)
                return False

            aoi_layer = QgsVectorLayer(study_area_path, "AOI Layer")
            if not aoi_layer.isValid():
                log("AOI layer is invalid.", info=False)
                return False

            source_crs = aoi_layer.crs()
            if not source_crs:
                log("CRS of AOI layer is undefined.", info=False)
                return False

            aoi_extent = aoi_layer.extent()
            if not aoi_extent:
                log("Extent of AOI layer is undefined.", info=False)
                return False

            # Reproject extent if required
            destination_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            if source_crs != destination_crs:
                aoi_extent = transform_extent(aoi_extent, source_crs, destination_crs)
        else:
            aoi_extent = None
            # From explicit extent definition
            settings_extent = settings_manager.get_value(
                Settings.SCENARIO_EXTENT, default=None
            )
            if settings_extent and len(settings_extent) == 4:
                aoi_extent = QgsRectangle(
                    float(settings_extent[0]),
                    float(settings_extent[2]),
                    float(settings_extent[1]),
                    float(settings_extent[3]),
                )

        if not aoi_extent:
            raise ValueError("Scenario extent is not defined or invalid.")

        url_bbox_part = extent_to_url_param(aoi_extent)
        if not url_bbox_part:
            log(
                "Unable to create the bbox query part of the default "
                "priority layer download URL.",
                info=False,
            )
            return False

        download_url_path = self.cplus_api_url.priority_layer_download(
            self.priority_layer.get("layer_uuid")
        )
        if not download_url_path:
            log(
                f"Source URL for priority layer {self.priority_layer.get('name')} not found.",
                info=False,
            )
            return False

        full_download_url = QtCore.QUrl(download_url_path)
        full_download_url.setQuery(url_bbox_part)

        if not self.save_file_path:
            log(
                "Save location for priority layer not specified.",
                info=False,
            )
            return False

        # Use to block downloader until it completes or encounters an error
        self._event_loop = QtCore.QEventLoop(self)

        self._downloader = QgsFileDownloader(
            full_download_url, self.save_file_path, delayStart=True
        )
        self._downloader.downloadError.connect(self._on_error_occurred)
        self._downloader.downloadCanceled.connect(self._on_download_canceled)
        self._downloader.downloadProgress.connect(self._on_progress_changed)
        self._downloader.downloadCompleted.connect(self._on_download_completed)
        self._downloader.downloadExited.connect(self._on_download_exited)

        self._update_download_status(
            ApiRequestStatus.NOT_STARTED, tr("Download not started")
        )

        self._downloader.startDownload()

        self.started.emit()

        self._update_download_status(
            ApiRequestStatus.IN_PROGRESS, tr("Download ongoing")
        )

        log(
            f"Started download of {self.priority_layer.get('name')} - {full_download_url.toString()} - "
            f"on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        self._event_loop.exec()

        return True


class CalculateNatureBaseZonalStatsTask(QgsTask):
    """Worker that starts a zonal statistics job on the server
    and polls progress.
    """

    status_message_changed = QtCore.pyqtSignal(str)
    results_ready = QtCore.pyqtSignal(object)
    task_finished = QtCore.pyqtSignal(bool)

    def __init__(
        self,
        bbox: typing.Union[str, list] = None,
        polling_interval: float = 3.0,
        parent=None,
    ):
        super().__init__(tr("Calculating mean zonal statistics of Naturebase layers"))
        self.status_message = None
        self.request = CplusApiRequest()
        self.urls = CplusApiUrl()
        self.result = None
        self.bbox = bbox
        self.polling_interval = polling_interval

    def _get_bbox_for_request(self) -> str:
        """Return bbox either from provided bbox or from settings."""
        if self.bbox:
            if isinstance(self.bbox, (list, tuple)):
                return ",".join(str(v) for v in self.bbox)

            return str(self.bbox)

        # Otherwise get saved extents from settings
        clip_to_studyarea = settings_manager.get_value(
            Settings.CLIP_TO_STUDYAREA, default=False, setting_type=bool
        )
        if clip_to_studyarea:
            # From vector layer
            study_area_path = settings_manager.get_value(
                Settings.STUDYAREA_PATH, default="", setting_type=str
            )
            if not study_area_path or not os.path.exists(study_area_path):
                log("Path for determining layer extent is invalid.", info=False)
                return ""

            aoi_layer = QgsVectorLayer(study_area_path, "AOI Layer")
            if not aoi_layer.isValid():
                log("AOI layer is invalid.", info=False)
                return ""

            source_crs = aoi_layer.crs()
            if not source_crs:
                log("CRS of AOI layer is undefined.", info=False)
                return ""

            aoi_extent = aoi_layer.extent()
            if not aoi_extent:
                log("Extent of AOI layer is undefined.", info=False)
                return ""

            # Reproject extent if required
            destination_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            if source_crs != destination_crs:
                aoi_extent = transform_extent(aoi_extent, source_crs, destination_crs)

            extent = [
                aoi_extent.xMinimum(),
                aoi_extent.yMinimum(),
                aoi_extent.xMaximum(),
                aoi_extent.yMaximum(),
            ]
        else:
            extent = None
            # From explicit extent definition
            settings_extent = settings_manager.get_value(
                Settings.SCENARIO_EXTENT, default=None
            )
            if settings_extent:
                # Ensure in minX, minY, maxX, maxY format
                extent = [
                    float(settings_extent[0]),
                    float(settings_extent[2]),
                    float(settings_extent[1]),
                    float(settings_extent[3]),
                ]

        if not extent or len(extent) < 4:
            raise ValueError("Scenario extent is not defined or invalid.")

        return f"{extent[0]},{extent[1]},{extent[2]},{extent[3]}"

    def run(self) -> bool:
        """Initiate the zonal statistics calculation and poll until
        completed.

        Use `poll_once` method for non-blocking iterations.

        :returns: True if the calculation process succeeded or
        False it if failed.
        :rtype: bool
        """
        try:
            bbox_str = self._get_bbox_for_request()
            log(f"BBOX for Zonal stats request: {bbox_str}")
        except Exception as e:
            log(f"Invalid bbox: {e}")
            return False

        self.setProgress(0)
        self.set_status_message("Starting zonal statistics job on server...")
        response = None
        try:
            log(f"BBOX for zonal stats calculation: {bbox_str}")
            response, status = self.request.calculate_zonal_statistics(bbox_str)
        except Exception as ex:
            log(
                f"Failed to call zonal statistics endpoint: {ex}",
                info=False,
            )
            return False

        if response is None:
            log(
                "No response received from the server.",
                info=False,
            )
            return False

        if status < 200 or status >= 300:
            log(
                f"Server returned error when starting zonal statistics: {response}",
                info=False,
            )
            return False

        task_uuid = response.get("task_uuid", "")
        if not task_uuid:
            log(f"No task id returned: {response}", info=False)
            return False

        self.set_status_message(
            f"Zonal statistics calculation started, task id: {task_uuid}"
        )

        polling = self.request.fetch_zonal_statistics_progress(task_uuid)

        # Repeatedly poll until final status
        status = True
        try:
            while True:
                if self.isCanceled():
                    polling.cancelled = True
                    status = False
                    break

                try:
                    # Use poll once which is non-blocking
                    response = polling.poll_once() or {}
                except CplusApiRequestError as ex:
                    log(f"Polling error: {ex}", info=False)
                    status = False
                    break
                except Exception as ex:
                    log(
                        f"Error while polling zonal statistics progress: {ex}",
                        info=False,
                    )
                    time.sleep(self.polling_interval)
                    continue

                status_str = response.get("status")
                progress = response.get("progress", 0.0)
                try:
                    progress_value = float(progress)
                except Exception as ex:
                    log(
                        f"Failed to determine progress: {ex}",
                        info=False,
                    )
                    progress_value = 0.0

                self.setProgress(int(progress_value))
                self.set_status_message(
                    f"Zonal statistics: {status_str} ({progress_value:.1f}%)"
                )

                if status_str in CplusApiPooling.FINAL_STATUS_LIST:
                    if status_str != JOB_COMPLETED_STATUS:
                        status = False
                    self.result = response
                    break

                # Sleep between poll iterations so that we can control the frequency
                time.sleep(self.polling_interval)

            return status
        except Exception as ex:
            log(
                f"Error while polling zonal statistics progress: {ex}",
                info=False,
            )
            return False

    def finished(self, result: bool):
        """Emit signals and persist results in settings."""
        if result and self.result:
            results = self.result.get("results", [])
            self.results_ready.emit(results)
            self.set_status_message("Zonal statistics completed")
            if len(results) == 0:
                log(
                    "Empty result set for zonal statistics calculation of Naturebase layers.",
                    info=False,
                )
            sorted_results = []
            if results:
                sorted_results = sorted(results, key=lambda d: d["layer_name"])
            result_info = ResultInfo(sorted_results, self.result.get("finished_at", ""))
            settings_manager.save_nature_base_zonal_stats(result_info)
        else:
            self.set_status_message("Zonal statistics task failed or was cancelled")

        self.task_finished.emit(result)

    def set_status_message(self, message: str):
        self.status_message = message
        self.status_message_changed.emit(self.status_message)


def calculate_zonal_stats_task() -> QgsTask:
    """Convenience function that initiates a task for calculating
    zonal stats.

    It checks if there are any existing zonal stats tasks and
    cancels them before initiating a new one.

    :returns: Task for calculating mean zonal
    statistics.
    :rtype: QgsTask
    """
    zonal_stats_tasks = [
        task
        for task in QgsApplication.taskManager().tasks()
        if isinstance(task, CalculateNatureBaseZonalStatsTask)
    ]
    for zs_task in zonal_stats_tasks:
        zs_task.cancel()

    new_zonal_stats_task = CalculateNatureBaseZonalStatsTask()
    QgsApplication.taskManager().addTask(new_zonal_stats_task)

    return new_zonal_stats_task
