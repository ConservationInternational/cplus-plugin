# -*- coding: utf-8 -*-

""" QGIS CPLUS plugin models
"""

import dataclasses
from enum import Enum
import os.path
import typing

from uuid import UUID

from qgis.core import (
    QgsMapLayer,
    QgsRasterLayer,
    QgsVectorLayer
)


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


class LayerType(Enum):
    """QGIS spatial layer type."""

    RASTER = 0
    VECTOR = 1
    UNDEFINED = 2


@dataclasses.dataclass
class NcsPathway(BaseModelComponent):
    """Contains information about an NCS pathway layer."""

    path: str
    layer_type: LayerType
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


@dataclasses.dataclass
class ImplementationModel(BaseModelComponent):
    """Contains information about the implementation model for a scenario."""

    pathways: typing.List[NcsPathway]


@dataclasses.dataclass
class Scenario(BaseModelComponent):
    """Object for the handling
    workflow scenario information.
    """

    extent: SpatialExtent
    # TODO: Confirm if this should be weighted model instead.
    models: typing.List[ImplementationModel]
