# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""


import os

from qgis.PyQt import QtCore, QtGui
from qgis.core import Qgis, QgsMessageLog

from .definitions.defaults import DOCUMENTATION_SITE, PRIORITY_LAYERS, PRIORITY_GROUPS
from .conf import settings_manager


def tr(message):
    """Get the translation for a string using Qt translation API.
    We implement this ourselves since we do not inherit QObject.

    :param message: String for translation.
    :type message: str, QString

    :returns: Translated version of message.
    :rtype: QString
    """
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    return QtCore.QCoreApplication.translate("QgisCplus", message)


def log(
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
    level = Qgis.Info if info else Qgis.Warning
    QgsMessageLog.logMessage(
        message,
        name,
        level=level,
        notifyUser=notify,
    )


def open_documentation(url=None):
    """Opens documentation website in the default browser"""
    url = DOCUMENTATION_SITE if url is None else url
    result = QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
    return result


def create_priority_layers():
    """Prepares the priority weighted layers UI with the defaults"""

    if not settings_manager.get_value(
        "default_priority_layers_set", default=False, setting_type=bool
    ):
        log("Creating plugin priority layers")

        groups = []
        for group in PRIORITY_GROUPS:
            stored_group = {}
            stored_group["name"] = group["name"]
            stored_group["value"] = 0
            groups.append(stored_group)

        for layer in PRIORITY_LAYERS:
            layer["groups"] = groups
            settings_manager.save_priority_layer(layer)

        settings_manager.set_value("default_priority_layers_set", True)

class FileUtils:
    """
    Provides functionality for commonly used file-related operations.
    """

    @staticmethod
    def plugin_dir() -> str:
        """Returns the root directory of the plugin.

        :returns: Root directory of the plugin.
        :rtype: str
        """
        return os.path.join(os.path.dirname(os.path.realpath(__file__)))

    @staticmethod
    def get_icon(file_name: str) -> QtGui.QIcon:
        """Creates an icon based on the icon name in the 'icons' folder.

        :param file_name: File name which should include the extension.
        :type file_name: str

        :returns: Icon object matching the file name.
        :rtype: QtGui.QIcon
        """
        icon_path = os.path.normpath(
            f"{FileUtils.plugin_dir()}/icons/{file_name}"
        )

        if not os.path.exists(icon_path):
            return QtGui.QIcon()

        return QtGui.QIcon(icon_path)
