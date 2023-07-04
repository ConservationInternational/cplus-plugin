# -*- coding: utf-8 -*-

""" QGIS CPLUS plugin models
"""

import dataclasses
import enum
import typing


from uuid import UUID


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
class Scenario:
    """Object for the handling
    workflow scenario information.
    """

    uuid: UUID
    name: str
    description: str
    extent: SpatialExtent
