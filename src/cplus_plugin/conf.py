# -*- coding: utf-8 -*-
"""
    Handles storage and retrieval of the plugin QgsSettings.
"""

import contextlib
import dataclasses
import enum
import json
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

    :param group_root: Name of the root group for the settings.
    :type group_root: str

    :param settings: QGIS settings to use
    :type settings: QgsSettings

    :yields: Instance of the created settings.
    :type: QgsSettings
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
    """Plugin Scenario settings"""

    @classmethod
    def from_qgs_settings(cls, identifier: str, settings: QgsSettings):
        """Reads QGIS settings and parses them into a scenario
        settings instance with the respective settings values as properties.

        :param identifier: Scenario identifier
        :type identifier: str

        :param settings: QGIS settings.
        :type settings: QgsSettings

        :returns: Scenario settings object
        :rtype: ScenarioSettings
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

        :param scenario_settings: Scenario settings instance
        :type scenario_settings: ScenarioSettings

        :returns: Spatial extent instance extent
        :rtype: SpatialExtent
        """
        spatial_key = "extent/spatial"

        with qgis_settings(spatial_key, scenario_settings) as settings:
            bbox = settings.value("bbox", None)
            spatial_extent = SpatialExtent(bbox=bbox)

        return spatial_extent


class Settings(enum.Enum):
    """Plugin settings names"""

    DOWNLOAD_FOLDER = "download_folder"
    REFRESH_FREQUENCY = "refresh/period"
    REFRESH_FREQUENCY_UNIT = "refresh/unit"
    REFRESH_LAST_UPDATE = "refresh/last_update"
    REFRESH_STATE = "refresh/state"


