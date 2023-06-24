# -*- coding: utf-8 -*-

""" QGIS CPLUS plugin models
"""

import enum
from enum import Enum

import dataclasses
import uuid

from enum import IntEnum
import os.path
import typing


from uuid import UUID

from qgis.core import QgsMapLayer, QgsRasterLayer, QgsVectorLayer

from ..utils import tr


class PRIORITY_GROUP(enum.Enum):
    """Represents the STAC API resource types"""

    CARBON_IMPORTANCE = "Carbon importance"
    BIODIVERSITY = "Biodiversity"
    LIVELIHOOD = "Livelihood"
    CLIMATE_RESILIENCE = "Climate Resilience"
    ECOLOGICAL_INFRASTRUCTURE = "Ecological infrastructure"
    POLICY = "Policy"
    FINANCE_YEARS_EXPERIENCE = "Finance - Years Experience"
    FINANCE_MARKET_TRENDS = "Finance - Market Trends"
    FINANCE_NET_PRESENT_VALUE = "Finance - Net Present value"
    FINANCE_CARBON = "Finance - Carbon"


@dataclasses.dataclass
class SpatialExtent:
    """Extent object that stores
    the coordinates of the area of interest
    """

    bbox: typing.List[float]


@dataclasses.dataclass
class BaseModelComponent:
    """Base class for common model item properties."""

    uuid: UUID
    name: str
    description: str


BaseModelComponentType = typing.TypeVar(
    "BaseModelComponentType", bound=BaseModelComponent
)


class LayerType(IntEnum):
    """QGIS spatial layer type."""

    RASTER = 0
    VECTOR = 1
    UNDEFINED = -1


@dataclasses.dataclass
class NcsPathway(BaseModelComponent):
    """Contains information about an NCS pathway layer."""

    path: str
    layer_type: LayerType = LayerType.UNDEFINED
    user_defined: bool = False

    def to_map_layer(self) -> typing.Union[QgsMapLayer, None]:
        """Constructs a map layer from the specified path.

        If the path does not exist, it will return None.

        :returns: Map layer corresponding to the specified path.
        :rtype: QgsMapLayer
        """
        if not os.path.exists(self.path):
            return None

        ncs_layer = None
        if self.layer_type == LayerType.RASTER:
            ncs_layer = QgsRasterLayer(self.path, self.name)

        elif self.layer_type == LayerType.VECTOR:
            ncs_layer = QgsVectorLayer(self.path, self.name)

        return ncs_layer

    def is_valid(self) -> bool:
        """Checks if the corresponding map layer is valid.

        :returns: True if the map layer is valid, else False if map layer is
        invalid or of None type.
        :rtype: bool
        """
        layer = self.to_map_layer()
        if layer is None:
            return False

        return layer.isValid()


def model_component_to_dict(model_component: BaseModelComponentType) -> dict:
    """Creates a dictionary containing the base attribute
    name-value pairs from a model component object.

    :param model_component: Source model component object whose
    values are to be mapped to the corresponding
    attribute names.
    :type model_component: BaseModelComponent

    :returns: Returns a dictionary item containing attribute
    name-value pairs.
    :rtype: dict
    """
    return {
        "uuid": str(model_component.uuid),
        "name": model_component.name,
        "description": model_component.description,
    }


def create_model_component(
    source_dict: dict,
    model_cls: typing.Callable[[uuid.UUID, str, str], BaseModelComponentType],
) -> typing.Union[BaseModelComponentType, None]:
    """Factory method for creating and setting attribute values
    for a base model component object.

    :param source_dict: Dictionary containing attribute values.
    :type source_dict: dict

    :param model_cls: Callable class that will be created based on the
    input argument values from the dictionary.
    :type model_cls: BaseModelComponent

    :returns: Base model component object with property values
    derived from the dictionary.
    :rtype: BaseModelComponent
    """
    if not issubclass(model_cls, BaseModelComponent):
        return None

    return model_cls(
        uuid.UUID(source_dict["uuid"]), source_dict["name"], source_dict["description"]
    )


