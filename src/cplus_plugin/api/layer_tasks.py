# coding=utf-8
"""
 Plugin tasks related to the layer
"""

import os
import json
import traceback
import typing

from qgis.core import Qgis, QgsTask, QgsProcessingFeedback, QgsProcessingContext
from qgis.PyQt import QtCore

from ..conf import settings_manager
from ..utils import (
    log,
    tr,
    CustomJsonEncoder,
    todict,
    compress_raster,
    get_layer_type,
    convert_size,
)
from .request import CplusApiRequest


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
            tmp_file = compress_raster(self.file_path, nodata_value=-9999.0)
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
