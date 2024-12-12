# -*- coding: utf-8 -*-
"""
API requests for managing carbon layers.
"""
from numbers import Number
import os
from pathlib import Path
import traceback
import typing

from qgis.core import QgsApplication, QgsFileDownloader, QgsRectangle, QgsTask
from qgis.PyQt import QtCore

from ..conf import settings_manager, Settings
from ..models.helpers import extent_to_url_param
from ..utils import log, tr


class IrrecoverableCarbonDownloadTask(QgsTask):
    """Class for downloading the irrecoverable carbon data from the online server."""

    error_occurred = QtCore.pyqtSignal(list)
    canceled = QtCore.pyqtSignal()
    completed = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__(tr("Downloading irrecoverable carbon dataset"))
        self._downloader = None

    def cancel(self):
        """Cancel the download process."""
        if self._downloader:
            self._downloader.cancelDownload()

        super().cancel()

        log("Irrecoverable carbon dataset task canceled.")

    def _on_error_occurred(self, error_messages: typing.List[str]):
        """Slot raised when the downloader encounters an error.

        :param error_messages: Error messages.
        :type error_messages: typing.List[str]
        """
        self.error_occurred.emit(error_messages)

        err_msg = ", ".join(error_messages)
        log(f"Error in downloading irrecoverable carbon dataset: {err_msg}", info=False)

    def _on_download_canceled(self):
        """Slot raised when the download has been canceled."""
        self.canceled.emit()

        log("Download of irrecoverable carbon dataset canceled.")

    def _on_download_completed(self, url: QtCore.QUrl):
        """Slot raised when the download is complete.

        :param url: Url of the file resource.
        :type url: QtCore.QUrl
        """
        self.completed.emit()

        log("Download of irrecoverable carbon dataset successfully completed.")

    def _on_progress_changed(self, received: int, total: int):
        """Slot raised indicating progress made by the downloader.

        :param received: Bytes received.
        :type received: int

        :param total: Total size of the file in bytes.
        :type total: int
        """
        self.setProgress(received / float(total) * 100)

    def run(self) -> bool:
        """Initiates the report generation process and returns
        a result indicating whether the process succeeded or
        failed.

        :returns: True if the report generation process succeeded
        or False it if failed.
        :rtype: bool
        """
        if self.isCanceled():
            return False

        # Get extents, URL and local path
        extent = settings_manager.get_value(Settings.SCENARIO_EXTENT, default=None)
        if extent is None:
            if not extent:
                log(
                    "Scenario extent not defined for downloading irrecoverable "
                    "carbon dataset.",
                    info=False,
                )
                return False

        extent_rectangle = QgsRectangle(
            float(extent[0]), float(extent[2]), float(extent[1]), float(extent[3])
        )
        url_bbox_part = extent_to_url_param(extent_rectangle)

        download_url_path = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_SOURCE, default="", setting_type=str
        )
        if not download_url_path:
            log("Source URL for irrecoverable carbon dataset not found.", info=False)
            return False

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

        self._downloader = QgsFileDownloader(
            QtCore.QUrl(download_url_path), save_path, delayStart=True
        )
        self._downloader.downloadError.connect(self._on_error_occurred)
        self._downloader.downloadCanceled.connect(self._on_download_canceled)
        self._downloader.downloadProgress.connect(self._on_progress_changed)
        self._downloader.downloadCompleted.connect(self._on_download_completed)

        self._downloader.startDownload()

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
    """Starts the process of downloading the reference irrecoverable carbon dataset."""
    existing_download_task = get_downloader_task()
    if existing_download_task:
        existing_download_task.cancel()

    new_download_task = IrrecoverableCarbonDownloadTask()
    QgsApplication.taskManager().addTask(new_download_task)