class SettingsManager(QtCore.QObject):
    """Manages saving/loading settings for the plugin in QgsSettings."""

    BASE_GROUP_NAME: str = "cplus_plugin"
    SCENARIO_GROUP_NAME: str = "scenarios"
    PRIORITY_LAYERS_GROUP_NAME: str = "priority_layers"

    settings = QgsSettings()

    scenarios_settings_updated = QtCore.pyqtSignal()

    def set_value(self, name: str, value):
        """Adds a new setting key and value on the plugin specific settings.

        :param name: Name of setting key
        :type name: str

        :param value: Value of the setting
        :type value: Any

        """
        self.settings.setValue(f"{self.BASE_GROUP_NAME}/{name}", value)

    def get_value(self, name: str, default=None, setting_type=None):
        """Gets value of the setting with the passed name.

        :param name: Name of the setting key
        :type name: str

        :param default: Default value returned when the
         setting key does not exists
        :type default: Any

        :param setting_type: Type of the store setting
        :type setting_type: Any

        :returns: Value of the setting
        :rtype: Any
        """
        if setting_type:
            return self.settings.value(
                f"{self.BASE_GROUP_NAME}/{name}", default, setting_type
            )
        return self.settings.value(f"{self.BASE_GROUP_NAME}/{name}", default)

    def remove(self, name):
        """Remove the setting with the specified name.

        :param name: Name of the setting key
        :type name: str
        """
        self.settings.remove(f"{self.BASE_GROUP_NAME}/{name}")

    def _get_scenario_settings_base(self, identifier):
        """Gets the scenario settings base url.

        :param identifier: Scenario settings identifier
        :type identifier: uuid.UUID

        :returns Scenario settings base group
        :rtype str
        """
        return (
            f"{self.BASE_GROUP_NAME}/"
            f"{self.SCENARIO_GROUP_NAME}/"
            f"{str(identifier)}"
        )

    def save_scenario(self, scenario_settings):
        """Save the passed scenario settings into the plugin settings

        :param scenario_settings: Scenario settings
        :type scenario_settings:  ScenarioSettings
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

        :param extent: Scenario extent
        :type extent: SpatialExtent

        :param key: QgsSettings group key.
        :type key: str
        """
        spatial_extent = extent.spatial.bbox

        spatial_key = f"{key}/extent/spatial/"
        with qgis_settings(spatial_key) as settings:
            settings.setValue("bbox", spatial_extent)

    def get_scenario(self, identifier):
        """Retrieves the scenario that matches the passed identifier.

        :param identifier: Scenario identifier
        :type identifier: str

        :returns Scenario settings instance
        :rtype ScenarioSettings
        """

        settings_key = self._get_scenario_settings_base(identifier)
        with qgis_settings(settings_key) as settings:
            scenario_settings = ScenarioSettings.from_qgs_settings(
                str(identifier), settings
            )
        return scenario_settings

    def get_scenario(self, scenario_id):
        """Retrieves the first scenario that matched the passed scenario id.

        :param scenario_id: Scenario id
        :type scenario_id: str

        :returns Scenario settings instance
        :rtype ScenarioSettings
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

        :returns List of the scenario settings instances
        :rtype list
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

    def _get_priority_layers_settings_base(self, identifier):
        """Gets the priority layers settings base url.

        :param identifier: Priority layers settings identifier
        :type identifier: uuid.UUID

        :returns Priority layers settings base group
        :rtype str
        """
        return (
            f"{self.BASE_GROUP_NAME}/"
            f"{self.PRIORITY_LAYERS_GROUP_NAME}/"
            f"{str(identifier)}"
        )

    def get_priority_layer(self, identifier):
        """Retrieves the priority layer that matches the passed identifier.

        :param identifier: Priority identifier
        :type identifier: str

        :returns Priority layer
        :rtype dict
        """

        settings_key = self._get_priority_layers_settings_base(identifier)
        with qgis_settings(settings_key) as settings:
            groups_key = f"{settings}/groups"
            groups = []

            with qgis_settings(groups_key) as groups_settings:
                for name in groups_settings.childGroups():
                    group_settings_key = f"{groups_key}/{name}"
                    with qgis_settings(group_settings_key) as group_settings:
                        stored_group = {}
                        stored_group["name"] = group_settings.value("name")
                        stored_group["value"] = group_settings.value("value")
                        groups.append(stored_group)

            priority_layer = {"uuid": identifier}
            priority_layer["name"] = settings.value("name")
            priority_layer["description"] = settings.value("description")
            priority_layer["selected"] = settings.value("selected")
            priority_layer["groups"] = groups
        return priority_layer

    def find_layer_by_name(self, name):
        """Finds a priority layer setting inside the plugin QgsSettings by name.

        :param name: Name of the layer
        :type: str

        :returns: Priority layer dictionary
        :rtype: dict
        """
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_LAYERS_GROUP_NAME}"
        ) as settings:
            for layer_id in settings.childGroups():
                layer_settings_key = self._get_priority_layers_settings_base(layer_id)
                with qgis_settings(layer_settings_key) as layer_settings:
                    layer_name = layer_settings.value("name")
                    if layer_name == name:
                        found_id = uuid.UUID(layer_id)
                        break
            else:
                raise ValueError(
                    f"Could not find a priority layer named " f"{name!r} in QgsSettings"
                )
        return self.get_priority_layer(found_id)

    def save_priority_layer(self, priority_layer):
        """Save the priority layer into the plugin settings

        :param priority_layer: Priority layer
        :type priority_layer:  dict
        """
        settings_key = self._get_priority_layers_settings_base(priority_layer["uuid"])

        with qgis_settings(settings_key) as settings:
            groups = priority_layer["groups"]
            settings.setValue("name", priority_layer["name"])
            settings.setValue("description", priority_layer["description"])
            settings.setValue("selected", priority_layer["selected"])
            groups_key = f"{settings_key}/groups"
            for group in groups:
                group_key = f"{groups_key}/{group['name']}"
                with qgis_settings(group_key) as group_settings:
                    group_settings.setValue("name", group["name"])
                    group_settings.setValue("value", group["value"])

    def get_priority_layers(self):
        """Gets all the available priority layers in the plugin.

        :returns List of the priority layers instances
        :rtype list
        """
        result = []
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_LAYERS_GROUP_NAME}"
        ) as settings:
            for uuid in settings.childGroups():
                priority_layer_settings = self._get_priority_layers_settings_base(uuid)
                with qgis_settings(priority_layer_settings) as priority_settings:
                    groups_key = f"{priority_layer_settings}/groups"
                    groups = []

                    with qgis_settings(groups_key) as groups_settings:
                        for name in groups_settings.childGroups():
                            group_settings_key = f"{groups_key}/{name}"
                            with qgis_settings(group_settings_key) as group_settings:
                                stored_group = {}
                                stored_group["name"] = group_settings.value("name")
                                stored_group["value"] = group_settings.value("value")
                                groups.append(stored_group)
                    layer = {
                        "uuid": uuid,
                        "name": priority_settings.value("name"),
                        "description": priority_settings.value("description"),
                        "selected": priority_settings.value("selected"),
                        "groups": groups,
                    }
                    result.append(layer)
        return result

    def delete_priority_layers(self):
        """Deletes all the plugin priority settings."""
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_LAYERS_GROUP_NAME}"
        ) as settings:
            for priority_layer in settings.childGroups():
                settings.remove(priority_layer)

    def delete_priority_layer(self, identifier):
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_LAYERS_GROUP_NAME}/"
        ) as settings:
            for priority_layer in settings.childGroups():
                if priority_layer == identifier:
                    settings.remove(priority_layer)


settings_manager = SettingsManager()
