import os
from pathlib import Path

import qgis.core
import qgis.gui
from qgis.gui import QgsOptionsPageWidget
from qgis.gui import QgsOptionsWidgetFactory
from qgis.PyQt import QtCore
from qgis.PyQt import QtGui
from qgis.PyQt import QtWidgets
from qgis.PyQt import uic
from qgis.PyQt.QtGui import QIcon
from qgis.utils import iface

Ui_DlgSettings, _ = uic.loadUiType(str(Path(__file__).parent / "ui/qgis_settings.ui"))

# MOVE THESE VARIABLES TO A DEFAULT OR CONF FILE
OPTIONS_TITLE = "CPLUS"
ICON_PATH = "/../../resources/"
OPTIONS_ICON = "icon.svg"


class TrendsEarthSettings(Ui_DlgSettings, QgsOptionsPageWidget):
    message_bar: qgis.gui.QgsMessageBar

    # def __init__(self, dock_widget, parent=None):
    def __init__(self, parent=None):
        QgsOptionsPageWidget.__init__(self, parent)

        self.setupUi(self)
        self.message_bar = qgis.gui.QgsMessageBar(self)
        self.layout().insertWidget(0, self.message_bar)
        # self.dock_widget = dock_widget

        self.settings = qgis.core.QgsSettings()

    def apply(self):
        """This is called on OK click in the QGIS options panel."""

        print('apply')

        return

    def closeEvent(self, event):
        super().closeEvent(event)


class CplusOptionsFactory(QgsOptionsWidgetFactory):
    def __init__(self):
        super().__init__()

        self.dock_widget = None
        self.setTitle(OPTIONS_TITLE)

        print('test')

    def icon(self):
        cplus_icon = os.path.join(ICON_PATH, OPTIONS_ICON)

        return QIcon(cplus_icon)

    def set_dock_widget(self, dock_widget):
        # Widget required to update the title for the dock based
        # on the offline mode state
        self.dock_widget = dock_widget

    def createWidget(self, parent):
        return TrendsEarthSettings(self.dock_widget, parent)

