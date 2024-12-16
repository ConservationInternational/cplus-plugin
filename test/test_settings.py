import unittest

from utilities_for_testing import get_qgis_app

from cplus_plugin.definitions.defaults import IRRECOVERABLE_CARBON_API_URL
from cplus_plugin.models.base import DataSourceType
from cplus_plugin.gui.settings.cplus_options import CplusSettings
from cplus_plugin.gui.settings.report_options import ReportSettingsWidget
from cplus_plugin.conf import (
    settings_manager,
    Settings,
)

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()
OPTIONS_TITLE = "CPLUS"


class CplusPluginSettingsTest(unittest.TestCase):
    def test_save(self):
        """A test which will check if the main CPLUS settings are saved correctly
        when the save_settings function is called.
        """
        settings_dialog = CplusSettings(PARENT)

        save_base_dir = "base directory"
        carbon_coefficient = 0.1
        pathway_suitability_index = 1.5

        irrecoverable_carbon_local_path = "reference_irrecoverable_carbon_local"
        irrecoverable_carbon_online_save_as_path = (
            "reference_irrecoverable_carbon_online_save"
        )

        # Sets the values in the GUI
        settings_dialog.folder_data.setFilePath(save_base_dir)

        settings_dialog.carbon_coefficient_box.setValue(carbon_coefficient)
        settings_dialog.suitability_index_box.setValue(pathway_suitability_index)

        settings_dialog.fw_irrecoverable_carbon.setFilePath(
            irrecoverable_carbon_local_path
        )
        settings_dialog.fw_save_online_file.setFilePath(
            irrecoverable_carbon_online_save_as_path
        )
        settings_dialog.txt_ic_url.setText(IRRECOVERABLE_CARBON_API_URL)
        settings_dialog.sw_irrecoverable_carbon.setCurrentIndex(0)

        # Saves the settings set in the GUI
        settings_dialog.save_settings()

        # Checks if the settings were correctly saved
        base_dir = settings_manager.get_value(Settings.BASE_DIR)
        self.assertEqual(save_base_dir, base_dir)

        carbon_coefficient_val = settings_manager.get_value(Settings.CARBON_COEFFICIENT)
        self.assertEqual(carbon_coefficient, carbon_coefficient_val)

        pathway_suitability_index_val = settings_manager.get_value(
            Settings.PATHWAY_SUITABILITY_INDEX
        )
        self.assertEqual(pathway_suitability_index, pathway_suitability_index_val)

        self.assertEqual(
            settings_manager.get_value(Settings.IRRECOVERABLE_CARBON_LOCAL_SOURCE),
            irrecoverable_carbon_local_path,
        )
        self.assertEqual(
            settings_manager.get_value(Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH),
            irrecoverable_carbon_online_save_as_path,
        )
        self.assertEqual(
            settings_manager.get_value(Settings.IRRECOVERABLE_CARBON_ONLINE_SOURCE),
            IRRECOVERABLE_CARBON_API_URL,
        )
        self.assertEqual(
            settings_manager.get_value(Settings.IRRECOVERABLE_CARBON_SOURCE_TYPE),
            DataSourceType.LOCAL.value,
        )

    def test_load(self):
        """A test which will check if the main CPLUS settings are loaded correctly
        into the settings UI when calling the load_settings function.
        """
        settings_dialog = CplusSettings(PARENT)

        save_base_dir = "base directory 2"
        save_carbon_coefficient = 0.1
        save_pathway_suitability_index = 1.5

        irrecoverable_carbon_local_path = "reference_irrecoverable_carbon_local"
        irrecoverable_carbon_online_save_as_path = (
            "reference_irrecoverable_carbon_online_save"
        )

        # Set all values for testing
        settings_manager.set_value(Settings.BASE_DIR, save_base_dir)

        settings_manager.set_value(Settings.CARBON_COEFFICIENT, save_carbon_coefficient)
        settings_manager.set_value(
            Settings.PATHWAY_SUITABILITY_INDEX, save_pathway_suitability_index
        )

        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_LOCAL_SOURCE, irrecoverable_carbon_local_path
        ),
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH,
            irrecoverable_carbon_online_save_as_path,
        )
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_SOURCE, IRRECOVERABLE_CARBON_API_URL
        )
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_SOURCE_TYPE, DataSourceType.LOCAL.value
        )

        # Loads the values into the GUI
        settings_dialog.load_settings()

        # Tests if the values were loaded correctly
        base_dir_path = settings_dialog.folder_data.filePath()
        self.assertEqual(save_base_dir, base_dir_path)

        carbon_coefficient = settings_dialog.carbon_coefficient_box.value()
        self.assertEqual(save_carbon_coefficient, carbon_coefficient)

        pathway_suitability_index = settings_dialog.suitability_index_box.value()
        self.assertEqual(save_pathway_suitability_index, pathway_suitability_index)

        self.assertEqual(
            settings_dialog.fw_irrecoverable_carbon.filePath(),
            irrecoverable_carbon_local_path,
        )
        self.assertEqual(
            settings_dialog.txt_ic_url.text(), IRRECOVERABLE_CARBON_API_URL
        )
        self.assertEqual(
            settings_dialog.fw_save_online_file.filePath(),
            irrecoverable_carbon_online_save_as_path,
        )
        self.assertTrue(settings_dialog.rb_local.isChecked())

    def test_base_dir_exist(self):
        """A test which checks if the base_dir_exists function works
        as it should. A test is done for when the base directory exist,
        and when the directory does not exist.
        """
        settings_dialog = CplusSettings(PARENT)

        dir_exist = "icons/"
        dir_does_not_exist = "not_exist"

        settings_dialog.folder_data.setFilePath(dir_exist)
        file_exist = settings_dialog.base_dir_exists()
        self.assertEqual(True, file_exist)

        settings_dialog.folder_data.setFilePath(dir_does_not_exist)
        file_exist = settings_dialog.base_dir_exists()
        self.assertEqual(False, file_exist)


