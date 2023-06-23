import os
from pathlib import Path

import qgis.core
import qgis.gui
from qgis.gui import QgsOptionsPageWidget
from qgis.gui import QgsOptionsWidgetFactory
from qgis.PyQt import uic
from qgis.PyQt.QtGui import (
    QIcon,
    QShowEvent,
)
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QWidget

from .conf import (
    settings_manager,
    Settings,
)
from .definitions.defaults import OPTIONS_TITLE, ICON_PATH

Ui_DlgSettings, _ = uic.loadUiType(str(Path(__file__).parent / "ui/qgis_settings.ui"))


class CplusSettings(Ui_DlgSettings, QgsOptionsPageWidget):
    message_bar: qgis.gui.QgsMessageBar

    def __init__(self, parent=None) -> None:
        QgsOptionsPageWidget.__init__(self, parent)

        self.setupUi(self)
        self.message_bar = qgis.gui.QgsMessageBar(self)
        self.layout().insertWidget(0, self.message_bar)

        self.settings = qgis.core.QgsSettings()

        # Connections
        self.cb_custom_logo.stateChanged.connect(self.logo_state_change)
        self.logo_file.fileChanged.connect(self.logo_file_exists)
        self.folder_data.fileChanged.connect(self.base_dir_exists)

    def apply(self) -> None:
        """This is called on OK click in the QGIS options panel.
        """

        self.save_settings()

    def logo_state_change(self) -> None:
        """Called when the custom logo option is disabled or enabled.
        """

        custom_logo = self.cb_custom_logo.checkState()

        # Enables/disables the file widget for the logo directory
        if custom_logo > 0:
            self.logo_file.setEnabled(True)
            self.logo_file_exists()
        else:
            self.logo_file.setEnabled(False)

    def logo_file_exists(self) -> None:
        """Checks if the provided logo directory exists.
        A warning messages is presented if the file cannot be found.
        """

        # Check is skipped if custom logo is disabled
        if not self.cb_custom_logo.checkState():
            return

        # Clears the error messages when doing next check
        self.message_bar.clearWidgets()

        custom_logo_path = self.logo_file.filePath()
        if not os.path.exists(custom_logo_path):
            # File not found
            self.message_bar.pushWarning(
                "CPLUS - Custom logo not found: ", custom_logo_path
            )

    def base_dir_exists(self) -> None:
        """Checks if the provided base directory exists.
        A warning messages is presented if the directory does not exist.
        """

        # Clears the error messages when doing next check
        self.message_bar.clearWidgets()

        base_dir_path = self.folder_data.filePath()
        if not os.path.exists(base_dir_path):
            # File not found
            self.message_bar.pushWarning(
                "CPLUS - Base directory not found: ", base_dir_path
            )

    def save_settings(self) -> None:
        """Saves the settings.
        Also does error checking for settings (e.g if the custom logo exists).
        Will present the user with an error message if an issue is found.
        """

        # Analysis configuration

        # Report settings
        organization = self.txt_organization.text()
        settings_manager.set_value(Settings.REPORT_ORGANIZATION, organization)

        email = self.txt_email.text()
        settings_manager.set_value(Settings.REPORT_CONTACT_EMAIL, email)

        website = self.txt_website.text()
        settings_manager.set_value(Settings.REPORT_WEBSITE, website)

        custom_logo = self.cb_custom_logo.checkState()
        settings_manager.set_value(Settings.REPORT_CUSTOM_LOGO, custom_logo)

        # Checks if the logo file exists if custom logo is enabled
        if custom_logo > 0:
            custom_logo_path = self.logo_file.filePath()
            settings_manager.set_value(Settings.REPORT_LOGO_DIR, custom_logo_path)

            if not os.path.exists(custom_logo_path):
                # File not found, disable custom logo
                settings_manager.set_value(Settings.REPORT_CUSTOM_LOGO, 0)

                iface.messageBar().pushWarning(
                    "CPLUS - Custom logo not found, disabled: ", custom_logo_path
                )

        footer = self.txt_footer.toPlainText()
        settings_manager.set_value(Settings.REPORT_FOOTER, footer)

        disclaimer = self.txt_disclaimer.toPlainText()
        settings_manager.set_value(Settings.REPORT_DISLAIMER, disclaimer)

        report_license = self.txt_license.text()
        settings_manager.set_value(Settings.REPORT_LICENSE, report_license)

        # Advanced settings
        base_dir_path = self.folder_data.filePath()
        settings_manager.set_value(Settings.BASE_DIR, base_dir_path)

        # Checks if the provided base directory exists
        if not os.path.exists(base_dir_path):
            iface.messageBar().pushCritical(
                "CPLUS - Base directory not found: ", base_dir_path
            )

    def load_settings(self) -> None:
        """Loads the settings and displays it in the options UI"""

        # Analysis configuration settings

        # Report settings
        organization = settings_manager.get_value(Settings.REPORT_ORGANIZATION)
        self.txt_organization.setText(organization)

        email = settings_manager.get_value(Settings.REPORT_CONTACT_EMAIL)
        self.txt_email.setText(email)

        website = settings_manager.get_value(Settings.REPORT_WEBSITE)
        self.txt_website.setText(website)

        custom_logo = int(settings_manager.get_value(Settings.REPORT_CUSTOM_LOGO))
        self.cb_custom_logo.setCheckState(custom_logo)

        # Disables/enables the logo file widget
        if custom_logo > 0:
            self.logo_file.setEnabled(True)
        else:
            self.logo_file.setEnabled(False)

        custom_logo_dir = settings_manager.get_value(Settings.REPORT_LOGO_DIR)
        self.logo_file.setFilePath(custom_logo_dir)
        self.logo_file_exists()

        footer = settings_manager.get_value(Settings.REPORT_FOOTER)
        self.txt_footer.setPlainText(footer)

        disclaimer = settings_manager.get_value(Settings.REPORT_DISLAIMER)
        self.txt_disclaimer.setPlainText(disclaimer)

        report_license = settings_manager.get_value(Settings.REPORT_LICENSE)
        self.txt_license.setText(report_license)

        # Advanced settings
        base_dir = settings_manager.get_value(Settings.BASE_DIR)
        self.folder_data.setFilePath(base_dir)
        self.base_dir_exists()

    def showEvent(self, event: QShowEvent) -> None:
        """Show event being called. This will display the plugin settings.
        The stored/saved settings will be loaded.

        Args:
            event (QShowEvent): Event that has been triggered
        """

        super().showEvent(event)
        self.load_settings()

    def closeEvent(self, event: QShowEvent) -> None:
        """When closing the setings.

        Args:
            event (QShowEvent): Event that has been triggered
        """

        super().closeEvent(event)


class CplusOptionsFactory(QgsOptionsWidgetFactory):
    def __init__(self) -> None:
        super().__init__()

        self.setTitle(OPTIONS_TITLE)

    def icon(self) -> QIcon:
        """Returns the icon which will be used for the CPLUS options tab.

        Returns:
            Icon (QIcon): An icon object which contains the provided custom icon
        """

        return QIcon(ICON_PATH)

    def createWidget(self, parent: QWidget) -> CplusSettings:
        """Creates a widget for CPLUS settings.

        Args:
            parent (QWidget): Parent widget (e.g. dockwidget)

        Returns:
            SettingsWidget (CplusSettings): Widget to be used in the QGIS options
        """

        return CplusSettings(parent)
