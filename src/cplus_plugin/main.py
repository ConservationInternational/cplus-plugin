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

from qgis.core import QgsApplication, QgsMasterLayoutInterface, QgsSettings
from qgis.gui import QgsGui, QgsLayoutDesignerInterface
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QMainWindow, QVBoxLayout

# Initialize Qt resources from file resources.py
from .resources import *

from .gui.qgis_cplus_main import QgisCplusMain
from qgis.PyQt.QtWidgets import QToolButton
from qgis.PyQt.QtWidgets import QMenu

from .conf import Settings, settings_manager
from .definitions.constants import (
    NCS_CARBON_SEGMENT,
    NCS_PATHWAY_SEGMENT,
    PRIORITY_LAYERS_SEGMENT,
)
from .definitions.defaults import (
    ABOUT_DOCUMENTATION_SITE,
    CI_LOGO_PATH,
    CPLUS_LOGO_PATH,
    DEFAULT_IMPLEMENTATION_MODELS,
    DEFAULT_LOGO_PATH,
    DEFAULT_NCS_PATHWAYS,
    DEFAULT_REPORT_DISCLAIMER,
    DEFAULT_REPORT_LICENSE,
    DOCUMENTATION_SITE,
    ICON_PATH,
    OPTIONS_TITLE,
    PRIORITY_GROUPS,
    PRIORITY_LAYERS,
)
from .gui.map_repeat_item_widget import CplusMapLayoutItemGuiMetadata
from .lib.reports.layout_items import CplusMapRepeatItemLayoutItemMetadata
from .lib.reports.manager import report_manager
from .models.helpers import (
    copy_layer_component_attributes,
    create_implementation_model,
    create_ncs_pathway,
)
from .settings import CplusOptionsFactory

from .utils import (
    FileUtils,
    log,
    open_documentation,
)


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

        :param message: String for translation
        :type message: str

        :returns: Translated version of the message
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
        set_as_default_action=False,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action
        :type text: str

        :param callback: Function to be called when the action is triggered
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also be added to the menu
        :type add_to_menu: bool

        :param add_to_web_menu: Flag indicating whether the action should also be added to the web menu
        :type add_to_web_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also be added to the toolbar
        :type add_to_toolbar: bool

        :param set_as_default_action: Flag indicating whether the action is the default action
        :type set_as_default_action: bool

        :param status_tip: Optional text to show in a popup when mouse pointer hovers over the action
        :type status_tip: str

        :param parent: Parent widget for the new action
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the mouse pointer hovers over the action
        :type whats_this: str

        :returns: The action that was created
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
            os.path.join(
                os.path.dirname(__file__), "icons", "mActionHelpContents_green.svg"
            ),
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

        # Initialize default report settings
        initialize_report_settings()

        # Adds the settings to the QGIS options panel
        self.options_factory = CplusOptionsFactory()
        self.iface.registerOptionsWidgetFactory(self.options_factory)

        # Initialize default model components
        initialize_model_settings()

        # Register custom layout items
        self.register_layout_items()

        # Register custom report variables when a layout is opened
        self.iface.layoutDesignerOpened.connect(self.on_layout_designer_opened)

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

    def on_layout_designer_opened(self, designer: QgsLayoutDesignerInterface):
        """Register custom report variables in a print layout only."""
        layout_type = designer.masterLayout().layoutType()
        if layout_type == QgsMasterLayoutInterface.PrintLayout:
            layout = designer.layout()
            report_manager.register_variables(layout)

    def register_layout_items(self):
        """Register custom layout items."""
        # Register map layout item
        QgsApplication.layoutItemRegistry().addLayoutItemType(
            CplusMapRepeatItemLayoutItemMetadata()
        )

        # Register map GUI metadata
        item_gui_registry = QgsGui.layoutItemGuiRegistry()
        map_item_gui_metadata = CplusMapLayoutItemGuiMetadata()
        item_gui_registry.addLayoutItemGuiMetadata(map_item_gui_metadata)

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


