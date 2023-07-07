# -*- coding: utf-8 -*-
"""
    Handles storage and retrieval of the plugin QgsSettings.
"""

import contextlib
import dataclasses
import enum
import uuid

from qgis.PyQt import (
    QtCore,
    QtWidgets,
)
from qgis.core import QgsRectangle, QgsSettings

from .models.base import Scenario, SpatialExtent


@contextlib.contextmanager
def qgis_settings(group_root: str, settings=None):
    """Context manager to help defining groups when creating QgsSettings.

    Args:
        group_root (str): Name of the root group for the settings
        settings (QgsSettings): QGIS settings to use

    Yields:
        settings (QgsSettings): Instance of the created settings
    """
    if settings is None:
        settings = QgsSettings()
    settings.beginGroup(group_root)
    try:
        yield settings
    finally:
        settings.endGroup()


@dataclasses.dataclass
class ScenarioSettings(Scenario):
    """Plugin Scenario settings."""

    @classmethod
    def from_qgs_settings(cls, identifier: str, settings: QgsSettings):
        """Reads QGIS settings and parses them into a scenario
        settings instance with the respective settings values as properties.

        Args:
            identifier (str): Scenario identifier
            settings (QgsSettings): Scenario identifier

        Returns:
            scenarioSettings (ScenarioSettings): Scenario settings object
        """

        return cls(
            uuid=uuid.UUID(identifier),
            name=settings.value("name", None),
            description=settings.value("description", None),
        )

    @classmethod
    def get_scenario_extent(cls, scenario_settings):
        """Fetches Scenario extent from
         the passed scenario settings.

        Args:
            scenario_settings (ScenarioSettings): Scenario settings instance

        Returns:
            spatialExtent (SpatialExtent): Spatial extent instance extent
        """
        spatial_key = "extent/spatial"

        with qgis_settings(spatial_key, scenario_settings) as settings:
            bbox = settings.value("bbox", None)
            spatial_extent = SpatialExtent(bbox=bbox)

        return spatial_extent


class Settings(enum.Enum):
    """Plugin settings names."""

    DOWNLOAD_FOLDER = "download_folder"
    REFRESH_FREQUENCY = "refresh/period"
    REFRESH_FREQUENCY_UNIT = "refresh/unit"
    REFRESH_LAST_UPDATE = "refresh/last_update"
    REFRESH_STATE = "refresh/state"

    # Report settings
    REPORT_ORGANIZATION = "report/organization"
    REPORT_CONTACT_EMAIL = "report/email"
    REPORT_WEBSITE = "report/website"
    REPORT_CUSTOM_LOGO = "report/custom_logo"
    REPORT_LOGO_DIR = "report/logo_dir"
    REPORT_FOOTER = "report/footer"
    REPORT_DISLAIMER = "report/disclaimer"
    REPORT_LICENSE = "report/license"

    # Advanced settings
    BASE_DIR = "advanced/base_dir"


class SettingsManager(QtCore.QObject):
    """Manages saving/loading settings for the plugin in QgsSettings."""

    BASE_GROUP_NAME: str = "cplus_plugin"
    SCENARIO_GROUP_NAME: str = "scenarios"

    settings = QgsSettings()

    scenarios_settings_updated = QtCore.pyqtSignal()

    def set_value(self, name: str, value):
        """Adds a new setting key and value on the plugin specific settings.

        Args:
            name (str): Name of setting key
            value (Any): Value of the setting
        """
        self.settings.setValue(f"{self.BASE_GROUP_NAME}/{name}", value)

    def get_value(self, name: str, default=None, setting_type=None):
        """Gets value of the setting with the passed name.

        Args:
            name (str): Name of setting key
            default (Any): Default value returned when the setting key does not exist
            setting_type (Any): Type of the store setting

        Returns:
            value (Any): Value of the setting
        """
        if setting_type:
            return self.settings.value(
                f"{self.BASE_GROUP_NAME}/{name}", default, setting_type
            )
        return self.settings.value(f"{self.BASE_GROUP_NAME}/{name}", default)

    def remove(self, name):
        """Remove the setting with the specified name.

        Args:
            name (str): Name of the setting key
        """
        self.settings.remove(f"{self.BASE_GROUP_NAME}/{name}")

    def _get_scenario_settings_base(self, identifier):
        """Gets the scenario settings base url.

        Args:
            identifier (uuid.UUID): Scenario settings identifier

        Returns:
            baseGroup (str): Scenario settings base group
        """
        return (
            f"{self.BASE_GROUP_NAME}/"
            f"{self.SCENARIO_GROUP_NAME}/"
            f"{str(identifier)}"
        )

    def save_scenario(self, scenario_settings):
        """Save the passed scenario settings into the plugin settings

        Args:
            scenario_settings (ScenarioSettings): Scenario settings
        """
        settings_key = self._get_scenario_settings_base(scenario_settings.uuid)

        self.save_scenario_extent(settings_key, scenario_settings.extent)

        with qgis_settings(settings_key) as settings:
            settings.setValue("name", scenario_settings.name)
            settings.setValue("description", scenario_settings.description)
            settings.setValue("uuid", scenario_settings.uuid)

    def save_scenario_extent(self, key, extent):
        """Saves the scenario extent into plugin settings
        using the provided settings group key.

        Args:
            extent (SpatialExtent): Scenario extent
            key (str): QgsSettings group key
        """
        spatial_extent = extent.spatial.bbox

        spatial_key = f"{key}/extent/spatial/"
        with qgis_settings(spatial_key) as settings:
            settings.setValue("bbox", spatial_extent)

    def get_scenario(self, identifier):
        """Retrieves the scenario that matches the passed identifier.

        Args:
            identifier (str): Scenario identifier

        Returns:
            settingsInstance (ScenarioSettings): Scenario settings instance
        """

        settings_key = self._get_scenario_settings_base(identifier)
        with qgis_settings(settings_key) as settings:
            scenario_settings = ScenarioSettings.from_qgs_settings(
                str(identifier), settings
            )
        return scenario_settings

    def get_scenario(self, scenario_id):
        """Retrieves the first scenario that matched the passed scenario id.

        Args:
            scenario_id (str): Scenario id

        Returns:
            settingsInstance (ScenarioSettings): Scenario settings instance
        """

        result = []
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.SCENARIO_GROUP_NAME}"
        ) as settings:
            for uuid in settings.childGroups():
                scenario_settings_key = self._get_scenario_settings_base(uuid)
                with qgis_settings(scenario_settings_key) as scenario_settings:
                    scenario = ScenarioSettings.from_qgs_settings(
                        uuid, scenario_settings
                    )
                    if scenario.id == scenario_id:
                        return scenario
        return None

    def get_scenarios(self):
        """Gets all the available scenarios settings in the plugin.

        Returns:
            settingsInstancesList (list): List of the scenario settings instances
        """
        result = []
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.SCENARIO_GROUP_NAME}"
        ) as settings:
            for uuid in settings.childGroups():
                scenario_settings_key = self._get_scenario_settings_base(uuid)
                with qgis_settings(scenario_settings_key) as scenario_settings:
                    result.append(
                        ScenarioSettings.from_qgs_settings(uuid, scenario_settings)
                    )
        return result

    def delete_all_scenarios(self):
        """Deletes all the plugin scenarios settings."""
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.SCENARIO_GROUP_NAME}"
        ) as settings:
            for scenario_name in settings.childGroups():
                settings.remove(scenario_name)


settings_manager = SettingsManager()
