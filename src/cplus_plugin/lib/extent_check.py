# -*- coding: utf-8 -*-
"""
Checks if a given extent is within the pilot area of interest.
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
)

from ..definitions.defaults import DEFAULT_CRS_ID, PILOT_AREA_EXTENT


def extent_within_pilot(new_extent: QgsRectangle) -> bool:
    """Checks if the extent is within the pilot area.

    :param new_extent: Extent to check if within the pilot area.
    :type new_extent: QgsRectangle

    :returns: True if the current map canvas extent is within the
    pilot area, else False.
    :rtype: bool
    """
    extent_list = PILOT_AREA_EXTENT["coordinates"]
    pilot_extent = QgsRectangle(
        extent_list[0], extent_list[2], extent_list[1], extent_list[3]
    )

    default_crs = QgsCoordinateReferenceSystem.fromEpsgId(DEFAULT_CRS_ID)
    project_crs = QgsProject.instance().crs()

    if default_crs != project_crs:
        coordinate_xform = QgsCoordinateTransform(
            default_crs, project_crs, QgsProject.instance()
        )
        new_extent = coordinate_xform.transformBoundingBox(new_extent)

    return pilot_extent.contains(new_extent)
