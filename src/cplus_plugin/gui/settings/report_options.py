# coding=utf-8

"""Plugin report settings."""

import os
import typing

import qgis.core
import qgis.gui

from qgis.analysis import QgsAlignRaster

from qgis.gui import QgsFileWidget, QgsOptionsPageWidget
from qgis.gui import QgsOptionsWidgetFactory
from qgis.PyQt import uic
from qgis.PyQt.QtGui import (
    QIcon,
    QShowEvent,
    QPixmap,
)
from qgis.utils import iface

from qgis.PyQt.QtWidgets import QWidget

from ...conf import (
    settings_manager,
    Settings,
)
from ...definitions.constants import CPLUS_OPTIONS_KEY, REPORTS_OPTIONS_KEY
from ...definitions.defaults import ICON_PATH, REPORT_OPTIONS_TILE
from ...utils import FileUtils, tr


Ui_ReportSettingsWidget, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/report_settings.ui")
)


class ReportSettingsWidget(QgsOptionsPageWidget, Ui_ReportSettingsWidget):
    """Report settings widget."""

    def __init__(self, parent=None):
        QgsOptionsPageWidget.__init__(self, parent)
        self.setupUi(self)

    def apply(self) -> None:
        """This is called on OK click in the QGIS options panel."""
        pass


class ReportOptionsFactory(QgsOptionsWidgetFactory):
    """Factory for defining CPLUS report settings."""

    def __init__(self) -> None:
        super().__init__()

        self.setTitle(REPORT_OPTIONS_TILE)
        self.setKey(REPORTS_OPTIONS_KEY)

    def icon(self) -> QIcon:
        """Returns the icon which will be used for the report settings item.

        :returns: An icon object which contains the provided custom icon
        :rtype: QIcon
        """
        return QIcon(ICON_PATH)

    def path(self) -> typing.List[str]:
        """
        Returns the path to place the widget page at.

        This instructs the registry to place the options tab under the
        main CPLUS settings.

        :returns: Path name of the main CPLUS settings.
        :rtype: list
        """
        return [CPLUS_OPTIONS_KEY]

    def createWidget(self, parent: QWidget) -> ReportSettingsWidget:
        """Creates a widget for report settings.

        :param parent: Parent widget
        :type parent: QWidget

        :returns: Widget for defining report settings.
        :rtype: ReportSettingsWidget
        """
        return ReportSettingsWidget(parent)
