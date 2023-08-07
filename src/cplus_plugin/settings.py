# coding=utf-8

"""Plugin global settings.

Covers the plugin global settings which a user can set and save. The settings
will be saved using QgsSettings. Settings can be accessed via the QGIS options,
a button on the docking widget, and from the toolbar menu.
"""

import os
import typing
from pathlib import Path

import qgis.core
import qgis.gui
from qgis.gui import QgsOptionsPageWidget
from qgis.gui import QgsOptionsWidgetFactory
from qgis.PyQt import uic
from qgis.PyQt.QtGui import (
    QIcon,
    QShowEvent,
    QPixmap,
)
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QWidget

from .conf import (
    settings_manager,
    Settings,
)
from .definitions.defaults import (
    OPTIONS_TITLE,
    ICON_PATH,
    DEFAULT_LOGO_PATH,
)
from .utils import FileUtils

Ui_DlgSettings, _ = uic.loadUiType(str(Path(__file__).parent / "ui/qgis_settings.ui"))


class CplusSettings(Ui_DlgSettings, QgsOptionsPageWidget):
    message_bar: qgis.gui.QgsMessageBar

    """CPLUS plugin settings class.

    Class which manages the CPLUS settings. Initilizes the UI, which can be accessed
    from the menu drop-down or the QGIS settings.
    """

    def __init__(self, parent=None) -> None:
        """QGIS CPLUS Plugin Settings dialog."""
        QgsOptionsPageWidget.__init__(self, parent)

        self.setupUi(self)
        self.message_bar = qgis.gui.QgsMessageBar(self)
        self.layout().insertWidget(0, self.message_bar)

        self.settings = qgis.core.QgsSettings()
        settings_manager.settings_updated[str, object].connect(self.on_settings_changed)

        # Connections
        self.cb_custom_logo.stateChanged.connect(self.logo_state_changed)
        self.logo_file.fileChanged.connect(self.logo_file_changed)
        self.folder_data.fileChanged.connect(self.base_dir_exists)

    def apply(self) -> None:
        """This is called on OK click in the QGIS options panel."""

        self.save_settings()

    def on_settings_changed(self, name: str, value: typing.Any):
        """Slot raised when settings has been changed.

        :param name: Name of the setting that has changed.
        :type name: str

        :param value: New value for the given settings name.
        :type value: Any
        """
        # Create NCS pathway subdirectory if base directory has changed.
        if name == Settings.BASE_DIR.value:
            if not value:
                return

            FileUtils.create_ncs_pathways_dir(value)
            FileUtils.create_ncs_carbon_dir(value)
            FileUtils.create_pwls_dir(value)

    def update_logo(self, custom_logo, logo_dir=DEFAULT_LOGO_PATH):
        """Updates the logo preview.

        If the logo is not found, the default logo will be used.

        :param custom_logo: If a custom logo should be used
        :type custom_logo: bool

        :param logo_dir: The custom logo directory
        :type logo_dir: str
        """
        logo_found = False
        if custom_logo:
            # If custom logo is active, check if the provided directory exists
            logo_found = self.logo_file_exists()

        if custom_logo and logo_found:
            # If custom logo is enabled and the logo file exists
            pixmap = QPixmap(logo_dir)
        else:
            # If custom logo is disabled. The default logo will also be used when the custom logo does not exist
            pixmap = QPixmap(DEFAULT_LOGO_PATH)
        self.lbl_logo_image.setPixmap(pixmap)

    def logo_state_changed(self) -> None:
        """Called when the custom logo option is disabled or enabled.
        Will update the logo preview.
        """
        custom_logo = self.cb_custom_logo.checkState()
        custom_logo_path = self.logo_file.filePath()

        # Enables/disables the file widget for the logo directory
        if custom_logo:
            self.logo_file.setEnabled(True)
        else:
            self.logo_file.setEnabled(False)

        self.update_logo(custom_logo, custom_logo_path)

    def logo_file_changed(self):
        """Called when the logo file directory changes.
        Will update the logo preview.
        """
        custom_logo = self.cb_custom_logo.checkState()
        custom_logo_path = self.logo_file.filePath()

        self.update_logo(custom_logo, custom_logo_path)

    def logo_file_exists(self) -> bool:
        """Checks if the provided logo directory exists.
        A warning messages is presented if the file cannot be found.

        :returns: Whether the logo file exists
        :rtype: bool
        """
        # Clears the error messages when doing next check
        self.message_bar.clearWidgets()

        file_found = False
        custom_logo_path = self.logo_file.filePath()
        if not os.path.exists(custom_logo_path):
            # File not found
            self.message_bar.pushWarning(
                "CPLUS - Custom logo not found: ", custom_logo_path
            )
        else:
            file_found = True

        # File found
        return file_found

    def base_dir_exists(self) -> bool:
        """Checks if the provided base directory exists.
        A warning messages is presented if the directory does not exist.

        :returns: Whether the base directory exists
        :rtype: bool
        """

        # Clears the error messages when doing next check
        self.message_bar.clearWidgets()

        folder_found = False
        base_dir_path = self.folder_data.filePath()
        if not os.path.exists(base_dir_path):
            # File not found
            self.message_bar.pushWarning(
                "CPLUS - Base directory not found: ", base_dir_path
            )
        else:
            folder_found = True

        return folder_found

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
        if custom_logo:
            custom_logo_path = self.logo_file.filePath()
            settings_manager.set_value(Settings.REPORT_LOGO_DIR, custom_logo_path)

            if not os.path.exists(custom_logo_path):
                # File not found, disable custom logo
                settings_manager.set_value(Settings.REPORT_CUSTOM_LOGO, False)

                iface.messageBar().pushWarning(
                    "CPLUS - Custom logo not found, disabled: ", custom_logo_path
                )

        footer = self.txt_footer.toPlainText()
        settings_manager.set_value(Settings.REPORT_FOOTER, footer)

        disclaimer = self.txt_disclaimer.toPlainText()
        settings_manager.set_value(Settings.REPORT_DISCLAIMER, disclaimer)

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
        organization = settings_manager.get_value(
            Settings.REPORT_ORGANIZATION, default=""
        )
        self.txt_organization.setText(organization)

        email = settings_manager.get_value(Settings.REPORT_CONTACT_EMAIL, default="")
        self.txt_email.setText(email)

        website = settings_manager.get_value(Settings.REPORT_WEBSITE, default="")
        self.txt_website.setText(website)

        custom_logo = int(
            settings_manager.get_value(
                Settings.REPORT_CUSTOM_LOGO,
                default=True,
            )
        )
        self.cb_custom_logo.setCheckState(custom_logo)
        self.logo_file.setEnabled(custom_logo)

        custom_logo_dir = settings_manager.get_value(
            Settings.REPORT_LOGO_DIR, default=DEFAULT_LOGO_PATH
        )
        self.logo_file.setFilePath(custom_logo_dir)
        self.update_logo(custom_logo, custom_logo_dir)

        footer = settings_manager.get_value(Settings.REPORT_FOOTER, default="")
        self.txt_footer.setPlainText(footer)

        disclaimer = settings_manager.get_value(Settings.REPORT_DISCLAIMER, default="")
        self.txt_disclaimer.setPlainText(disclaimer)

        report_license = settings_manager.get_value(Settings.REPORT_LICENSE, default="")
        self.txt_license.setText(report_license)

        # Advanced settings
        base_dir = settings_manager.get_value(Settings.BASE_DIR, default="")
        self.folder_data.setFilePath(base_dir)
        self.base_dir_exists()

    def showEvent(self, event: QShowEvent) -> None:
        """Show event being called. This will display the plugin settings.
        The stored/saved settings will be loaded.

        :param event: Event that has been triggered
        :type event: QShowEvent
        """

        super().showEvent(event)
        self.load_settings()

    def closeEvent(self, event: QShowEvent) -> None:
        """When closing the setings.

        :param event: Event that has been triggered
        :type event: QShowEvent
        """

        super().closeEvent(event)


class CplusOptionsFactory(QgsOptionsWidgetFactory):
    """Options factory initializes the CPLUS settings.

    Class which creates the widget requied for the CPLUS settings.
    QgsOptionsWidgetFactory is used to accomplish this.
    """

    def __init__(self) -> None:
        """QGIS CPLUS Plugin Settings factory."""
        super().__init__()

        self.setTitle(OPTIONS_TITLE)

    def icon(self) -> QIcon:
        """Returns the icon which will be used for the CPLUS options tab.

        :returns: An icon object which contains the provided custom icon
        :rtype: QIcon
        """

        return QIcon(ICON_PATH)

    def createWidget(self, parent: QWidget) -> CplusSettings:
        """Creates a widget for CPLUS settings.

        :param parent: Parent widget
        :type parent: QWidget

        :returns: Widget to be used in the QGIS options
        :rtype: CplusSettings
        """

        return CplusSettings(parent)