def initialize_model_settings():
    """Initialize default model components such as NCS pathways
    and implementation models.

    It will check if there are existing components using the UUID
    and only add the ones that do not exist in the settings.

    This is normally called during plugin startup.
    """
    # Create NCS subdirectories if BASE_DIR has been defined
    base_dir = settings_manager.get_value(Settings.BASE_DIR)
    if base_dir:
        # Create NCS pathways subdirectory
        FileUtils.create_ncs_pathways_dir(base_dir)

        # Create NCS carbon subdirectory
        FileUtils.create_ncs_carbon_dir(base_dir)

        # Create priority weighting layers subdirectory
        FileUtils.create_pwls_dir(base_dir)

    # Use carbon coefficient values for older-version NCS pathways
    carbon_coefficient = settings_manager.get_value(Settings.CARBON_COEFFICIENT, 0)

    # Add default pathways
    for ncs_dict in DEFAULT_NCS_PATHWAYS:
        try:
            ncs_uuid = ncs_dict["uuid"]
            ncs = settings_manager.get_ncs_pathway(ncs_uuid)
            if ncs is None:
                # Update dir
                base_dir = settings_manager.get_value(Settings.BASE_DIR, None)
                if base_dir is not None:
                    # Pathway location
                    file_name = ncs_dict["path"]
                    absolute_path = f"{base_dir}/{NCS_PATHWAY_SEGMENT}/{file_name}"
                    abs_path = str(os.path.normpath(absolute_path))
                    ncs_dict["path"] = abs_path

                    # Carbon location
                    carbon_file_names = ncs_dict["carbon_paths"]
                    abs_carbon_paths = []
                    for carbon_file_name in carbon_file_names:
                        abs_carbon_path = (
                            f"{base_dir}/{NCS_CARBON_SEGMENT}/{carbon_file_name}"
                        )
                        norm_carbon_path = str(os.path.normpath(abs_carbon_path))
                        abs_carbon_paths.append(norm_carbon_path)
                    ncs_dict["carbon_paths"] = abs_carbon_paths

                ncs_dict["user_defined"] = False
                ncs_dict["carbon_coefficient"] = carbon_coefficient
                settings_manager.save_ncs_pathway(ncs_dict)
            else:
                # Update carbon coefficient value
                # Check if carbon coefficient had previously been defined
                ncs_dict = settings_manager.get_ncs_pathway_dict(ncs_uuid)
                if "carbon_coefficient" in ncs_dict:
                    continue
                else:
                    ncs_dict["carbon_coefficient"] = carbon_coefficient
                    source_ncs = create_ncs_pathway(ncs_dict)
                    if source_ncs is None:
                        continue
                    ncs = copy_layer_component_attributes(ncs, source_ncs)
                    settings_manager.update_ncs_pathway(ncs)
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
            else:
                pathways = imp_model.pathways
                # Update values
                imp_model_dict["priority_layers"] = imp_model.priority_layers
                source_im = create_implementation_model(imp_model_dict)
                if source_im is None:
                    continue
                imp_model = copy_layer_component_attributes(imp_model, source_im)
                imp_model.pathways = pathways
                settings_manager.remove_implementation_model(str(imp_model.uuid))
                settings_manager.save_implementation_model(imp_model)
        except KeyError as ke:
            log(f"Default implementation model configuration load error - {str(ke)}")
            continue


def initialize_report_settings():
    """Sets the default report settings on first time use
    of the plugin.
    """
    if settings_manager.get_value(Settings.REPORT_DISCLAIMER, None) is None:
        settings_manager.set_value(
            Settings.REPORT_DISCLAIMER, DEFAULT_REPORT_DISCLAIMER
        )

    if settings_manager.get_value(Settings.REPORT_LICENSE, None) is None:
        settings_manager.set_value(Settings.REPORT_LICENSE, DEFAULT_REPORT_LICENSE)

    if settings_manager.get_value(Settings.REPORT_CPLUS_LOGO, None) is None:
        settings_manager.set_value(Settings.REPORT_CPLUS_LOGO, CPLUS_LOGO_PATH)

    if settings_manager.get_value(Settings.REPORT_CI_LOGO, None) is None:
        settings_manager.set_value(Settings.REPORT_CI_LOGO, CI_LOGO_PATH)
