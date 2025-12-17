# -*- coding: utf-8 -*-
"""
API requests for managing carbon layers.
"""

from datetime import datetime
import os
import typing

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFileDownloader,
    QgsRectangle,
    QgsTask,
    QgsVectorLayer,
)
from qgis.PyQt import QtCore

from .base import ApiRequestStatus
from ..conf import settings_manager, Settings
from ..models.helpers import extent_to_url_param
from ..utils import log, tr, transform_extent


class BaseCarbonDownloadTask(QgsTask):
    """Base task for downloading carbon datasets from the online server.

    Required information i.e. download URL, file path for saving
    the downloaded file and extents for clipping the dataset are fetched
    from the settings hence they need to be defined for the download
    process to be successfully initiated.  Alternatively, these can be
    provided directly in the constructor.
    """

    error_occurred = QtCore.pyqtSignal()
    canceled = QtCore.pyqtSignal()
    completed = QtCore.pyqtSignal()
    started = QtCore.pyqtSignal()
    exited = QtCore.pyqtSignal()
    status_message_changed = QtCore.pyqtSignal(ApiRequestStatus, str)

    def __init__(
        self,
        task_description: str,
        download_url: typing.Optional[str] = None,
        local_path: typing.Optional[str] = None,
    ):
        """Initialize the base carbon download task.

        :param task_description:  Description of the task.
        :type task_description: str

        :param download_url: Optional URL for downloading the dataset.  If not
        provided, it will be fetched from settings.
        :type download_url: typing.Optional[str]

        :param local_path: Optional local file path for saving the downloaded
        file. If not provided, it will be fetched from settings.
        : type local_path: typing.Optional[str]
        """
        super().__init__(task_description)
        self._downloader = None
        self._event_loop = None
        self._errors = None
        self._exited = False
        self._successfully_completed = False
        self._download_url = download_url
        self._local_path = local_path

    @property
    def source_url_setting(self) -> typing.Optional[Settings]:
        """Gets the Settings enum for the source URL.

        :returns: Settings enum for source URL.
        :rtype: Settings
        """
        return None

    @property
    def local_path_setting(self) -> typing.Optional[Settings]:
        """Gets the Settings enum for the local save path.

        :returns: Settings enum for local path.
        :rtype: Settings
        """
        return None

    @property
    def download_status_setting(self) -> typing.Optional[Settings]:
        """Gets the Settings enum for the download status.

        :returns: Settings enum for download status.
        :rtype: Settings
        """
        return None

    @property
    def status_description_setting(self) -> typing.Optional[Settings]:
        """Gets the Settings enum for the status description.

        :returns: Settings enum for status description.
        :rtype: Settings
        """
        return None

    @property
    def dataset_name(self) -> str:
        """Gets the human-readable name of the dataset.

        :returns: Dataset name.
        :rtype: str
        """
        return ""

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

        log(f"{self.dataset_name} dataset task canceled.")

    def _on_error_occurred(self, error_messages: typing.List[str]):
        """Slot raised when the downloader encounters an error.

        :param error_messages: Error messages.
        :type error_messages: typing.List[str]
        """
        self._errors = error_messages

        err_msg = ", ".join(error_messages)
        log(f"Error in downloading {self.dataset_name} dataset: {err_msg}", info=False)

        self._update_download_status(
            ApiRequestStatus.ERROR, tr("Download error. See logs for details.")
        )

        self._event_loop.quit()

        self.error_occurred.emit()

    def _on_download_canceled(self):
        """Slot raised when the download has been canceled."""
        log(f"Download of {self. dataset_name} dataset canceled.")

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
            f"Download of {self. dataset_name} dataset in {self._get_file_path()} "
            f"successfully completed on {completion_datetime_str}."
        )

        self._update_download_status(
            ApiRequestStatus.COMPLETED, tr("Download successful")
        )

        self._event_loop.quit()

        self._successfully_completed = True

        self.completed.emit()

    def _on_progress_changed(self, received: int, total: int):
        """Slot raised indicating progress made by the downloader.

        :param received:  Bytes received.
        :type received: int

        :param total:  Total size of the file in bytes.
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
        if self.download_status_setting:
            settings_manager.set_value(self.download_status_setting, status.value)

        if self.status_description_setting:
            settings_manager.set_value(self.status_description_setting, description)

        self.status_message_changed.emit(status, description)

    def disconnect_receivers(self):
        """Disconnects all custom signals related to the downloader. This is
        recommended prior to canceling the task.
        """
        if self._downloader:
            self._downloader.downloadError.disconnect(self._on_error_occurred)
            self._downloader.downloadCanceled.disconnect(self._on_download_canceled)
            self._downloader.downloadProgress.disconnect(self._on_progress_changed)
            self._downloader.downloadCompleted.disconnect(self._on_download_completed)
            self._downloader.downloadExited.disconnect(self._on_download_exited)

    def run(self) -> bool:
        """Initiates the download of carbon dataset process and
        returns a result indicating whether the process succeeded or failed.

        :returns: True if the download process succeeded or False it if
        failed.
        :rtype: bool
        """
        if self.isCanceled():
            return False

        # Get download URL - use constructor value if provided, otherwise get from settings
        if self._download_url:
            base_download_url_path = self._download_url
        else:
            base_download_url_path = settings_manager.get_value(
                self.source_url_setting, default="", setting_type=str
            )
        if not base_download_url_path:
            log(f"Source URL for {self.dataset_name} dataset not found.", info=False)
            return False

        # Get local save path - use constructor value if provided, otherwise get from settings
        save_path = self._get_file_path()
        if not save_path:
            log(
                f"Save location for {self.dataset_name} dataset not specified.",
                info=False,
            )
            return False

        # Get extents for creating the bbox query parameter
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
            log("Scenario extent is not defined or invalid.", info=False)
            return False

        url_bbox_part = extent_to_url_param(aoi_extent)
        if not url_bbox_part:
            log(
                f"Unable to create the bbox query part of the {self.dataset_name} "
                f"carbon download URL.",
                info=False,
            )
            return False

        full_download_url = QtCore.QUrl(base_download_url_path)
        full_download_url.setQuery(url_bbox_part)

        # Use to block downloader until it completes or encounters an error
        self._event_loop = QtCore.QEventLoop(self)

        self._downloader = QgsFileDownloader(
            full_download_url, save_path, delayStart=True
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
            f"Started download of {self.dataset_name} dataset - {full_download_url. toString()} - "
            f"on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        self._event_loop.exec()

        return True

    def _get_file_path(self) -> str:
        # Get the path for saving the download file.
        if self._local_path:
            save_path = self._local_path
        else:
            save_path = settings_manager.get_value(
                self.local_path_setting,
                default="",
                setting_type=str,
            )
        return save_path


class IrrecoverableCarbonDownloadTask(BaseCarbonDownloadTask):
    """Task for downloading the irrecoverable carbon dataset from the
    online server.
    """

    def __init__(
        self,
        download_url: typing.Optional[str] = None,
        local_path: typing.Optional[str] = None,
    ):
        """Initialize the irrecoverable carbon download task.

        :param download_url: Optional URL for downloading the dataset. If not
        provided, it will be fetched from settings.
        :type download_url: typing.Optional[str]

        :param local_path: Optional local file path for saving the downloaded
        file. If not provided, it will be fetched from settings.
        :type local_path: typing.Optional[str]
        """
        super().__init__(
            tr("Downloading irrecoverable carbon dataset"),
            download_url=download_url,
            local_path=local_path,
        )

    @property
    def source_url_setting(self) -> Settings:
        return Settings.IRRECOVERABLE_CARBON_ONLINE_SOURCE

    @property
    def local_path_setting(self) -> Settings:
        return Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH

    @property
    def download_status_setting(self) -> Settings:
        return Settings.IRRECOVERABLE_CARBON_ONLINE_DOWNLOAD_STATUS

    @property
    def status_description_setting(self) -> Settings:
        return Settings.IRRECOVERABLE_CARBON_ONLINE_STATUS_DESCRIPTION

    @property
    def dataset_name(self) -> str:
        return "irrecoverable carbon"


class StoredCarbonDownloadTask(BaseCarbonDownloadTask):
    """Task for downloading the stored carbon dataset from the
    online server.
    """

    def __init__(
        self,
        download_url: typing.Optional[str] = None,
        local_path: typing.Optional[str] = None,
    ):
        """Initialize the stored carbon download task.

        :param download_url: Optional URL for downloading the dataset. If not
        provided, it will be fetched from settings.
        :type download_url: typing.Optional[str]

        :param local_path: Optional local file path for saving the downloaded
        file. If not provided, it will be fetched from settings.
        :type local_path: typing.Optional[str]
        """
        super().__init__(
            tr("Downloading stored carbon dataset"),
            download_url=download_url,
            local_path=local_path,
        )

    @property
    def source_url_setting(self) -> Settings:
        return Settings.STORED_CARBON_ONLINE_SOURCE

    @property
    def dataset_name(self) -> str:
        return "stored carbon"


def get_downloader_task(task_class: type) -> typing.Optional[BaseCarbonDownloadTask]:
    """Gets a specific carbon task downloader in the QgsTaskManager.

    :param task_class: The class type of the task to retrieve.
    :type task_class: type

    :returns: The carbon task downloader in the QgsTaskManager
    or None if not found.
    :rtype: BaseCarbonDownloadTask
    """
    tasks = [
        task
        for task in QgsApplication.taskManager().tasks()
        if isinstance(task, task_class)
    ]
    if len(tasks) == 0:
        return None

    return tasks[0]


def start_carbon_download(
    task_class: type,
    download_url: typing.Optional[str] = None,
    local_path: typing.Optional[str] = None,
) -> BaseCarbonDownloadTask:
    """Starts the process of downloading a carbon dataset.

    Any ongoing downloading processing of the same type will be canceled.

    :param task_class: The class of the download task to start.
    :type task_class: type

    : param download_url: Optional URL for downloading the dataset. If not
    provided, it will be fetched from settings.
    :type download_url: typing.Optional[str]

    :param local_path:  Optional local file path for saving the downloaded
    file. If not provided, it will be fetched from settings.
    :type local_path:  typing.Optional[str]

    :returns: Instance of the carbon downloader task.
    :rtype: BaseCarbonDownloadTask
    """
    existing_download_task = get_downloader_task(task_class)
    if existing_download_task:
        existing_download_task.cancel()

    new_download_task = task_class(download_url=download_url, local_path=local_path)
    QgsApplication.taskManager().addTask(new_download_task)

    return new_download_task


# Convenience functions for backward compatibility
def get_irrecoverable_carbon_downloader_task() -> (
    typing.Optional[IrrecoverableCarbonDownloadTask]
):
    """Gets the irrecoverable carbon task downloader in the QgsTaskManager.

    :returns: The irrecoverable carbon task downloader in the QgsTaskManager
    or None if not found.
    :rtype: IrrecoverableCarbonDownloadTask
    """
    return get_downloader_task(IrrecoverableCarbonDownloadTask)


def start_irrecoverable_carbon_download(
    download_url: typing.Optional[str] = None, local_path: typing.Optional[str] = None
) -> IrrecoverableCarbonDownloadTask:
    """Starts the process of downloading the reference irrecoverable carbon dataset.

    Any ongoing downloading processing will be canceled.

    :param download_url: Optional URL for downloading the dataset. If not
    provided, it will be fetched from settings.
    :type download_url:  typing.Optional[str]

    :param local_path: Optional local file path for saving the downloaded
    file. If not provided, it will be fetched from settings.
    :type local_path: typing. Optional[str]

    :returns: Task for downloading irrecoverable carbon.
    :rtype: IrrecoverableCarbonDownloadTask
    """
    return start_carbon_download(
        IrrecoverableCarbonDownloadTask,
        download_url=download_url,
        local_path=local_path,
    )


def get_stored_carbon_downloader_task() -> typing.Optional[StoredCarbonDownloadTask]:
    """Gets the stored carbon task downloader in the QgsTaskManager.

    :returns: The stored carbon task downloader in the QgsTaskManager
    or None if not found.
    :rtype: StoredCarbonDownloadTask
    """
    return get_downloader_task(StoredCarbonDownloadTask)


def start_stored_carbon_download(
    download_url: typing.Optional[str] = None, local_path: typing.Optional[str] = None
):
    """Starts the process of downloading the reference stored carbon dataset.

    Any ongoing downloading processing will be canceled.

    :param download_url: Optional URL for downloading the dataset. If not
    provided, it will be fetched from settings.
    :type download_url: typing.Optional[str]

    :param local_path: Optional local file path for saving the downloaded
    file. If not provided, it will be fetched from settings.
    :type local_path: typing.Optional[str]

    :returns: Task for downloading stored carbon.
    :rtype: StoredCarbonDownloadTask
    """
    return start_carbon_download(
        StoredCarbonDownloadTask, download_url=download_url, local_path=local_path
    )
