# -*- coding: utf-8 -*-
"""
    Handles storage and retrieval of the plugin QgsSettings.
"""

import contextlib
import dataclasses
import enum
import json
import os.path
from pathlib import Path
import typing
import uuid

from qgis.PyQt import QtCore
from qgis.core import QgsRectangle, QgsSettings

from .definitions.constants import NCS_PATHWAY_SEGMENT

from .models.base import (
    ImplementationModel,
    NcsPathway,
    Scenario,
    SpatialExtent,
)
from .models.helpers import (
    create_implementation_model,
    create_ncs_pathway,
    layer_component_to_dict,
    ncs_pathway_to_dict,
)

from .utils import log


@contextlib.contextmanager
def qgis_settings(group_root: str, settings=None):
    """Context manager to help defining groups when creating QgsSettings.

    :param group_root: Name of the root group for the settings
    :type group_root: str

    :param settings: QGIS settings to use
    :type settings: QgsSettings

    :yields: Instance of the created settings
    :ytype: QgsSettings
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

        :param identifier: Scenario identifier
        :type identifier: str

        :param settings: Scenario identifier
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
    def get_scenario_extent(cls):
        """Fetches Scenario extent from
         the passed scenario settings.


        :returns: Spatial extent instance extent
        :rtype: SpatialExtent
        """
        spatial_key = "extent/spatial"

        with qgis_settings(spatial_key, cls) as settings:
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

    # Report settings
    REPORT_ORGANIZATION = "report/organization"
    REPORT_CONTACT_EMAIL = "report/email"
    REPORT_WEBSITE = "report/website"
    REPORT_CUSTOM_LOGO = "report/custom_logo"
    REPORT_CPLUS_LOGO = "report/cplus_logo"
    REPORT_CI_LOGO = "report/ci_logo"
    REPORT_LOGO_DIR = "report/logo_dir"
    REPORT_FOOTER = "report/footer"
    REPORT_DISCLAIMER = "report/disclaimer"
    REPORT_LICENSE = "report/license"

    # Last selected data directory
    LAST_DATA_DIR = "last_data_dir"

    # Advanced settings
    BASE_DIR = "advanced/base_dir"

    # Scenario basic details
    SCENARIO_NAME = "scenario_name"
    SCENARIO_DESCRIPTION = "scenario_description"
    SCENARIO_EXTENT = "scenario_extent"


class SettingsManager(QtCore.QObject):
    """Manages saving/loading settings for the plugin in QgsSettings."""

    BASE_GROUP_NAME: str = "cplus_plugin"
    SCENARIO_GROUP_NAME: str = "scenarios"
    PRIORITY_GROUP_NAME: str = "priority_groups"
    PRIORITY_LAYERS_GROUP_NAME: str = "priority_layers"
    NCS_PATHWAY_BASE: str = "ncs_pathways"

    IMPLEMENTATION_MODEL_BASE: str = "implementation_models"

    settings = QgsSettings()

    scenarios_settings_updated = QtCore.pyqtSignal()
    priority_layers_changed = QtCore.pyqtSignal()
    settings_updated = QtCore.pyqtSignal([str, object], [Settings, object])

    def set_value(self, name: str, value):
        """Adds a new setting key and value on the plugin specific settings.

        :param name: Name of setting key
        :type name: str

        :param value: Value of the setting
        :type value: Any
        """
        self.settings.setValue(f"{self.BASE_GROUP_NAME}/{name}", value)
        if isinstance(name, Settings):
            name = name.value

        self.settings_updated.emit(name, value)

    def get_value(self, name: str, default=None, setting_type=None):
        """Gets value of the setting with the passed name.

        :param name: Name of setting key
        :type name: str

        :param default: Default value returned when the setting key does not exist
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

    def delete_settings(self):
        """Deletes the all the plugin settings."""
        self.settings.remove(f"{self.BASE_GROUP_NAME}")

    def _get_scenario_settings_base(self, identifier):
        """Gets the scenario settings base url.

        :param identifier: Scenario settings identifier
        :type identifier: uuid.UUID

        :returns: Scenario settings base group
        :rtype: str
        """
        return (
            f"{self.BASE_GROUP_NAME}/"
            f"{self.SCENARIO_GROUP_NAME}/"
            f"{str(identifier)}"
        )

    def save_scenario(self, scenario_settings):
        """Save the passed scenario settings into the plugin settings

        :param scenario_settings: Scenario settings
        :type scenario_settings: ScenarioSettings
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

        :param key: Scenario extent
        :type key: SpatialExtent

        :param extent: QgsSettings group key
        :type extent: str

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

        :param identifier: Scenario identifier
        :type identifier: str

        :returns: Scenario settings instance
        :rtype: ScenarioSettings
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

        :returns: Scenario settings instance
        :rtype: ScenarioSettings
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

        :returns: List of the scenario settings instances
        :rtype: list
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
                    scenario.extent = self.get_scenario_
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

    def _get_priority_layers_settings_base(self, identifier) -> str:
        """Gets the priority layers settings base url.

        :param identifier: Priority layers settings identifier
        :type identifier: uuid.UUID

        :returns: Priority layers settings base group
        :rtype: str
        """
        return (
            f"{self.BASE_GROUP_NAME}/"
            f"{self.PRIORITY_LAYERS_GROUP_NAME}/"
            f"{str(identifier)}"
        )

    def get_priority_layer(self, identifier) -> typing.Dict:
        """Retrieves the priority layer that matches the passed identifier.

        :param identifier: Priority layers identifier
        :type identifier: uuid.UUID

        :returns: Priority layers dict
        :rtype: dict
        """

        settings_key = self._get_priority_layers_settings_base(identifier)
        with qgis_settings(settings_key) as settings:
            groups_key = f"{settings_key}/groups"
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
            priority_layer["selected"] = settings.value("selected", type=bool)
            priority_layer["groups"] = groups
        return priority_layer

    def get_priority_layers(self) -> typing.List:
        """Gets all the available priority layers in the plugin.

        :returns: Priority layers list
        :rtype: list
        """
        priority_layer_list = []
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
                        "selected": priority_settings.value("selected", type=bool),
                        "groups": groups,
                    }
                    priority_layer_list.append(layer)
        return priority_layer_list

    def find_layer_by_name(self, name) -> typing.Dict:
        """Finds a priority layer setting inside
        the plugin QgsSettings by name.

        :param name: Priority layers identifier
        :type name: str

        :returns: Priority layers dict
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

        return self.get_priority_layer(found_id)

    def find_layers_by_group(self, group) -> typing.List:
        """Finds priority layers inside the plugin QgsSettings
         that contain the passed group.

        :param group: Priority group name
        :type group: str

        :returns: Priority layers list
        :rtype: list
        """
        layers = []
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_LAYERS_GROUP_NAME}"
        ) as settings:
            for layer_id in settings.childGroups():
                priority_layer_settings = self._get_priority_layers_settings_base(
                    layer_id
                )
                with qgis_settings(priority_layer_settings) as priority_settings:
                    groups_key = f"{priority_layer_settings}/groups"

                    with qgis_settings(groups_key) as groups_settings:
                        for name in groups_settings.childGroups():
                            group_settings_key = f"{groups_key}/{name}"
                            with qgis_settings(group_settings_key) as group_settings:
                                if group == group_settings.value("name"):
                                    layers.append(self.get_priority_layer(layer_id))
        return layers

    def save_priority_layer(self, priority_layer):
        """Save the priority layer into the plugin settings.
        Updates the layer with new priority groups.

        Note: Emits priority_layers_changed signal

        :param priority_layer: Priority layer
        :type priority_layer: dict
        """
        settings_key = self._get_priority_layers_settings_base(priority_layer["uuid"])

        with qgis_settings(settings_key) as settings:
            groups = priority_layer.get("groups", [])
            settings.setValue("name", priority_layer["name"])
            settings.setValue("description", priority_layer["description"])
            settings.setValue("selected", priority_layer["selected"])
            groups_key = f"{settings_key}/groups"
            with qgis_settings(groups_key) as groups_settings:
                for group_id in groups_settings.childGroups():
                    groups_settings.remove(group_id)
            for group in groups:
                group_key = f"{groups_key}/{group['name']}"
                with qgis_settings(group_key) as group_settings:
                    group_settings.setValue("name", group["name"])
                    group_settings.setValue("value", group["value"])

        self.priority_layers_changed.emit()

    def set_current_priority_layer(self, identifier):
        """Set current priority layer

        :param identifier: Priority layer identifier
        :type identifier: str
        """
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_LAYERS_GROUP_NAME}/"
        ) as settings:
            for priority_layer in settings.childGroups():
                settings_key = self._get_priority_layers_settings_base(identifier)
                with qgis_settings(settings_key) as layer_settings:
                    layer_settings.setValue(
                        "selected", str(priority_layer) == str(identifier)
                    )

    def delete_priority_layers(self):
        """Deletes all the plugin priority settings."""
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_LAYERS_GROUP_NAME}"
        ) as settings:
            for priority_layer in settings.childGroups():
                settings.remove(priority_layer)

    def delete_priority_layer(self, identifier):
        """Removes priority layer that match the passed identifier

        :param identifier: Priority layer identifier
        :type identifier: str
        """
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_LAYERS_GROUP_NAME}/"
        ) as settings:
            for priority_layer in settings.childGroups():
                if str(priority_layer) == str(identifier):
                    settings.remove(priority_layer)

    def _get_priority_groups_settings_base(self, identifier) -> str:
        """Gets the priority group settings base url.

        :param identifier: Priority group settings identifier
        :type identifier: str

        :returns: Priority groups settings base group
        :rtype: str

        """
        return (
            f"{self.BASE_GROUP_NAME}/"
            f"{self.PRIORITY_GROUP_NAME}/"
            f"{str(identifier)}"
        )

    def find_group_by_name(self, name) -> typing.Dict:
        """Finds a priority group setting inside the plugin QgsSettings by name.

        :param name: Name of the group
        :type name: str

        :returns: Priority group
        :rtype: typing.Dict
        """
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_GROUP_NAME}"
        ) as settings:
            for group_id in settings.childGroups():
                group_settings_key = self._get_priority_groups_settings_base(group_id)
                with qgis_settings(group_settings_key) as group_settings_key:
                    group_name = group_settings_key.value("name")
                    if group_name == name:
                        found_id = uuid.UUID(group_id)
                        break

        return self.get_priority_group(found_id)

    def get_priority_group(self, identifier) -> typing.Dict:
        """Retrieves the priority group that matches the passed identifier.

        :param identifier: Priority group identifier
        :type identifier: str

        :returns: Priority group
        :rtype: typing.Dict
        """

        settings_key = self._get_priority_groups_settings_base(identifier)
        with qgis_settings(settings_key) as settings:
            priority_group = {"uuid": identifier}
            priority_group["name"] = settings.value("name")
            priority_group["value"] = settings.value("value")
        return priority_group

    def get_priority_groups(self) -> typing.List[typing.Dict]:
        """Gets all the available priority groups in the plugin.

        :returns: List of the priority groups instances
        :rtype: list
        """
        priority_groups = []
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_GROUP_NAME}"
        ) as settings:
            for uuid in settings.childGroups():
                priority_layer_settings = self._get_priority_groups_settings_base(uuid)
                with qgis_settings(priority_layer_settings) as priority_settings:
                    group = {
                        "uuid": uuid,
                        "name": priority_settings.value("name"),
                        "value": priority_settings.value("value"),
                    }
                    priority_groups.append(group)
        return priority_groups

    def save_priority_group(self, priority_group):
        """Save the priority group into the plugin settings

        :param priority_group: Priority group
        :type priority_group: str
        """

        settings_key = self._get_priority_groups_settings_base(priority_group["uuid"])

        with qgis_settings(settings_key) as settings:
            settings.setValue("name", priority_group["name"])
            settings.setValue("value", priority_group["value"])

    def delete_priority_groups(self):
        """Deletes all the plugin priority groups settings."""
        with qgis_settings(
            f"{self.BASE_GROUP_NAME}/" f"{self.PRIORITY_GROUP_NAME}"
        ) as settings:
            for priority_group in settings.childGroups():
                settings.remove(priority_group)

    def _get_ncs_pathway_settings_base(self) -> str:
        """Returns the path for NCS pathway settings.

        :returns: Base path to NCS pathway group.
        :rtype: str
        """
        return f"{self.BASE_GROUP_NAME}/" f"{NCS_PATHWAY_SEGMENT}"

    def save_ncs_pathway(self, ncs_pathway: typing.Union[NcsPathway, dict]):
        """Saves an NCS pathway object serialized to a json string
        indexed by the UUID.

        :param ncs_pathway: NCS pathway object or attribute values
        in a dictionary which are then serialized to a JSON string.
        :type ncs_pathway: NcsPathway, dict
        """
        if isinstance(ncs_pathway, NcsPathway):
            ncs_pathway = ncs_pathway_to_dict(ncs_pathway)

        ncs_str = json.dumps(ncs_pathway)

        ncs_uuid = ncs_pathway["uuid"]
        ncs_root = self._get_ncs_pathway_settings_base()

        with qgis_settings(ncs_root) as settings:
            settings.setValue(ncs_uuid, ncs_str)

    def get_ncs_pathway(self, ncs_uuid: str) -> typing.Union[NcsPathway, None]:
        """Gets an NCS pathway object matching the given unique identified.

        :param ncs_uuid: Unique identifier for the NCS pathway object.
        :type ncs_uuid: str

        :returns: Returns the NCS pathway object matching the given
        identifier else None if not found.
        :rtype: NcsPathway
        """
        ncs_pathway = None

        ncs_root = self._get_ncs_pathway_settings_base()

        with qgis_settings(ncs_root) as settings:
            ncs_model = settings.value(ncs_uuid, None)
            if ncs_model is not None:
                ncs_pathway = create_ncs_pathway(json.loads(ncs_model))

        return ncs_pathway

    def get_all_ncs_pathways(self) -> typing.List[NcsPathway]:
        """Get all the NCS pathway objects stored in settings.

        :returns: Returns all the NCS pathway objects.
        :rtype: list
        """
        ncs_pathways = []

        ncs_root = self._get_ncs_pathway_settings_base()

        with qgis_settings(ncs_root) as settings:
            keys = settings.childKeys()
            for k in keys:
                ncs_pathway = self.get_ncs_pathway(k)
                if ncs_pathway is not None:
                    ncs_pathways.append(ncs_pathway)

        return sorted(ncs_pathways, key=lambda ncs: ncs.name)

    def update_ncs_pathways(self):
        """Updates the path attribute of all NCS pathway settings
        based on the BASE_DIR settings to reflect the absolute path
        of each NCS pathway layer.
        If BASE_DIR is empty then the NCS pathway settings will not
        be updated.
        """
        ncs_pathways = self.get_all_ncs_pathways()
        for ncs in ncs_pathways:
            self.update_ncs_pathway(ncs)

    def update_ncs_pathway(self, ncs_pathway: NcsPathway):
        """Updates the attributes of the NCS pathway object
        in settings. On the path, the BASE_DIR in settings
        is used to reflect the absolute path of each NCS
        pathway layer. If BASE_DIR is empty then the NCS
        pathway setting will not be updated.

        :param ncs_pathway: NCS pathway object to be updated.
        :type ncs_pathway: NcsPathway
        """
        base_dir = self.get_value(Settings.BASE_DIR)
        if not base_dir:
            return

        p = Path(ncs_pathway.path)
        abs_path = f"{base_dir}/{NCS_PATHWAY_SEGMENT}/" f"{p.name}"
        abs_path = str(os.path.normpath(abs_path))
        ncs_pathway.path = abs_path

        # Remove then re-insert
        self.remove_ncs_pathway(str(ncs_pathway.uuid))
        self.save_ncs_pathway(ncs_pathway)

    def remove_ncs_pathway(self, ncs_uuid: str):
        """Removes an NCS pathway settings entry using the UUID.

        :param ncs_uuid: Unique identifier of the NCS pathway entry
        to removed.
        :type ncs_uuid: str
        """
        if self.get_ncs_pathway(ncs_uuid) is not None:
            self.remove(f"{self.NCS_PATHWAY_BASE}/{ncs_uuid}")

    def _get_implementation_model_settings_base(self) -> str:
        """Returns the path for implementation model settings.

        :returns: Base path to implementation model group.
        :rtype: str
        """
        return f"{self.BASE_GROUP_NAME}/" f"{self.IMPLEMENTATION_MODEL_BASE}"

    def save_implementation_model(
        self, implementation_model: typing.Union[ImplementationModel, dict]
    ):
        """Saves an implementation model object serialized to a json string
        indexed by the UUID.

        :param implementation_model: Implementation model object or attribute
        values in a dictionary which are then serialized to a JSON string.
        :type implementation_model: ImplementationModel, dict
        """
        if isinstance(implementation_model, ImplementationModel):
            implementation_model = layer_component_to_dict(implementation_model)

        implementation_model_str = json.dumps(implementation_model)

        implementation_model_uuid = implementation_model["uuid"]
        implementation_model_root = self._get_implementation_model_settings_base()

        with qgis_settings(implementation_model_root) as settings:
            settings.setValue(implementation_model_uuid, implementation_model_str)

    def get_implementation_model(
        self, implementation_model_uuid: str
    ) -> typing.Union[ImplementationModel, None]:
        """Gets an implementation model object matching the given unique
        identified.

        :param implementation_model_uuid: Unique identifier for the
        implementation model object.
        :type implementation_model_uuid: str

        :returns: Returns the implementation model object matching the given
        identifier else None if not found.
        :rtype: ImplementationModel
        """
        implementation_model = None

        implementation_model_root = self._get_implementation_model_settings_base()

        with qgis_settings(implementation_model_root) as settings:
            implementation_model = settings.value(implementation_model_uuid, None)
            if implementation_model is not None:
                implementation_model = create_implementation_model(
                    json.loads(implementation_model)
                )

        return implementation_model

    def get_all_implementation_models(self) -> typing.List[ImplementationModel]:
        """Get all the implementation model objects stored in settings.

        :returns: Returns all the implementation model objects.
        :rtype: list
        """
        implementation_models = []

        implementation_model_root = self._get_implementation_model_settings_base()

        with qgis_settings(implementation_model_root) as settings:
            keys = settings.childKeys()
            for k in keys:
                implementation_model = self.get_implementation_model(k)
                if implementation_model is not None:
                    implementation_models.append(implementation_model)

        return sorted(implementation_models, key=lambda imp_model: imp_model.name)

    def remove_implementation_model(self, implementation_model_uuid: str):
        """Removes an implementation model settings entry using the UUID.

        :param implementation_model_uuid: Unique identifier of the
        implementation model entry to removed.
        :type implementation_model_uuid: str
        """
        if self.get_implementation_model(implementation_model_uuid) is not None:
            self.remove(f"{self.IMPLEMENTATION_MODEL_BASE}/{implementation_model_uuid}")


settings_manager = SettingsManager()
