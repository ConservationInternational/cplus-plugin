# coding=utf-8

"""Plugin main/core.

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
from qgis.PyQt.QtWidgets import QToolButton
from qgis.PyQt.QtWidgets import QMenu

from .definitions.defaults import (
    ABOUT_DOCUMENTATION_SITE,
    DOCUMENTATION_SITE,
    USER_DOCUMENTATION_SITE,
    ICON_PATH,
    OPTIONS_TITLE,
)
from .settings import CplusOptionsFactory

from .utils import (
    log,
    open_documentation,
)

from .conf import Settings, settings_manager
from .definitions.defaults import (
    DEFAULT_IMPLEMENTATION_MODELS,
    DEFAULT_NCS_PATHWAYS,
    PRIORITY_GROUPS,
    PRIORITY_LAYERS,
)
from .definitions.constants import NCS_PATHWAY_SEGMENT


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
        self.pluginIsActive = False

        self.menu = QMenu("&CPLUS")
        self.menu.setIcon(QIcon(ICON_PATH))

        self.raster_menu = self.iface.rasterMenu()
        self.raster_menu.addMenu(self.menu)

        self.toolbar = self.iface.addToolBar("Open CPLUS")
        self.toolbar.setObjectName("CPLUS")
        self.toolButton = QToolButton()
        self.toolButton.setMenu(QMenu())
        self.toolButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.toolBtnAction = self.toolbar.addWidget(self.toolButton)
        self.actions.append(self.toolBtnAction)

        if not settings_manager.get_value(
            "default_priority_layers_set", default=False, setting_type=bool
        ):
            create_priority_layers()

        self.main_widget = QgisCplusMain(
            iface=self.iface, parent=self.iface.mainWindow()
        )

        self.options_factory = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message) -> str:
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.

        Args:
            message (str): String for translation

        Returns:
            TranslatedMessage (QString): Translated version of the message
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
        set_as_default_action=False,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar.

        Args:
            icon_path (str): Path to the icon for this action
            text (str): Text that should be shown in menu items for this action
            callback (function): Function to be called when the action is triggered
            enabled_flag (bool): A flag indicating if the action should be enabled
            add_to_menu (bool): Flag indicating whether the action should also be added to the menu
            add_to_web_menu (bool): Flag indicating whether the action should also be added to the web menu
            add_to_toolbar (bool): Flag indicating whether the action should also be added to the toolbar
            set_as_default_action (bool): Flag indicating whether the action is the default action
            status_tip (str): Optional text to show in a popup when mouse pointer hovers over the action
            parent (QWidget): Parent widget for the new action
            whats_this (str): Optional text to show in the status bar when the mouse pointer hovers over the action

        Returns:
            Action (QAction): The action that was created
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
            self.menu.addAction(action)

        # If we want to read this
        # if add_to_web_menu:
        #     self.iface.addPluginToWebMenu(self.menu, action)

        if add_to_toolbar:
            self.toolButton.menu().addAction(action)

            if set_as_default_action:
                self.toolButton.setDefaultAction(action)

        if add_to_menu:
            self.menu.addAction(action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.add_action(
            ICON_PATH,
            text=self.tr("CPLUS"),
            callback=self.run,
            parent=self.iface.mainWindow(),
            set_as_default_action=True,
        )

        self.add_action(
            os.path.join(os.path.dirname(__file__), "icons", "settings.svg"),
            text=self.tr("Settings"),
            callback=self.run_settings,
            parent=self.iface.mainWindow(),
            status_tip=self.tr("CPLUS Settings"),
        )

        self.add_action(
            os.path.join(os.path.dirname(__file__), "icons", "mActionHelpContents_green.svg"),
            text=self.tr("Help"),
            callback=self.open_help,
            parent=self.iface.mainWindow(),
            status_tip=self.tr("CPLUS Help"),
        )

        self.add_action(
            os.path.join(os.path.dirname(__file__), "icons", "info_green.svg"),
            text=self.tr("About"),
            callback=self.open_about,
            parent=self.iface.mainWindow(),
            status_tip=self.tr("CPLUS About"),
        )

        # Adds the settings to the QGIS options panel
        self.options_factory = CplusOptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)

        # Initialize default model components
        initialize_default_settings()

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin widget is closed."""
        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        try:
            for action in self.actions:
                self.iface.removePluginMenu(self.tr("&CPLUS"), action)
                self.iface.removePluginWebMenu(self.tr("&CPLUS"), action)
                self.iface.removeToolBarIcon(action)

        except Exception as e:
            pass

    def run(self):
        """Creates the main widget for the plugin."""
        if self.main_widget is None:
            self.main_widget = QgisCplusMain(
                iface=self.iface, parent=self.iface.mainWindow()
            )

        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.main_widget)
        self.main_widget.show()

        if not self.pluginIsActive:
            self.pluginIsActive = True

    def run_settings(self):
        """Options the CPLUS settings in the QGIS options dialog."""
        self.iface.showOptionsDialog(currentPage=OPTIONS_TITLE)

    def open_help(self):
        """Opens documentation home page for the plugin in a browser"""
        open_documentation(DOCUMENTATION_SITE)

    def open_about(self):
        """Opens the about documentation for the plugin in a browser"""
        open_documentation(ABOUT_DOCUMENTATION_SITE)


def create_priority_layers():
    """Prepares the priority weighted layers UI with the defaults priority groups"""

    if not settings_manager.get_value(
        "default_priority_layers_set", default=False, setting_type=bool
    ):
        log(f"Initializing priority layers and groups")

        groups = []
        for group in PRIORITY_GROUPS:
            group["value"] = 0
            settings_manager.save_priority_group(group)

        for layer in PRIORITY_LAYERS:
            layer["groups"] = groups
            settings_manager.save_priority_layer(layer)

        settings_manager.set_value("default_priority_layers_set", True)


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

