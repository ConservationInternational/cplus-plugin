import unittest

from utilities_for_testing import get_qgis_app

# from qgis.utils import iface

from cplus_plugin.settings import CplusSettings
from cplus_plugin.conf import (
    settings_manager,
    Settings,
)

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()
OPTIONS_TITLE = "CPLUS"


class CplusPluginSettingsTest(unittest.TestCase):
    def test_save(self):
        """A test which will check if all CPLUS settings is saved correctly
        when the save_settings function is called.
        """
        settings_dialog = CplusSettings(PARENT)

        save_organization = "a company"
        save_email = "an email"
        save_website = "a website"
        save_custom_logo_enabled = True
        save_custom_logo_dir = "logos/ci_logo.png"
        save_footer = "a footer"
        save_disclaimer = "a disclaimer"
        save_report_license = "license"
        save_base_dir = "base directory"

        carbon_coefficient = 0.1
        coefficient_importance = 3
        pathway_suitability_index = 1.5

        # Sets the values in the GUI
        settings_dialog.txt_organization.setText(save_organization)
        settings_dialog.txt_email.setText(save_email)
        settings_dialog.txt_website.setText(save_website)
        settings_dialog.cb_custom_logo.setCheckState(save_custom_logo_enabled)
        settings_dialog.logo_file.setFilePath(save_custom_logo_dir)
        settings_dialog.txt_footer.setPlainText(save_footer)
        settings_dialog.txt_disclaimer.setPlainText(save_disclaimer)
        settings_dialog.txt_license.setText(save_report_license)
        settings_dialog.folder_data.setFilePath(save_base_dir)

        settings_dialog.carbon_coefficient_box.setValue(carbon_coefficient)
        settings_dialog.coefficients_importance_box.setValue(coefficient_importance)
        settings_dialog.suitability_index_box.setValue(pathway_suitability_index)

        # Saves the settings set in the GUI
        settings_dialog.save_settings()

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

        base_dir = settings_manager.get_value(Settings.BASE_DIR)
        self.assertEqual(save_base_dir, base_dir)

        carbon_coefficient_val = settings_manager.get_value(Settings.CARBON_COEFFICIENT)
        self.assertEqual(carbon_coefficient, carbon_coefficient_val)

        coefficient_importance_val = settings_manager.get_value(
            Settings.COEFFICIENT_IMPORTANCE
        )
        self.assertEqual(coefficient_importance, coefficient_importance_val)

        pathway_suitability_index_val = settings_manager.get_value(
            Settings.PATHWAY_SUITABILITY_INDEX
        )
        self.assertEqual(pathway_suitability_index, pathway_suitability_index_val)

    def test_load(self):
        """A test which will check if the CPLUS settings is loaded correctly
        into the settings UI when calling the load_settings function.
        """
        settings_dialog = CplusSettings(PARENT)

        save_organization = "a company 2"
        save_email = "an email 2"
        save_website = "a website 2"
        save_custom_logo_enabled = False
        save_custom_logo_dir = "logos/ci_logo.png"
        save_footer = "a footer 2"
        save_disclaimer = "a disclaimer 2"
        save_report_license = "license 2"
        save_base_dir = "base directory 2"

        save_carbon_coefficient = 0.1
        save_coefficient_importance = 3
        save_pathway_suitability_index = 1.5

        # Set all values for testing
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
        settings_manager.set_value(Settings.BASE_DIR, save_base_dir)

        settings_manager.set_value(Settings.CARBON_COEFFICIENT, save_carbon_coefficient)
        settings_manager.set_value(
            Settings.COEFFICIENT_IMPORTANCE, save_coefficient_importance
        )
        settings_manager.set_value(
            Settings.PATHWAY_SUITABILITY_INDEX, save_pathway_suitability_index
        )

        # Loads the values into the GUI
        settings_dialog.load_settings()

        # Tests if the values were loaded correctly
        organization = settings_dialog.txt_organization.text()
        self.assertEqual(save_organization, organization)

        email = settings_dialog.txt_email.text()
        self.assertEqual(save_email, email)

        website = settings_dialog.txt_website.text()
        self.assertEqual(save_website, website)

        custom_logo = settings_dialog.cb_custom_logo.checkState()
        self.assertEqual(save_custom_logo_enabled, custom_logo)

        custom_logo_path = settings_dialog.logo_file.filePath()
        self.assertEqual(save_custom_logo_dir, custom_logo_path)

        footer = settings_dialog.txt_footer.toPlainText()
        self.assertEqual(save_footer, footer)

        disclaimer = settings_dialog.txt_disclaimer.toPlainText()
        self.assertEqual(save_disclaimer, disclaimer)

        report_license = settings_dialog.txt_license.text()
        self.assertEqual(save_report_license, report_license)

        base_dir_path = settings_dialog.folder_data.filePath()
        self.assertEqual(save_base_dir, base_dir_path)

        carbon_coefficient = settings_dialog.carbon_coefficient_box.value()
        self.assertEqual(save_carbon_coefficient, carbon_coefficient)

        coefficient_importance = settings_dialog.coefficients_importance_box.value()
        self.assertEqual(save_coefficient_importance, coefficient_importance)

        pathway_suitability_index = settings_dialog.suitability_index_box.value()
        self.assertEqual(save_pathway_suitability_index, pathway_suitability_index)

    def test_base_dir_exist(self):
        """A test which checks if the base_dir_exists function works
        as it should. A test is done for when the base directory exist,
        and when the directory does not exist.
        """
        settings_dialog = CplusSettings(PARENT)

        dir_exist = "logos/"
        dir_does_not_exist = "not_exist"

        settings_dialog.folder_data.setFilePath(dir_exist)
        file_exist = settings_dialog.base_dir_exists()
        self.assertEqual(True, file_exist)

        settings_dialog.folder_data.setFilePath(dir_does_not_exist)
        file_exist = settings_dialog.base_dir_exists()
        self.assertEqual(False, file_exist)

    def test_logo_exist(self):
        """A test which checks if the logo_file_exists function works
        as it should. A test is done for when the logog exist,
        and when the logo does not exist.
        """
        settings_dialog = CplusSettings(PARENT)

        logo_exist = "logos/ci_logo.png"
        logo_does_not_exist = "logos/does_not_exist.png"

        settings_dialog.logo_file.setFilePath(logo_exist)
        file_exist = settings_dialog.logo_file_exists()
        self.assertEqual(True, file_exist)

        settings_dialog.logo_file.setFilePath(logo_does_not_exist)
        file_exist = settings_dialog.logo_file_exists()
        self.assertEqual(False, file_exist)


if __name__ == "__main__":
    unittest.main()
