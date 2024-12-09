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
    QgsCoordinateReferenceSystem,
    QgsFeedback,
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
    QgsRasterBlock,
    QgsRasterIterator,
    QgsRasterLayer,
    QgsRectangle,
)
from qgis import processing

from qgis.PyQt import QtCore

from ..definitions.constants import NPV_PRIORITY_LAYERS_SEGMENT, PRIORITY_LAYERS_SEGMENT
from ..conf import settings_manager, Settings
from ..models.base import Activity, DataSourceType, NcsPathwayType
from ..utils import clean_filename, FileUtils, log, tr


# For now, will set this manually but for future implementation, consider
# calculating this automatically based on the pixel size and CRS of the
# reference layer. This area is in hectares i.e. 300m by 300m pixel size.
MEAN_REFERENCE_LAYER_AREA = 9.0


def calculate_irrecoverable_carbon_from_mean(
    ncs_pathways_layer: QgsRasterLayer,
) -> float:
    """Calculates the total irrecoverable carbon in tonnes for protect NCS pathways
    using the reference layer defined in settings that is based on the
    mean value per hectare.

    This is a manual, pixel-by-pixel analysis that overcomes the limitations
    of the raster calculator and zonal statistics tools, which use the intersection
    of the center point of the reference pixel to determine whether the reference
    pixel will be considered in the computation. The use of these tools results in some
    valid intersecting pixels being excluded from the analysis. This is a known
    issue that has been raised in the QGIS GitHub repo, hence the reason for
    using this function.

    :param ncs_pathways_layer: Layer containing an aggregate of protect NCS pathways.
    The CRS needs to be WGS84 otherwise the result will be incorrect. In addition,
    the layer needs to be in binary form i.e. a pixel value of 1 represents a
    valid value and 0 represents a non-valid or nodata value. The raster boolean
    (AND or OR) tool can be used to normalize the layer before passing it into
    this function.
    :type ncs_pathways_layer: QgsRasterLayer

    :returns: The total irrecoverable carbon for protect NCS pathways
    specified in the input. If there are any errors during the operation,
    such as an invalid input raster layer, then -1.0 will be returned.
    :rtype: float
    """
    if not ncs_pathways_layer.isValid():
        log(
            "Irrecoverable Carbon Calculation - Input union of protect NCS pathways is invalid.",
            info=False,
        )
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
            f"Irrecoverable Carbon Calculation - Data source for reference irrecoverable carbon layer "
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
            "Irrecoverable Carbon Calculation - Final computation might be incorrect as protect NCS "
            "pathways and reference irrecoverable carbon layer have different "
            "CRSs.",
            info=False,
        )

    scenario_extent = settings_manager.get_value(Settings.SCENARIO_EXTENT)
    if scenario_extent is None:
        log(
            "Irrecoverable Carbon Calculation - Scenario extent not defined.",
            info=False,
        )
        return -1.0

    reference_extent = QgsRectangle(
        float(scenario_extent[0]),
        float(scenario_extent[2]),
        float(scenario_extent[1]),
        float(scenario_extent[3]),
    )

    ncs_pathways_extent = ncs_pathways_layer.extent()
    # if they do not intersect then exit. This might also be related to the CRS.
    if not reference_extent.intersects(ncs_pathways_extent):
        log(
            "Irrecoverable Carbon Calculation - The protect NCS pathways layer does not intersect with "
            "the reference irrecoverable carbon layer.",
            info=False,
        )
        return -1.0

    #
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
            break

        if not block.isValid():
            log(
                "Irrecoverable Carbon Calculation - Invalid irrecoverable carbon layer raster block.",
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
                if not ncs_block.isValid():
                    log(
                        "Irrecoverable Carbon Calculation - Invalid aggregated NCS pathway raster block.",
                        info=False,
                    )
                    continue

                ncs_block_data = ncs_block.data()
                invalid_data = QgsRasterBlock.valueBytes(ncs_block.dataType(), 0.0)

                # Check if the NCS block within the reference block contains
                # any other value apart from the invalid value i.e. 0 pixel value.
                # In future iterations, consider using QGIS 3.40+ which includes
                # QgsRasterBlock.as_numpy() that provides the ability to work with
                # the raw binary data in numpy.
                ncs_ba_set = set(
                    ncs_block_data[i] for i in range(ncs_block_data.size())
                )
                invalid_ba_set = set(
                    invalid_data[i] for i in range(invalid_data.size())
                )

                if ncs_ba_set - invalid_ba_set:
                    # we have valid overlapping pixels hence we can pick the value of
                    # the corresponding reference IC layer.
                    irrecoverable_carbon_intersecting_pixel_values.append(
                        block.value(r, c)
                    )

    reference_layer_iterator.stopRasterRead(1)

    ic_count = len(irrecoverable_carbon_intersecting_pixel_values)
    if ic_count == 0:
        log(
            "Irrecoverable Carbon Calculation - No protect NCS pathways were found in the reference layer.",
            info=False,
        )
        return 0.0

    ic_mean = sum(irrecoverable_carbon_intersecting_pixel_values) / float(ic_count)

    return MEAN_REFERENCE_LAYER_AREA * ic_count * ic_mean


class IrrecoverableCarbonCalculator:
    """Calculates the total irrecoverable carbon of an activity using
    the mean-based reference carbon layer.

    It specifically searches for protect pathways in the activity.
    If none is found, it will return 0. This is designed to be called
    within a QgsExpressionFunction.
    """

    def __init__(self, activity: typing.Union[str, Activity]):
        if isinstance(activity, str):
            activity = settings_manager.get_activity(activity)

        self._activity = activity

    @property
    def activity(self) -> Activity:
        """Gets the activity used to calculate the total
        irrecoverable carbon.

        :returns: The activity for calculating the total
        irrecoverable carbon.
        :rtype: Activity
        """
        return self._activity

    def run(self) -> float:
        """Calculates the total irrecoverable carbon of the referenced activity.

        :returns: The total irrecoverable carbon of the activity. If there are
        no protect NCS pathways in the activity, the function will return 0.0.
        If there are any errors encountered during the process, the function
        will return -1.0.
        :rtype: float
        """
        if len(self._activity.pathways) == 0:
            log(
                f"Irrecoverable Carbon Calculation - There are no pathways in "
                f"{self._activity.name} activity.",
                info=False,
            )
            return 0.0

        protect_pathways = [
            pathway
            for pathway in self._activity.pathways
            if pathway.pathway_type == NcsPathwayType.PROTECT
        ]

        if len(protect_pathways) == 0:
            log(
                f"Irrecoverable Carbon Calculation - There are no protect pathways in "
                f"{self._activity.name} activity.",
                info=False,
            )
            return 0.0

        protect_layers = [pathway.to_map_layer() for pathway in protect_pathways]
        valid_protect_layers = [layer for layer in protect_layers if layer.isValid()]
        if len(valid_protect_layers) == 0:
            log(
                f"Irrecoverable Carbon Calculation - There are no valid protect pathway layers in "
                f"{self._activity.name} activity.",
                info=False,
            )
            return 0.0

        if len(valid_protect_layers) != len(protect_layers):
            # Just warn if some layers were excluded
            log(
                f"Irrecoverable Carbon Calculation - Some protect pathway layers are invalid and will be "
                f"exclude from the irrecoverable carbon calculation.",
                info=False,
            )

        # Perform a union of the pathways
        processing_context = QgsProcessingContext()

        protect_data_sources = [layer.source() for layer in valid_protect_layers]

        boolean_args = {
            "INPUT": protect_data_sources,
            "REF_LAYER": protect_data_sources[0],
            "NODATA_AS_FALSE": True,
            "NO_DATA": -9999,
            "DATA_TYPE": 11,  # Since we are only dealing wih 0s and 1s, this will help reduce the size of the output file.
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        boolean_result = None
        try:
            boolean_result = processing.run(
                "native:rasterlogicalor",
                boolean_args,
                context=processing_context,
            )
        except QgsProcessingException as ex:
            log(
                "Irrecoverable Carbon Calculation - Error creating a union of protect NCS pathways.",
                info=False,
            )
            return -1.0

        aggregate_raster_path = boolean_result["OUTPUT"]
        aggregate_layer = QgsRasterLayer(aggregate_raster_path, "aggregate_pathways")
        if not aggregate_layer.isValid():
            log(
                "Irrecoverable Carbon Calculation - Aggregate protect pathways layer is invalid.",
                info=False,
            )
            return -1.0

        # Reproject the aggregated protect raster
        reproject_args = {
            "INPUT": aggregate_raster_path,
            "SOURCE_CRS": valid_protect_layers[0].crs(),
            "TARGET_CRS": QgsCoordinateReferenceSystem(
                "EPSG:4326"
            ),  # Global IC reference raster
            "RESAMPLING": 0,
            "DATA_TYPE": 0,
            "OPTIONS": "COMPRESS=DEFLATE|PREDICTOR=2|ZLEVEL=9",
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            "EXTRA": "--config CHECK_DISK_FREE_SPACE NO",
        }
        reproject_result = None
        try:
            reproject_result = processing.run(
                "gdal:warpreproject",
                reproject_args,
                context=QgsProcessingContext(),
            )
        except QgsProcessingException as ex:
            log(
                "Irrecoverable Carbon Calculation - Error re-projecting the "
                "aggregate protect NCS pathways.",
                info=False,
            )
            return -1.0

        reprojected_raster_path = reproject_result["OUTPUT"]

        reprojected_protect_layer = QgsRasterLayer(
            reprojected_raster_path, "reprojected_protect_pathway"
        )
        if not reprojected_protect_layer.isValid():
            log(
                "Irrecoverable Carbon Calculation - Reprojected "
                "protect pathways layer is invalid.",
                info=False,
            )
            return -1.0

        total_irrecoverable_carbon = calculate_irrecoverable_carbon_from_mean(
            reprojected_protect_layer
        )
        if total_irrecoverable_carbon == -1.0:
            log(
                "Irrecoverable Carbon Calculation - Error occurred in "
                "calculating the total irrecoverable carbon. See logs for details.",
                info=False,
            )

        return total_irrecoverable_carbon
