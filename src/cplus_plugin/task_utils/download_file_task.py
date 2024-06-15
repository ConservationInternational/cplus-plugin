import random
from time import sleep

import os
from qgis.core import (
    QgsApplication,
    QgsTask,
    QgsMessageLog,
    Qgis,
    QgsNetworkAccessManager,
)
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QUrl, QCoreApplication, QTimer
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.PyQt.QtWidgets import QApplication
from ..utils import log

MESSAGE_CATEGORY = "RandomIntegerSumTask"


class DownloadTask(QgsTask):
    def __init__(self, description, url, output_path):
        super().__init__(description)
        self.url = url
        self.output_path = output_path
        self.network_manager = QgsNetworkAccessManager.instance()

    def run(self):
        log("RUN")
        self.request = QNetworkRequest(QUrl(self.url))
        self.reply = self.network_manager.get(self.request)
        self.reply.finished.connect(self.download_finished)
        self.reply.readyRead.connect(self.ready_read)
        self.data = b""
        self.completed = False

        # Run a loop until the download is finished
        while not self.completed:
            QCoreApplication.processEvents()

        return not self.reply.error()

    def ready_read(self):
        log("READY READ")
        self.data += self.reply.readAll()

    def download_finished(self):
        log("FINISH")
        if self.reply.error() == QNetworkReply.NoError:
            with open(self.output_path, "wb") as f:
                f.write(self.data)
            QgsMessageLog.logMessage(
                "Download finished successfully.", "DownloadTask", Qgis.Info
            )
        else:
            QgsMessageLog.logMessage(
                f"Error: {self.reply.errorString()}", "DownloadTask", Qgis.Critical
            )
        self.completed = True