def create_ncs_pathway(source_dict) -> NcsPathway:
    """Factory method for creating an NcsPathway object using
    attribute values defined in a dictionary.

    :param source_dict: Dictionary containing property values.
    :type source_dict: dict

    :returns: NCS pathway object with property values set
    from the dictionary.
    :rtype: NcsPathway
    """
    return NcsPathway(
        uuid.UUID(source_dict["uuid"]),
        source_dict["name"],
        source_dict["description"],
        source_dict["path"],
        LayerType(int(source_dict["layer_type"])),
        bool(source_dict["user_defined"]),
    )


def ncs_pathway_to_dict(ncs_pathway: NcsPathway) -> dict:
    """Creates a dictionary containing attribute
    name-value pairs from an NCS pathway object.

    :param ncs_pathway: Source NCS pathway object whose
    values are to be mapped to the corresponding
    attribute names.
    :type ncs_pathway: NcsPathway

    :returns: Returns a dictionary item containing attribute
    name-value pairs.
    :rtype: dict
    """
    base_attrs = model_component_to_dict(ncs_pathway)
    base_attrs["path"] = ncs_pathway.path
    base_attrs["layer_type"] = int(ncs_pathway.layer_type)
    base_attrs["user_defined"] = ncs_pathway.user_defined

    return base_attrs


@dataclasses.dataclass
class ImplementationModel(BaseModelComponent):
    """Contains information about the implementation model for a scenario."""

    pathways: typing.List[NcsPathway] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        """Ensure there are no duplicate pathways."""
        uuids = [str(p.uuid) for p in self.pathways]

        if len(set(uuids)) != len(uuids):
            msg = tr("Duplicate pathways found in implementation model")
            raise ValueError(f"{msg} {self.name}")

    def contains_pathway(self, pathway_uuid: str) -> bool:
        """Checks if there is an NCS pathway matching the given UUID.

        :param pathway_uuid: UUID to search for in the collection.
        :type pathway_uuid: str

        :returns: True if there is a matching NCS pathway, else False.
        :rtype: bool
        """
        ncs_pathway = self.pathway_by_uuid(pathway_uuid)
        if ncs_pathway is None:
            return False

        return True

    def add_ncs_pathway(self, ncs: NcsPathway) -> bool:
        """Adds an NCS pathway object to the collection.

        :param ncs: NCS pathway to be added to the model.
        :type ncs: NcsPathway

        :returns: True if the NCS pathway was successfully added, else False
        if there was an existing NCS pathway object with a similar UUID.
        """
        if self.contains_pathway(str(ncs.uuid)):
            return False

        self.pathways.append(ncs)

        return True

    def remove_ncs_pathway(self, pathway_uuid: str) -> bool:
        """Removes the NCS pathway with a matching UUID from the collection.

        :param pathway_uuid: UUID for the NCS pathway to be removed.
        :type pathway_uuid: str

        :returns: True if the NCS pathway object was successfully removed,
         else False if there is no object matching the given UUID.
        :rtype: bool
        """
        idxs = [i for i, p in enumerate(self.pathways) if str(p.uuid) == pathway_uuid]

        if len(idxs) == 0:
            return False

        rem_idx = idxs[0]
        _ = self.pathways.pop(rem_idx)

        return True

    def pathway_by_uuid(self, pathway_uuid: str) -> typing.Union[NcsPathway, None]:
        """Returns an NCS pathway matching the given UUID.

        :param pathway_uuid: UUID for the NCS pathway to retrieve.
        :type pathway_uuid: str

        :returns: NCS pathway object matching the given UUID else None if
        not found.
        :rtype: NcsPathway
        """
        pathways = [p for p in self.pathways if str(p.uuid) == pathway_uuid]

        if len(pathways) == 0:
            return None

        return pathways[0]


@dataclasses.dataclass
class Scenario(BaseModelComponent):
    """Object for the handling
    workflow scenario information.
    """

    extent: SpatialExtent
    # TODO: Confirm if this should be weighted model instead.
    models: typing.List[ImplementationModel]
