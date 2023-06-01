"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os.path

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QMainWindow, QVBoxLayout

# Initialize Qt resources from file resources.py
from .resources import *

from .gui.qgis_cplus_main import QgisCplusMain

from .conf import settings_manager

from .utils import create_priority_layers
from .settings import CplusOptionsFactory

class QgisCplus:
    """QGIS CPLUS Plugin Implementation."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        locale = QgsSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(self.plugin_dir, "i18n", "CPLUS{}.qm".format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr("&CPLUS")
        self.pluginIsActive = False
        self.toolbar = self.iface.addToolBar("Open CPLUS")
        self.toolbar.setObjectName("CPLUS")

        if not settings_manager.get_value(
            "default_priority_layers_set", default=False, setting_type=bool
        ):
            create_priority_layers()

        self.main_widget = QgisCplusMain(
            iface=self.iface, parent=self.iface.mainWindow()
        )

        self.options_factory = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.
        :param message: String for translation.
        :type message: str, QString
        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate("CPLUS", message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_web_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_web_menu: Flag indicating whether the action
            should also be added to the web menu. Defaults to True.
        :type add_to_web_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        if add_to_web_menu:
            self.iface.addPluginToWebMenu(self.menu, action)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ":/plugins/cplus_plugin/icon.svg"
        self.add_action(
            icon_path,
            text=self.tr("Open CPLUS"),
            callback=self.run,
            parent=self.iface.mainWindow(),
        )

        # Adds the settings to the QGIS options panel
        self.options_factory = CplusOptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin widget is closed"""
        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        try:
            settings_manager.delete_priority_layers()
            settings_manager.set_value("default_priority_layers_set", False)
            for action in self.actions:
                self.iface.removePluginMenu(self.tr("&CPLUS"), action)
                self.iface.removePluginWebMenu(self.tr("&CPLUS"), action)
                self.iface.removeToolBarIcon(action)

        except Exception as e:
            pass

    def run(self):
        if self.main_widget == None:
            self.main_widget = QgisCplusMain(
                iface=self.iface, parent=self.iface.mainWindow()
            )

        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.main_widget)
        self.main_widget.show()

        if not self.pluginIsActive:
            self.pluginIsActive = True
