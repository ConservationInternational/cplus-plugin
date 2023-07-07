# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""


import os
from pathlib import Path

from qgis.PyQt import QtCore, QtGui
from qgis.core import Qgis, QgsApplication, QgsMessageLog

from .conf import Settings, settings_manager
from .definitions.defaults import (
    DEFAULT_IMPLEMENTATION_MODELS,
    DEFAULT_NCS_PATHWAYS,
    DOCUMENTATION_SITE,
)
from .definitions.constants import NCS_PATHWAY_SEGMENT


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


def is_dark_theme() -> bool:
    """Checks if the current QGIS UI theme is dark mode.

    :returns: True if the current UI theme is on dark mode, else False.
    :rtype: bool
    """
    if QgsApplication.instance().themeName() == "Night Mapping":
        return True

    return False


def initialize_default_settings():
    """Initialize default model components such as NCS pathways
    and implementation models.

    It will check if there are existing components using the UUID
    and only add the ones that do not exist in the settings.

    This is normally called during plugin startup.
    """
    # Add default pathways
    for ncs_dict in DEFAULT_NCS_PATHWAYS:
        try:
            ncs_uuid = ncs_dict["uuid"]
            ncs = settings_manager.get_ncs_pathway(ncs_uuid)
            if ncs is None:
                # Update dir
                base_dir = settings_manager.get_value(Settings.BASE_DIR, None)
                if base_dir is not None:
                    file_name = ncs_dict["path"]
                    absolute_path = f"{base_dir}/{NCS_PATHWAY_SEGMENT}/{file_name}"
                    abs_path = str(os.path.normpath(absolute_path))
                    ncs_dict["path"] = abs_path
                ncs_dict["user_defined"] = False
                settings_manager.save_ncs_pathway(ncs_dict)
        except KeyError as ke:
            log(f"Default NCS configuration load error - {str(ke)}")
            continue

    # Add default implementation models
    for imp_model_dict in DEFAULT_IMPLEMENTATION_MODELS:
        try:
            imp_model_uuid = imp_model_dict["uuid"]
            imp_model = settings_manager.get_implementation_model(imp_model_uuid)
            if imp_model is None:
                settings_manager.save_implementation_model(imp_model_dict)
        except KeyError as ke:
            log(f"Default implementation model configuration load error - {str(ke)}")
            continue


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
        icon_path = os.path.normpath(f"{FileUtils.plugin_dir()}/icons/{file_name}")

        if not os.path.exists(icon_path):
            return QtGui.QIcon()

        return QtGui.QIcon(icon_path)

    @staticmethod
    def create_ncs_pathways_dir(base_dir: str):
        """Creates an NCS sub-directory under BASE_DIR. Skips
        creation of the sub-directory if it already exists.
        """
        ncs_pathway_dir = f"{base_dir}/{NCS_PATHWAY_SEGMENT}"
        p = Path(ncs_pathway_dir)
        if not p.exists():
            p.mkdir(parents=True)
