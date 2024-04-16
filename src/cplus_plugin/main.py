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

from qgis.core import (
    QgsApplication,
    QgsColorBrewerColorRamp,
    QgsMasterLayoutInterface,
    QgsSettings,
)
from qgis.gui import QgsGui, QgsLayoutDesignerInterface
from qgis.PyQt.QtCore import QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

# Initialize Qt resources from file resources.py
from .resources import *

from .gui.qgis_cplus_main import QgisCplusMain
from qgis.PyQt.QtWidgets import QToolButton
from qgis.PyQt.QtWidgets import QMenu

from .conf import Settings, settings_manager
from .definitions.constants import (
    CARBON_PATHS_ATTRIBUTE,
    COLOR_RAMP_PROPERTIES_ATTRIBUTE,
    COLOR_RAMP_TYPE_ATTRIBUTE,
    ACTIVITY_LAYER_STYLE_ATTRIBUTE,
    NCS_CARBON_SEGMENT,
    NCS_PATHWAY_SEGMENT,
    PATH_ATTRIBUTE,
    PIXEL_VALUE_ATTRIBUTE,
    STYLE_ATTRIBUTE,
    USER_DEFINED_ATTRIBUTE,
    UUID_ATTRIBUTE,
)
from .definitions.defaults import (
    ABOUT_DOCUMENTATION_SITE,
    CI_LOGO_PATH,
    CPLUS_LOGO_PATH,
    DEFAULT_ACTIVITIES,
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
from .gui.settings.cplus_options import CplusOptionsFactory
from .gui.settings.log_options import LogOptionsFactory
from .gui.settings.report_options import ReportOptionsFactory

from .utils import FileUtils, log, open_documentation, get_plugin_version


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

        self.cplus_action = None

        self.menu = QMenu("&CPLUS")
        self.menu.setIcon(QIcon(ICON_PATH))

        self.raster_menu = self.iface.rasterMenu()
        self.raster_menu.addMenu(self.menu)

        self.toolbar = self.iface.addToolBar("Open CPLUS")
        self.toolbar.setObjectName("CPLUS")
        self.toolButton = QToolButton()
        self.toolButton.setMenu(QMenu())
        self.toolButton.setCheckable(True)
        self.toolButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.toolBtnAction = self.toolbar.addWidget(self.toolButton)
        self.actions.append(self.toolBtnAction)

        # Create options factories
        self.cplus_options_factory = CplusOptionsFactory()
        self.reports_options_factory = ReportOptionsFactory()
        self.log_options_factory = LogOptionsFactory()

        create_priority_layers()

        initialize_model_settings()

        # Initialize default report settings
        initialize_report_settings()

        self.main_widget = QgisCplusMain(
            iface=self.iface, parent=self.iface.mainWindow()
        )
        self.main_widget.visibilityChanged.connect(
            self.on_dock_widget_visibility_changed
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

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Create main dock widget action
        self.create_dock_widget_action()

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

        # Register plugin options factories
        self.iface.registerOptionsWidgetFactory(self.cplus_options_factory)
        self.iface.registerOptionsWidgetFactory(self.reports_options_factory)
        self.iface.registerOptionsWidgetFactory(self.log_options_factory)

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

            # Unregister plugin options factories
            self.iface.unregisterOptionsWidgetFactory(self.cplus_options_factory)
            self.iface.unregisterOptionsWidgetFactory(self.reports_options_factory)
            self.iface.unregisterOptionsWidgetFactory(self.log_options_factory)

        except Exception as e:
            log(str(e), info=False)

    def run(self):
        """Creates the main widget for the plugin."""
        if self.main_widget is None:
            self.main_widget = QgisCplusMain(
                iface=self.iface, parent=self.iface.mainWindow()
            )
            self.create_dock_widget_action()

        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.main_widget)
        self.main_widget.show()

        if not self.pluginIsActive:
            self.pluginIsActive = True

    def create_dock_widget_action(self):
        """Create the action corresponding to the main dock widget."""
        self.cplus_action = self.main_widget.toggleViewAction()
        self.cplus_action.setIcon(QIcon(ICON_PATH))
        self.cplus_action.setText(self.tr("CPLUS"))
        self.menu.addAction(self.cplus_action)
        self.toolButton.menu().addAction(self.cplus_action)
        self.toolButton.setDefaultAction(self.cplus_action)

        self.actions.append(self.cplus_action)

    def on_dock_widget_visibility_changed(self, visible: bool):
        """Slot raised when the visibility of the main docket widget changes.

        :param visible: True if the dock widget is visible, else False.
        :type visible: bool
        """
        # Set default dock position on first time load.
        if visible:
            app_window = self.iface.mainWindow()
            dock_area = app_window.dockWidgetArea(self.main_widget)
            if dock_area == Qt.NoDockWidgetArea and not self.main_widget.isFloating():
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.main_widget)
                self.main_widget.show()

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

    priority_layers_setting = f"default_priority_layers_set_{get_plugin_version()}"

    log(f"Priority weighting layers plugin setting - {priority_layers_setting}")

    if not settings_manager.get_value(
        priority_layers_setting, default=False, setting_type=bool
    ):
        log(f"Initializing priority layers and groups")
        found_settings = settings_manager.find_settings("default_priority_layers_set")

        # Remove old settings as they will not be of use anymore.
        for previous_setting in found_settings:
            settings_manager.remove(previous_setting)

        groups = []
        for group in PRIORITY_GROUPS:
            group["value"] = 0
            settings_manager.save_priority_group(group)
        new_uuids = []
        for layer in PRIORITY_LAYERS:
            layer["groups"] = groups
            layer["user_defined"] = False
            new_uuids.append(layer["uuid"])

            plugin_priority_layer = settings_manager.get_priority_layer(layer["uuid"])

            if plugin_priority_layer is not None:
                plugin_priority_layer["name"] = layer["name"]
                plugin_priority_layer["description"] = layer["description"]
                plugin_priority_layer["path"] = layer["path"]
                settings_manager.save_priority_layer(plugin_priority_layer)
            else:
                settings_manager.save_priority_layer(layer)

        for layer in settings_manager.get_priority_layers():
            if layer["uuid"] not in new_uuids:
                settings_manager.delete_priority_layer(layer["uuid"])

        settings_manager.set_value(priority_layers_setting, True)


