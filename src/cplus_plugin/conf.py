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
    create_model_component,
    create_ncs_pathway,
    model_component_to_dict,
    ncs_pathway_to_dict,
)


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
    IMPLEMENTATION_MODEL_BASE: str = "implementation_models"

    settings = QgsSettings()

    scenarios_settings_updated = QtCore.pyqtSignal()
    settings_updated = QtCore.pyqtSignal(Settings, object)

    def set_value(self, name: str, value):
        """Adds a new setting key and value on the plugin specific settings.

        Args:
            name (str): Name of setting key
            value (Any): Value of the setting
        """
        self.settings.setValue(f"{self.BASE_GROUP_NAME}/{name}", value)
        self.settings_updated.emit(name, value)

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
            implementation_model = model_component_to_dict(implementation_model)

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
                implementation_model = create_model_component(
                    json.loads(implementation_model), ImplementationModel
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


settings_manager = SettingsManager()
