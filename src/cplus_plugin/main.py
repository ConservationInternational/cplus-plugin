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

from .api.base import ApiRequestStatus
from .conf import Settings, settings_manager
from .definitions.defaults import (
    ABOUT_DOCUMENTATION_SITE,
    CI_LOGO_PATH,
    CPLUS_LOGO_PATH,
    DEFAULT_REPORT_DISCLAIMER,
    DEFAULT_REPORT_LICENSE,
    DOCUMENTATION_SITE,
    ICON_PATH,
    IRRECOVERABLE_CARBON_API_URL,
    OPTIONS_TITLE,
    PRIORITY_GROUPS,
    PRIORITY_LAYERS,
    BASE_API_URL,
    REPORT_FONT_NAME,
)
from .gui.map_repeat_item_widget import CplusMapLayoutItemGuiMetadata
from .lib.reports.layout_items import CplusMapRepeatItemLayoutItemMetadata
from .lib.reports.manager import report_manager
from .lib.reports.metrics import register_metric_functions, unregister_metric_functions
from .models.base import PriorityLayerType
from .models.report import MetricConfigurationProfile, MetricProfileCollection
from .gui.settings.cplus_options import CplusOptionsFactory
from .gui.settings.log_options import LogOptionsFactory
from .gui.settings.report_options import ReportOptionsFactory

from .utils import (
    FileUtils,
    contains_font_family,
    install_font,
    log,
    open_documentation,
    get_plugin_version,
    tr,
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

        create_priority_layers()

        clean_up_finance_pwl_references()

        initialize_model_settings()

        # Initialize default report settings
        initialize_report_settings()

        initialize_api_url()

        # Upgrade metric configuration to profile collection
        upgrade_metric_configuration_to_profile_collection()

        self.main_widget = QgisCplusMain(
            iface=self.iface, parent=self.iface.mainWindow()
        )
        self.main_widget.visibilityChanged.connect(
            self.on_dock_widget_visibility_changed
        )

        # Create options factories
        self.cplus_options_factory = CplusOptionsFactory(main_widget=self.main_widget)
        self.reports_options_factory = ReportOptionsFactory()
        self.log_options_factory = LogOptionsFactory()

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

        # Register custom layout items
        self.register_layout_items()

        # Register custom report variables when a layout is opened
        self.iface.layoutDesignerOpened.connect(self.on_layout_designer_opened)

        # Install report font
        self.install_report_font()

        # Register metric functions. Note that these are
        # scoped for specific contexts.
        register_metric_functions()

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

            # Unregister metric functions
            unregister_metric_functions()

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

    def install_report_font(self):
        """Checks if the report font exists and install it."""
        font_exists = contains_font_family(REPORT_FONT_NAME)
        if not font_exists:
            log(message=self.tr("Installing report font..."))
            status = install_font(REPORT_FONT_NAME.lower())
            if status:
                log(message=self.tr("Report font successfully installed."))
            else:
                log(message=self.tr("Report font could not be installed."), info=False)
        else:
            log(message="Report font exists.")


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


def clean_up_finance_pwl_references():
    """Check if NPV PWLs are valid i.e. refer to existing NCS pathways.

    This also cleans up those finance PWLs that were previously referring
    to activities.
    """
    ncs_pathway_pwl_ids = list(
        {
            pwl.get("uuid")
            for pathway in settings_manager.get_all_ncs_pathways()
            for pwl in pathway.priority_layers
            if pwl.get("uuid") is not None
        }
    )

    for layer in settings_manager.get_priority_layers():
        # Remove finance priority layers that were previously pointing
        # to activities or also for NCS pathways that have been removed.
        pwl_type = layer.get("type", PriorityLayerType.DEFAULT.value)
        if pwl_type != PriorityLayerType.NPV:
            continue

        if layer["uuid"] not in ncs_pathway_pwl_ids:
            settings_manager.delete_priority_layer(layer["uuid"])


def upgrade_metric_configuration_to_profile_collection():
    """Due to changes introduced in v1.17dev, where metrics are
    now managed in a collection of profiles, this function will
    attempt to automatically update the previous single metric
    configuration to a 'Default' metric configuration profile.
    """
    metric_profile_collection = settings_manager.get_metric_profile_collection()
    # We assume that since the collection is None then it was
    # from an older version of managing metric configuration however
    # if not None then no need to upgrade since its assumed
    # that this was already automatically done before.
    if metric_profile_collection:
        log("Metric profile collection is upto date")
        return

    metric_configuration = settings_manager.get_metric_configuration()
    if metric_configuration is None:
        log(
            "Metric configuration not found, skipping "
            "upgrade to a default metric configuration profile"
        )
        return

    # Group previous metric configuration as "Default"
    default_profile_name = tr("Default")
    default_metric_config_profile = MetricConfigurationProfile(
        default_profile_name, metric_configuration
    )
    upgraded_profile_collection = MetricProfileCollection(
        default_profile_name, [default_metric_config_profile]
    )
    settings_manager.save_metric_profile_collection(upgraded_profile_collection)
    log(
        "Successfully upgraded the metric configuration settings "
        "to be the default metric configuration profile"
    )


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

    settings_manager.set_value(activity_ncs_setting, True)


def initialize_api_url():
    """Sets the default api url for the plugin"""
    if not settings_manager.get_value(Settings.DEBUG, False, bool):
        settings_manager.set_value(Settings.DEBUG, False)
    if not settings_manager.get_value(Settings.BASE_API_URL, None, str):
        settings_manager.set_value(Settings.BASE_API_URL, BASE_API_URL)

    # Default URL for irrecoverable carbon dataset
    if not settings_manager.get_value(
        Settings.IRRECOVERABLE_CARBON_ONLINE_SOURCE, None, str
    ):
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_SOURCE, IRRECOVERABLE_CARBON_API_URL
        )

    # Default status of downloading irrecoverable carbon dataset
    if not settings_manager.get_value(
        Settings.IRRECOVERABLE_CARBON_ONLINE_DOWNLOAD_STATUS, None, int
    ):
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_DOWNLOAD_STATUS,
            ApiRequestStatus.NOT_STARTED.value,
        )

    # Default description of irrecoverable carbon dataset download status
    if not settings_manager.get_value(
        Settings.IRRECOVERABLE_CARBON_ONLINE_STATUS_DESCRIPTION, None, str
    ):
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_STATUS_DESCRIPTION,
            tr("Download not started"),
        )


def initialize_report_settings():
    """Sets the default report settings on first time use
    of the plugin.
    """
    plugin_version = get_plugin_version()
    log(f"Initializing report settings for version: {get_plugin_version()}")

    # Check if default report settings have already been set
    report_setting = f"default_report_settings_set_{plugin_version}"

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
