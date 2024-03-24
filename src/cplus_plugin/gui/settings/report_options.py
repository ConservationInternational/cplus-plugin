# coding=utf-8

"""Plugin report settings."""

import os
import typing

from qgis.gui import QgsFileWidget, QgsMessageBar, QgsOptionsPageWidget
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
from ...definitions.defaults import (
    DEFAULT_LOGO_PATH,
    REPORT_OPTIONS_TITLE,
    REPORT_SETTINGS_ICON_PATH,
)
from ...utils import tr


Ui_ReportSettingsWidget, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/report_settings.ui")
)


class ReportSettingsWidget(QgsOptionsPageWidget, Ui_ReportSettingsWidget):
    """Report settings widget."""

    def __init__(self, parent=None):
        QgsOptionsPageWidget.__init__(self, parent)
        self.setupUi(self)

        self.message_bar = QgsMessageBar(self)
        self.layout.insertWidget(0, self.message_bar)

        # Connect signals
        self.cb_custom_logo.stateChanged.connect(self.logo_state_changed)
        self.logo_file.fileChanged.connect(self.logo_file_changed)

    def apply(self) -> None:
        """This is called on OK click in the QGIS options panel."""
        self.save_settings()

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

    def save_settings(self) -> None:
        """Saves the settings.
        Also does error checking for settings (e.g if the custom logo exists).
        Will present the user with an error message if an issue is found.
        """
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

        stakeholders = self.txt_stakeholders.text()
        settings_manager.set_value(Settings.REPORT_STAKEHOLDERS, stakeholders)

        policies = self.txt_culture_policies.text()
        settings_manager.set_value(Settings.REPORT_CULTURE_POLICIES, policies)

    def load_settings(self):
        """Loads the settings and displays it in the options UI."""
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

        stakeholders = settings_manager.get_value(
            Settings.REPORT_STAKEHOLDERS, default=""
        )
        self.txt_stakeholders.setText(stakeholders)

        policies = settings_manager.get_value(
            Settings.REPORT_CULTURE_POLICIES, default=""
        )
        self.txt_culture_policies.setText(policies)

    def showEvent(self, event: QShowEvent) -> None:
        """Show event being called. This will display the plugin settings.
        The stored/saved settings will be loaded.

        :param event: Event that has been triggered
        :type event: QShowEvent
        """
        super().showEvent(event)
        self.load_settings()

    def closeEvent(self, event: QShowEvent) -> None:
        """When closing the settings.

        :param event: Event that has been triggered
        :type event: QShowEvent
        """
        super().closeEvent(event)


class ReportOptionsFactory(QgsOptionsWidgetFactory):
    """Factory for defining CPLUS report settings."""

    def __init__(self) -> None:
        super().__init__()

        self.setTitle(tr(REPORT_OPTIONS_TITLE))
        self.setKey(REPORTS_OPTIONS_KEY)

    def icon(self) -> QIcon:
        """Returns the icon which will be used for the report settings item.

        :returns: An icon object which contains the provided custom icon
        :rtype: QIcon
        """
        return QIcon(REPORT_SETTINGS_ICON_PATH)

    def path(self) -> typing.List[str]:
        """
        Returns the path to place the widget page at.

        This instructs the registry to place the report options tab under the
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