class ReportSettingsTest(unittest.TestCase):
    def test_save(self):
        """A test which will check if report settings are saved correctly
        when the save_settings function is called.
        """
        report_settings_widget = ReportSettingsWidget(PARENT)

        save_organization = "a company"
        save_email = "an email"
        save_website = "a website"
        save_custom_logo_enabled = True
        save_custom_logo_dir = "icons/ci_logo.png"
        save_footer = "a footer"
        save_disclaimer = "a disclaimer"
        save_report_license = "license"
        save_stakeholders = "academia, cso"
        save_culture_policies = "customary land laws"
        save_culture_considerations = "pastoralist community"

        # Sets the values in the GUI
        report_settings_widget.txt_organization.setText(save_organization)
        report_settings_widget.txt_email.setText(save_email)
        report_settings_widget.txt_website.setText(save_website)
        report_settings_widget.cb_custom_logo.setCheckState(save_custom_logo_enabled)
        report_settings_widget.logo_file.setFilePath(save_custom_logo_dir)
        report_settings_widget.txt_footer.setPlainText(save_footer)
        report_settings_widget.txt_disclaimer.setPlainText(save_disclaimer)
        report_settings_widget.txt_license.setText(save_report_license)
        report_settings_widget.txt_stakeholders.setPlainText(save_stakeholders)
        report_settings_widget.txt_policies.setPlainText(save_culture_policies)
        report_settings_widget.txt_cultural_considerations.setPlainText(
            save_culture_considerations
        )

        # Saves the settings set in the GUI
        report_settings_widget.save_settings()

        # Checks if the settings were correctly saved
        organization = settings_manager.get_value(Settings.REPORT_ORGANIZATION)
        self.assertEqual(save_organization, organization)

        email = settings_manager.get_value(Settings.REPORT_CONTACT_EMAIL)
        self.assertEqual(save_email, email)

        website = settings_manager.get_value(Settings.REPORT_WEBSITE)
        self.assertEqual(save_website, website)

        custom_logo = settings_manager.get_value(Settings.REPORT_CUSTOM_LOGO)
        self.assertEqual(save_custom_logo_enabled, custom_logo)

        custom_logo_dir = settings_manager.get_value(Settings.REPORT_LOGO_DIR)
        self.assertEqual(save_custom_logo_dir, custom_logo_dir)

        footer = settings_manager.get_value(Settings.REPORT_FOOTER)
        self.assertEqual(save_footer, footer)

        disclaimer = settings_manager.get_value(Settings.REPORT_DISCLAIMER)
        self.assertEqual(save_disclaimer, disclaimer)

        report_license = settings_manager.get_value(Settings.REPORT_LICENSE)
        self.assertEqual(save_report_license, report_license)

        stakeholders = settings_manager.get_value(Settings.REPORT_STAKEHOLDERS)
        self.assertEqual(save_stakeholders, stakeholders)

        culture_considerations = settings_manager.get_value(
            Settings.REPORT_CULTURE_CONSIDERATIONS
        )
        self.assertEqual(save_culture_considerations, culture_considerations)

        culture_policies = settings_manager.get_value(Settings.REPORT_CULTURE_POLICIES)
        self.assertEqual(save_culture_policies, culture_policies)

    def test_load(self):
        """A test which will check if the report settings are loaded correctly
        into the settings UI when calling the load_settings function.
        """
        report_settings_widget = ReportSettingsWidget(PARENT)

        save_organization = "a company 2"
        save_email = "an email 2"
        save_website = "a website 2"
        save_custom_logo_enabled = False
        save_custom_logo_dir = "icons/ci_logo.png"
        save_footer = "a footer 2"
        save_disclaimer = "a disclaimer 2"
        save_report_license = "license 2"
        save_stakeholders = "academia, cso 2"
        save_culture_policies = "customary land laws"
        save_culture_considerations = "pastoralist community"

        # Set values for testing
        settings_manager.set_value(Settings.REPORT_ORGANIZATION, save_organization)
        settings_manager.set_value(Settings.REPORT_CONTACT_EMAIL, save_email)
        settings_manager.set_value(Settings.REPORT_WEBSITE, save_website)
        settings_manager.set_value(
            Settings.REPORT_CUSTOM_LOGO, save_custom_logo_enabled
        )
        settings_manager.set_value(Settings.REPORT_LOGO_DIR, save_custom_logo_dir)
        settings_manager.set_value(Settings.REPORT_FOOTER, save_footer)
        settings_manager.set_value(Settings.REPORT_DISCLAIMER, save_disclaimer)
        settings_manager.set_value(Settings.REPORT_LICENSE, save_report_license)
        settings_manager.set_value(Settings.REPORT_STAKEHOLDERS, save_stakeholders)
        settings_manager.set_value(
            Settings.REPORT_CULTURE_CONSIDERATIONS, save_culture_considerations
        )
        settings_manager.set_value(
            Settings.REPORT_CULTURE_POLICIES, save_culture_policies
        )

        # Loads the values into the GUI
        report_settings_widget.load_settings()

        # Tests if the values were loaded correctly
        organization = report_settings_widget.txt_organization.text()
        self.assertEqual(save_organization, organization)

        email = report_settings_widget.txt_email.text()
        self.assertEqual(save_email, email)

        website = report_settings_widget.txt_website.text()
        self.assertEqual(save_website, website)

        custom_logo = report_settings_widget.cb_custom_logo.checkState()
        self.assertEqual(save_custom_logo_enabled, custom_logo)

        custom_logo_path = report_settings_widget.logo_file.filePath()
        self.assertEqual(save_custom_logo_dir, custom_logo_path)

        footer = report_settings_widget.txt_footer.toPlainText()
        self.assertEqual(save_footer, footer)

        disclaimer = report_settings_widget.txt_disclaimer.toPlainText()
        self.assertEqual(save_disclaimer, disclaimer)

        report_license = report_settings_widget.txt_license.text()
        self.assertEqual(save_report_license, report_license)

        stakeholders = report_settings_widget.txt_stakeholders.toPlainText()
        self.assertEqual(save_stakeholders, stakeholders)

        culture_considerations = (
            report_settings_widget.txt_cultural_considerations.toPlainText()
        )
        self.assertEqual(save_culture_considerations, culture_considerations)

        culture_policies = report_settings_widget.txt_policies.toPlainText()
        self.assertEqual(save_culture_policies, culture_policies)

    def test_logo_exist(self):
        """A test which checks if the logo_file_exists function works
        as it should. A test is done for when the logog exist,
        and when the logo does not exist.
        """
        report_settings_widget = ReportSettingsWidget(PARENT)

        logo_exist = "icons/ci_logo.png"
        logo_does_not_exist = "icons/does_not_exist.png"

        report_settings_widget.logo_file.setFilePath(logo_exist)
        file_exist = report_settings_widget.logo_file_exists()
        self.assertEqual(True, file_exist)

        report_settings_widget.logo_file.setFilePath(logo_does_not_exist)
        file_exist = report_settings_widget.logo_file_exists()
        self.assertEqual(False, file_exist)


if __name__ == "__main__":
    unittest.main()
