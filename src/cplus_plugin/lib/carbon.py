# -*- coding: utf-8 -*-
"""
Contains functions for carbon calculations.
"""

from functools import partial
import math
import os
import typing
from itertools import count

from qgis.core import (
    QgsFeedback,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
    QgsRasterIterator,
    QgsRasterLayer,
    QgsRectangle,
)
from qgis import processing

from qgis.PyQt import QtCore

from ..definitions.constants import NPV_PRIORITY_LAYERS_SEGMENT, PRIORITY_LAYERS_SEGMENT
from ..conf import settings_manager, Settings
from ..models.base import DataSourceType
from ..utils import clean_filename, FileUtils, log, tr


# For now, will set this manually but for future implementation, consider
# calculating this automatically based on the pixel size and CRS of the
# reference layer. This area is in hectares i.e. 300m by 300m pixel size.
MEAN_REFERENCE_LAYER_AREA = 9.0


def calculate_irrecoverable_carbon_from_mean(
    ncs_pathways_layer: QgsRasterLayer,
) -> float:
    """Calculates the total irrecoverable carbon for protected NCS pathways
    using the reference layer defined in settings that is based on the
    mean value per hectare.

    This is a manual, pixel-by-pixel analysis that overcomes the limitations
    of the raster calculator and zonal statistics tools, which use the intersection
    of the center point of the reference pixel to determine whether the reference
    pixel will be considered in the computation. The use of these tools results in some
    valid intersecting pixels being excluded from the analysis. This is a known
    issue that has been raised in the QGIS GitHub repo, hence the reason of
    adopting this function.

    :param ncs_pathways_layer: Layer containing a union of protected NCS pathways.
    The CRS needs to be WGS84 otherwise the result will be incorrect.
    :type ncs_pathways_layer: QgsRasterLayer

    :returns: The total irrecoverable carbon for protected NCS pathways
    specified in the input. If there are any errors during the operation,
    such as an invalid input raster layer, then -1.0 will be returned.
    :rtype: float
    """
    if not ncs_pathways_layer.isValid():
        log("Input union of protected NCS pathways is invalid.", info=False)
        return -1.0

    # TBC - should we cancel the process if using IC is disabled in settings? If
    # so, we will need to explicitly need to check the corresponding settings.
    source_type_int = settings_manager.get_value(
        Settings.IRRECOVERABLE_CARBON_SOURCE_TYPE,
        default=DataSourceType.UNDEFINED.value,
        setting_type=int,
    )
    reference_source_path = ""
    if source_type_int == DataSourceType.LOCAL.value:
        reference_source_path = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_LOCAL_SOURCE, default=""
        )
    elif source_type_int == DataSourceType.ONLINE.value:
        reference_source_path = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_SOURCE, default=""
        )

    if not reference_source_path:
        log(
            "Data source for reference irrecoverable carbon layer not found.",
            info=False,
        )
        return -1.0

    norm_source_path = os.path.normpath(reference_source_path)
    if not os.path.exists(norm_source_path):
        error_msg = (
            f"Data source for reference irrecoverable carbon layer "
            f"{norm_source_path} does not exist."
        )
        log(error_msg, info=False)
        return -1.0

    reference_irrecoverable_carbon_layer = QgsRasterLayer(
        norm_source_path, "mean_irrecoverable_carbon"
    )

    # Check CRS and warn if different
    if reference_irrecoverable_carbon_layer.crs() != ncs_pathways_layer.crs():
        log(
            "Final computation might be incorrect as protected NCS "
            "pathways and reference irrecoverable carbon layer have different "
            "CRSs.",
            info=False,
        )

    reference_extent = reference_irrecoverable_carbon_layer.extent()
    ncs_pathways_extent = ncs_pathways_layer.extent()
    # if they do not intersect then exit. This might also be related to the CRS.
    if not reference_extent.intersects(ncs_pathways_extent):
        log(
            "The protected NCS pathways layer does not intersect with "
            "the reference irrecoverable carbon layer.",
            info=False,
        )
        return -1.0

    reference_provider = reference_irrecoverable_carbon_layer.dataProvider()
    reference_layer_iterator = QgsRasterIterator(reference_provider)
    reference_layer_iterator.startRasterRead(
        1, reference_provider.xSize(), reference_provider.ySize(), reference_extent
    )

    irrecoverable_carbon_intersecting_pixel_values = []

    while True:
        (
            success,
            columns,
            rows,
            block,
            left,
            top,
        ) = reference_layer_iterator.readNextRasterPart(1)

        if not success:
            log(
                "Unable to read the reference irrecoverable carbon layer.",
                info=False,
            )
            break

        for r in range(rows):
            block_part_y_min = reference_extent.yMaximum() - (
                (r + 1) / rows * reference_extent.height()
            )
            block_part_y_max = reference_extent.yMaximum() - (
                r / rows * reference_extent.height()
            )

            for c in range(columns):
                if block.isNoData(r, c):
                    continue

                block_part_x_min = reference_extent.xMinimum() + (
                    c / columns * reference_extent.width()
                )
                block_part_x_max = reference_extent.xMinimum() + (
                    (c + 1) / columns * reference_extent.width()
                )

                # Use this to check if there are intersecting NCS pathway pixels in
                # the reference layer block
                analysis_extent = QgsRectangle(
                    block_part_x_min,
                    block_part_y_min,
                    block_part_x_max,
                    block_part_y_max,
                )
                ncs_cols = math.ceil(
                    1.0
                    * analysis_extent.width()
                    / ncs_pathways_layer.rasterUnitsPerPixelX()
                )
                ncs_rows = math.ceil(
                    1.0
                    * analysis_extent.height()
                    / ncs_pathways_layer.rasterUnitsPerPixelY()
                )

                ncs_block = ncs_pathways_layer.dataProvider().block(
                    1, analysis_extent, ncs_cols, ncs_rows
                )
                ncs_block_data = ncs_block.data()

                fill_data = QtCore.QByteArray()
                if ncs_pathways_layer.dataProvider().sourceHasNoDataValue(1):
                    # If there are no overlaps, the block will contain nodata values
                    fill_data = ncs_block.valueBytes(
                        ncs_block.dataType(), ncs_block.noDataValue()
                    )

                # Check if the NCS block within the reference block contains
                # any other values apart from nodata.
                ncs_ba_set = set(ncs_block_data[i] for i in range(ncs_block_data.size()))
                fill_ba_set = set(fill_data[i] for i in range(fill_data.size()))

                if ncs_ba_set - fill_ba_set:
                    # we have valid overlapping pixels hence we can pick the value of
                    # the reference IC layer.
                    irrecoverable_carbon_intersecting_pixel_values.append(block.value(r, c))

    reference_layer_iterator.stopRasterRead(1)

    ic_count = len(irrecoverable_carbon_intersecting_pixel_values)
    if count == 0:
        log(
            "No protected NCS pathways were found in the reference layer.",
            info=False,
        )
        return -1.0

    ic_mean = sum(irrecoverable_carbon_intersecting_pixel_values) / float(ic_count)

    return MEAN_REFERENCE_LAYER_AREA * ic_count * ic_mean