def initialize_model_settings():
    """Initialize default model components such as NCS pathways
    and activities.

    It will check if there are existing components using the UUID
    and only add the ones that do not exist in the settings.

    This is normally called during plugin startup.
    """

    # Check if default NCS pathways and activities have been loaded
    activity_ncs_setting = f"default_ncs_activity_models_set_{get_plugin_version()}"

    log(f"Activities and NCS pathway plugin setting - {activity_ncs_setting}")

    if settings_manager.get_value(
        activity_ncs_setting, default=False, setting_type=bool
    ):
        return

    found_settings = settings_manager.find_settings("default_ncs_activity_models_set")

    # Remove old settings as they will not be of use anymore.
    for previous_setting in found_settings:
        settings_manager.remove(previous_setting)

    # Create NCS subdirectories if BASE_DIR has been defined
    base_dir = settings_manager.get_value(Settings.BASE_DIR)
    if base_dir:
        # Create NCS pathways subdirectory
        FileUtils.create_ncs_pathways_dir(base_dir)

        # Create NCS carbon subdirectory
        FileUtils.create_ncs_carbon_dir(base_dir)

        # Create priority weighting layers subdirectory
        FileUtils.create_pwls_dir(base_dir)

    new_pathways_uuid = []

    # Add default pathways
    for ncs_dict in DEFAULT_NCS_PATHWAYS:
        try:
            ncs_uuid = ncs_dict[UUID_ATTRIBUTE]
            ncs = settings_manager.get_ncs_pathway(ncs_uuid)

            new_pathways_uuid.append(ncs_uuid)

            if ncs is None:
                # Update dir
                base_dir = settings_manager.get_value(Settings.BASE_DIR, None)
                if base_dir is not None:
                    # Pathway location
                    file_name = ncs_dict[PATH_ATTRIBUTE]
                    absolute_path = f"{base_dir}/{NCS_PATHWAY_SEGMENT}/{file_name}"
                    abs_path = str(os.path.normpath(absolute_path))
                    ncs_dict[PATH_ATTRIBUTE] = abs_path

                    # Carbon location
                    carbon_file_names = ncs_dict[CARBON_PATHS_ATTRIBUTE]
                    abs_carbon_paths = []
                    for carbon_file_name in carbon_file_names:
                        abs_carbon_path = (
                            f"{base_dir}/{NCS_CARBON_SEGMENT}/{carbon_file_name}"
                        )
                        norm_carbon_path = str(os.path.normpath(abs_carbon_path))
                        abs_carbon_paths.append(norm_carbon_path)
                    ncs_dict[CARBON_PATHS_ATTRIBUTE] = abs_carbon_paths

                ncs_dict[USER_DEFINED_ATTRIBUTE] = False
                settings_manager.save_ncs_pathway(ncs_dict)
        except KeyError as ke:
            log(f"Default NCS configuration load error - {str(ke)}")
            continue

    # Preset color brewer scheme names
    preset_scheme_names = QgsColorBrewerColorRamp.listSchemeNames()

    for ncs in settings_manager.get_all_ncs_pathways():
        if str(ncs.uuid) not in new_pathways_uuid:
            settings_manager.remove_ncs_pathway(str(ncs.uuid))

    new_activities_uuids = []
    # Add default activities
    for i, activity_dict in enumerate(DEFAULT_ACTIVITIES, start=1):
        try:
            activity_uuid = activity_dict[UUID_ATTRIBUTE]
            activity = settings_manager.get_activity(activity_uuid)
            new_activities_uuids.append(activity_uuid)
            if activity is None:
                if STYLE_ATTRIBUTE in activity_dict:
                    style_info = activity_dict[STYLE_ATTRIBUTE]
                    if ACTIVITY_LAYER_STYLE_ATTRIBUTE in style_info:
                        activity_layer_style = style_info[
                            ACTIVITY_LAYER_STYLE_ATTRIBUTE
                        ]
                        if COLOR_RAMP_PROPERTIES_ATTRIBUTE in activity_layer_style:
                            # Must be a preset color brewer scheme name
                            scheme_name = activity_layer_style[
                                COLOR_RAMP_PROPERTIES_ATTRIBUTE
                            ]
                            if scheme_name in preset_scheme_names:
                                color_ramp = QgsColorBrewerColorRamp(scheme_name, 8)
                                color_ramp_properties = color_ramp.properties()
                                # Save the color ramp properties instead of just the
                                # scheme name
                                activity_dict[STYLE_ATTRIBUTE][
                                    ACTIVITY_LAYER_STYLE_ATTRIBUTE
                                ][
                                    COLOR_RAMP_PROPERTIES_ATTRIBUTE
                                ] = color_ramp_properties
                                activity_dict[STYLE_ATTRIBUTE][
                                    ACTIVITY_LAYER_STYLE_ATTRIBUTE
                                ][
                                    COLOR_RAMP_TYPE_ATTRIBUTE
                                ] = QgsColorBrewerColorRamp.typeString()

                activity_dict[PIXEL_VALUE_ATTRIBUTE] = i
                activity_dict[USER_DEFINED_ATTRIBUTE] = False
                settings_manager.save_activity(activity_dict)
        except KeyError as ke:
            log(f"Default activity configuration load error - {str(ke)}")
            continue

    for activity in settings_manager.get_all_activities():
        if str(activity.uuid) not in new_activities_uuids:
            settings_manager.activities(str(activity.uuid))

    settings_manager.set_value(activity_ncs_setting, True)


def initialize_report_settings():
    """Sets the default report settings on first time use
    of the plugin.
    """

    log(f"Initializing report settings")

    # Check if default report settings have already been set
    report_setting = f"default_report_settings_set_{get_plugin_version()}"

    if settings_manager.get_value(report_setting, default=False, setting_type=bool):
        return

    found_settings = settings_manager.find_settings("default_report_settings_set")

    # Remove old settings as they will not be of use anymore.
    for previous_setting in found_settings:
        settings_manager.remove(previous_setting)

    settings_manager.set_value(Settings.REPORT_DISCLAIMER, DEFAULT_REPORT_DISCLAIMER)

    settings_manager.set_value(Settings.REPORT_LICENSE, DEFAULT_REPORT_LICENSE)

    settings_manager.set_value(Settings.REPORT_CPLUS_LOGO, CPLUS_LOGO_PATH)
    settings_manager.set_value(Settings.REPORT_CI_LOGO, CI_LOGO_PATH)

    settings_manager.set_value(report_setting, True)
