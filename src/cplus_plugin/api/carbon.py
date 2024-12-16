# -*- coding: utf-8 -*-
"""
API requests for managing carbon layers.
"""

from datetime import datetime
import typing

from qgis.core import QgsApplication, QgsFileDownloader, QgsRectangle, QgsTask
from qgis.PyQt import QtCore

from .base import ApiRequestStatus
from ..conf import settings_manager, Settings
from ..models.helpers import extent_to_url_param
from ..utils import log, tr


class IrrecoverableCarbonDownloadTask(QgsTask):
    """Task for downloading the irrecoverable carbon dataset from the
    online server.

    The required information i.e. download URL, file path for saving
    the downloaded file and extents for clipping the dataset are fetched
    from the settings hence they need to be defined for the download
    process to be successfully initiated.
    """

    error_occurred = QtCore.pyqtSignal()
    canceled = QtCore.pyqtSignal()
    completed = QtCore.pyqtSignal()
    started = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__(tr("Downloading irrecoverable carbon dataset"))
        self._downloader = None
        self._event_loop = None
        self._errors = None
        self._successfully_completed = False

    @property
    def errors(self) -> typing.List[str]:
        """Gets any errors encountered during the download process.

        :returns: Download errors.
        :rtype: typing.List[str]
        """
        return [] if self._errors is None else self._errors

    @property
    def has_completed(self) -> bool:
        """Indicates whether the file was successfully downloaded.

        :returns: True if the file was successfully downloaded, else
        False.
        :rtype: bool
        """
        return self._successfully_completed

    def cancel(self):
        """Cancel the download process."""
        if self._downloader:
            self._downloader.cancelDownload()
            self._update_download_status(ApiRequestStatus.CANCELED, "Download canceled")
            self.disconnect_receivers()

        self._event_loop.quit()

        super().cancel()

        log("Irrecoverable carbon dataset task canceled.")

    def _on_error_occurred(self, error_messages: typing.List[str]):
        """Slot raised when the downloader encounters an error.

        :param error_messages: Error messages.
        :type error_messages: typing.List[str]
        """
        self._errors = error_messages

        err_msg = ", ".join(error_messages)
        log(f"Error in downloading irrecoverable carbon dataset: {err_msg}", info=False)

        self._update_download_status(
            ApiRequestStatus.ERROR, tr("Download error. See logs for details.")
        )

        self._event_loop.quit()

        self.error_occurred.emit()

    def _on_download_canceled(self):
        """Slot raised when the download has been canceled."""
        log("Download of irrecoverable carbon dataset canceled.")

        self._event_loop.quit()

        self.canceled.emit()

    def _on_download_completed(self, url: QtCore.QUrl):
        """Slot raised when the download is complete.

        :param url: Url of the file resource.
        :type url: QtCore.QUrl
        """
        completion_datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log(
            f"Download of irrecoverable carbon dataset successfully completed "
            f"on {completion_datetime_str}."
        )

        self._update_download_status(
            ApiRequestStatus.COMPLETED, tr("Download successful")
        )

        self._event_loop.quit()

        self._successfully_completed = True

        self.completed.emit()

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
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_DOWNLOAD_STATUS, status.value
        )
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_STATUS_DESCRIPTION, description
        )

    def disconnect_receivers(self):
        """Disconnects all custom signals related to the downloader. This is
        recommended prior to canceling the task.
        """
        self._downloader.downloadError.disconnect(self._on_error_occurred)
        self._downloader.downloadCanceled.disconnect(self._on_download_canceled)
        self._downloader.downloadProgress.disconnect(self._on_progress_changed)
        self._downloader.downloadCompleted.disconnect(self._on_download_completed)

    def run(self) -> bool:
        """Initiates the download of irrecoverable carbon dataset process and
        returns a result indicating whether the process succeeded or failed.

        :returns: True if the download process succeeded or False it if
        failed.
        :rtype: bool
        """
        if self.isCanceled():
            return False

        # Get extents, URL and local path
        extent = settings_manager.get_value(Settings.SCENARIO_EXTENT, default=None)
        if extent is None:
            log(
                "Scenario extent not defined for downloading irrecoverable "
                "carbon dataset.",
                info=False,
            )
            return False

        if len(extent) < 4:
            log(
                "Definition of scenario extent is incorrect. Consists of "
                "less than 4 segments.",
                info=False,
            )
            return False

        extent_rectangle = QgsRectangle(
            float(extent[0]), float(extent[2]), float(extent[1]), float(extent[3])
        )
        url_bbox_part = extent_to_url_param(extent_rectangle)
        if not url_bbox_part:
            log(
                "Unable to create the bbox query part of the irrecoverable "
                "carbon download URL.",
                info=False,
            )
            return False

        base_download_url_path = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_SOURCE, default="", setting_type=str
        )
        if not base_download_url_path:
            log("Source URL for irrecoverable carbon dataset not found.", info=False)
            return False

        full_download_url = QtCore.QUrl(base_download_url_path)
        full_download_url.setQuery(url_bbox_part)

        save_path = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH,
            default="",
            setting_type=str,
        )
        if not save_path:
            log(
                "Save location for irrecoverable carbon dataset not specified.",
                info=False,
            )
            return False

        # Use to block downloader until it completes or encounters an error
        self._event_loop = QtCore.QEventLoop(self)

        self._downloader = QgsFileDownloader(
            full_download_url, save_path, delayStart=True
        )
        self._downloader.downloadError.connect(self._on_error_occurred)
        self._downloader.downloadCanceled.connect(self._on_download_canceled)
        self._downloader.downloadProgress.connect(self._on_progress_changed)
        self._downloader.downloadCompleted.connect(self._on_download_completed)

        self._update_download_status(
            ApiRequestStatus.NOT_STARTED, tr("Download not started")
        )

        self._downloader.startDownload()

        self.started.emit()

        self._update_download_status(
            ApiRequestStatus.IN_PROGRESS, tr("Download ongoing")
        )

        log(
            f"Started download of irrecoverable carbon dataset - {full_download_url.toString()} - "
            f"on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        self._event_loop.exec_()

        return True


def get_downloader_task() -> typing.Optional[IrrecoverableCarbonDownloadTask]:
    """Gets the irrecoverable carbon task downloader in the QgsTaskManager.

    :returns: The irrecoverable carbon task downloader in the QgsTaskManager
    or None if not found.
    :rtype: IrrecoverableCarbonDownloadTask
    """
    ic_tasks = [
        task
        for task in QgsApplication.taskManager().tasks()
        if isinstance(task, IrrecoverableCarbonDownloadTask)
    ]
    if len(ic_tasks) == 0:
        return None

    return ic_tasks[0]


def start_irrecoverable_carbon_download():
    """Starts the process of downloading the reference irrecoverable carbon dataset.

    Any ongoing downloading processing will be canceled.
    """
    existing_download_task = get_downloader_task()
    if existing_download_task:
        existing_download_task.cancel()

    new_download_task = IrrecoverableCarbonDownloadTask()
    QgsApplication.taskManager().addTask(new_download_task)
