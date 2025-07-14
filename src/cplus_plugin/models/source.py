# -*- coding: utf-8 -*-

""" QGIS CPLUS plugin models.
"""
from enum import Enum, IntEnum


class DataSourceType(IntEnum):
    """Specifies whether a data source is from a local or online source."""

    LOCAL = 0
    ONLINE = 1
    UNDEFINED = -1

    @staticmethod
    def from_int(int_enum: int) -> "DataSourceType":
        """Creates an enum from the corresponding int equivalent.

        :param int_enum: Integer representing the data source type.
        :type int_enum: int

        :returns: Data source type enum corresponding to the given
        integer else unknown if not found.
        :rtype: DataSourceType
        """
        return {
            0: DataSourceType.LOCAL,
            1: DataSourceType.ONLINE,
            -1: DataSourceType.UNDEFINED,
        }[int_enum]


class LayerSource(Enum):
    """Specify if a layer source is cplus or naturebase."""

    CPLUS = "CPLUS"
    NATUREBASE = "Naturebase"


class AreaOfInterestSource(Enum):
    """Defines the area of inteterest sources"""

    LAYER = 0
    EXTENT = 1
