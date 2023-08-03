# -*- coding: utf-8 -*-

""" QGIS CPLUS plugin models.
"""

import dataclasses
import datetime
from enum import Enum, IntEnum
import os.path
import typing
from uuid import UUID

from qgis.core import QgsMapLayer, QgsRasterLayer, QgsVectorLayer


@dataclasses.dataclass
class SpatialExtent:
    """Extent object that stores
    the coordinates of the area of interest
    """

    bbox: typing.List[float]


class PRIORITY_GROUP(Enum):
    """Represents priority groups types"""

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
class BaseModelComponent:
    """Base class for common model item properties."""

    uuid: UUID
    name: str
    description: str

    def __eq__(self, other: "BaseModelComponent") -> bool:
        """Test equality of object with another BaseModelComponent
        object using the attributes.

        :param other: BaseModelComponent object to compare with this object.
        :type other: BaseModelComponent

        :returns: True if the all the attribute values match, else False.
        :rtype: bool
        """
        if self.uuid != other.uuid:
            return False

        if self.name != other.name:
            return False

        if self.description != other.description:
            return False

        return True


BaseModelComponentType = typing.TypeVar(
    "BaseModelComponentType", bound=BaseModelComponent
)


class LayerType(IntEnum):
    """QGIS spatial layer type."""

    RASTER = 0
    VECTOR = 1
    UNDEFINED = -1


class ModelComponentType(Enum):
    """Type of model component i.e. NCS pathway or
    implementation model.
    """

    NCS_PATHWAY = "ncs_pathway"
    IMPLEMENTATION_MODEL = "implementation_model"
    UNKNOWN = "unknown"

    @staticmethod
    def from_string(str_enum: str) -> "ModelComponentType":
        """Creates an enum from the corresponding string equivalent.

        :param str_enum: String representing the model component type.
        :type str_enum: str

        :returns: Component type enum corresponding to the given
        string else unknown if not found.
        :rtype: ModelComponentType
        """
        if str_enum.lower() == "ncs_pathway":
            return ModelComponentType.NCS_PATHWAY
        elif str_enum.lower() == "implementation_model":
            return ModelComponentType.IMPLEMENTATION_MODEL

        return ModelComponentType.UNKNOWN


@dataclasses.dataclass
class LayerModelComponent(BaseModelComponent):
    """Base class for model components that support
    a map layer.
    """

    path: str = ""
    layer_type: LayerType = LayerType.UNDEFINED
    user_defined: bool = False
    layer: typing.Union[QgsMapLayer, None] = None

    def __post_init__(self):
        """Try to set the layer and layer type properties."""
        self.update_layer_type()

    def update_layer_type(self):
        """Update the layer type if either the layer or
        path properties have been set.
        """
        layer = self.to_map_layer()
        if layer is None:
            return

        if not layer.isValid():
            return

        if isinstance(layer, QgsRasterLayer):
            self.layer_type = LayerType.RASTER

        elif isinstance(layer, QgsVectorLayer):
            self.layer_type = LayerType.VECTOR

    def to_map_layer(self) -> typing.Union[QgsMapLayer, None]:
        """Constructs a map layer from the specified path.

        It will first check if the layer property has been set
        else try to construct the layer from the path else return
        None.

        :returns: Map layer corresponding to the set layer
        property or specified path.
        :rtype: QgsMapLayer
        """
        if self.layer:
            return self.layer

        if not os.path.exists(self.path):
            return None

        ncs_layer = None
        if self.layer_type == LayerType.RASTER:
            ncs_layer = QgsRasterLayer(self.path, self.name)

        elif self.layer_type == LayerType.VECTOR:
            ncs_layer = QgsVectorLayer(self.path, self.name)

        if ncs_layer:
            self.layer = ncs_layer

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

    def __eq__(self, other) -> bool:
        """Uses BaseModelComponent equality test rather than
        what the dataclass default implementation will provide.
        """
        return super().__eq__(other)


LayerModelComponentType = typing.TypeVar(
    "LayerModelComponentType", bound=LayerModelComponent
)


@dataclasses.dataclass
class NcsPathway(LayerModelComponent):
    """Contains information about an NCS pathway layer."""

    def __eq__(self, other: "NcsPathway") -> bool:
        """Test equality of NcsPathway object with another
        NcsPathway object using the attributes.

        Excludes testing the map layer for equality.

        :param other: NcsPathway object to compare with this object.
        :type other: NcsPathway

        :returns: True if all the attribute values match, else False.
        :rtype: bool
        """
        base_equality = super().__eq__(other)
        if not base_equality:
            return False

        if self.path != other.path:
            return False

        if self.layer_type != other.layer_type:
            return False

        if self.user_defined != other.user_defined:
            return False

        return True


@dataclasses.dataclass
class ImplementationModel(LayerModelComponent):
    """Contains information about the implementation model
    for a scenario. If the layer has been set then it will
    not be possible to add NCS pathways unless the layer
    is cleared.
    Priority will be given to the layer property.
    """

    pathways: typing.List[NcsPathway] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        """Pre-checks on initialization."""
        super().__post_init__()

        # Ensure there are no duplicate pathways.
        uuids = [str(p.uuid) for p in self.pathways]

        if len(set(uuids)) != len(uuids):
            msg = "Duplicate pathways found in implementation model"
            raise ValueError(f"{msg} {self.name}.")

        # Reset pathways if layer has also been set.
        if self.layer and len(self.pathways) > 0:
            self.pathways = []

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
        if there was an existing NCS pathway object with a similar UUID or
        the layer property had already been set.
        """

        if not ncs.is_valid():
            return False

        if self.contains_pathway(str(ncs.uuid)):
            return False

        self.pathways.append(ncs)

        return True

    def clear_layer(self):
        """Simply sets the layer property so that NCS pathway objects
        can be added.
        """
        self.layer = None

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

    def is_valid(self) -> bool:
        """Includes an additional check to assert if NCS pathways have
        been specified if the layer has not been set or is not valid.

        Does not check for validity of individual NCS pathways in the
        collection.
        """
        if self.layer:
            return super().is_valid()
        else:
            if len(self.pathways) == 0:
                return False

            return True


class ScenarioState(Enum):
    """Defines scenario analysis process states"""

    IDLE = 0
    RUNNING = 1
    STOPPED = 3
    FINISHED = 4
    TERMINATED = 5


@dataclasses.dataclass
class Scenario(BaseModelComponent):
    """Object for the handling
    workflow scenario information.
    """

    extent: SpatialExtent
    # TODO: Confirm if this should be weighted model instead.
    models: typing.List[ImplementationModel]
    priority_layer_groups: typing.List
    state: ScenarioState = ScenarioState.IDLE


@dataclasses.dataclass
class ScenarioResult:
    """Scenario result details."""

    scenario: Scenario
    created_date: datetime.datetime = datetime.datetime.now()
    analysis_output: typing.Dict = None
