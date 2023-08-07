# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""


import os
from pathlib import Path

from qgis.PyQt import QtCore, QtGui
from qgis.core import Qgis, QgsApplication, QgsMessageLog

from .definitions.defaults import DOCUMENTATION_SITE, REPORT_FONT_NAME, TEMPLATE_NAME
from .definitions.constants import NCS_CARBON_SEGMENT, NCS_PATHWAY_SEGMENT


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
    """Opens documentation website in the default browser

    :param url: URL link to documentation site (e.g. gh pages site)
    :type url: str

    """
    url = DOCUMENTATION_SITE if url is None else url
    result = QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
    return result


def get_report_font(size=11, bold=False, italic=False) -> QtGui.QFont:
    """Uses the default font family name to create a
    font for use in the report.

    :param size: The font point size, default is 11.
    :type size: int

    :param bold: True for bold font else False which is the default.
    :type bold: bool

    :param italic: True for font to be in italics else False which is the default.
    :type italic: bool

    :returns: Font to use in a report.
    :rtype: QtGui.QFont
    """
    font_weight = 50
    if bold is True:
        font_weight = 75

    # return QtGui.QFont(REPORT_FONT_NAME, size, font_weight, italic)
    return QtGui.QFont(REPORT_FONT_NAME, size, font_weight, italic)


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


def is_dark_theme() -> bool:
    """Checks if the current QGIS UI theme is dark mode.

    :returns: True if the current UI theme is on dark mode, else False.
    :rtype: bool
    """
    if QgsApplication.instance().themeName() == "Night Mapping":
        return True

    return False


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
    def report_template_path(file_name=None) -> str:
        """Get the absolute path to the template file with the given name.
        Caller needs to verify that the file actually exists.

        :param file_name: Template file name including the extension. If
        none is specified then it will use `main.qpt` as the default
        template name.
        :type file_name: str

        :returns: The absolute path to the template file with the given name.
        :rtype: str
        """
        if file_name is None:
            file_name = TEMPLATE_NAME

        absolute_path = f"{FileUtils.plugin_dir()}/app_data/reports/{file_name}"

        return os.path.normpath(absolute_path)

    @staticmethod
    def create_ncs_pathways_dir(base_dir: str):
        """Creates an NCS subdirectory under BASE_DIR. Skips
        creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        ncs_pathway_dir = f"{base_dir}/{NCS_PATHWAY_SEGMENT}"
        message = tr(
            "Missing parent directory when creating NCS pathways subdirectory."
        )
        FileUtils.create_new_dir(ncs_pathway_dir, message)

    @staticmethod
    def create_ncs_carbon_dir(base_dir: str):
        """Creates an NCS subdirectory for carbon layers under BASE_DIR.
        Skips creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        ncs_carbon_dir = f"{base_dir}/{NCS_CARBON_SEGMENT}"
        message = tr("Missing parent directory when creating NCS carbon subdirectory.")
        FileUtils.create_new_dir(ncs_carbon_dir, message)

    @staticmethod
    def create_new_dir(directory: str, log_message: str = ""):
        """Creates new file directory if it doesn't exist"""
        p = Path(directory)
        if not p.exists():
            try:
                p.mkdir()
            except FileNotFoundError:
                log(log_message)
