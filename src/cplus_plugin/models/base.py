# -*- coding: utf-8 -*-

""" QGIS CPLUS plugin models
"""

import dataclasses
import typing

from uuid import UUID


@dataclasses.dataclass
class SpatialExtent:
    """ Extent object that stores
    the coordinates of the area of interest
    """
    bbox: typing.List[float]


@dataclasses.dataclass
class Scenario:
    """ Object for the handling
    workflow scenario information.
    """
    uuid: UUID
    name: str
    description: str
    extent: SpatialExtent
