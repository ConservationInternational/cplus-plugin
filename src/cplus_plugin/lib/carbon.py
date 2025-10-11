# -*- coding: utf-8 -*-
"""
Contains functions for carbon calculations.
"""

from dataclasses import dataclass
import math
from numbers import Number
import os
import typing

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingException,
    QgsRasterBlock,
    QgsRasterIterator,
    QgsRasterLayer,
    QgsRectangle,
)
from qgis import processing

from ..conf import settings_manager, Settings
from ..definitions.constants import CARBON_IMPACT_ATTRIBUTE
from ..models.base import (
    Activity,
    DataSourceType,
    NcsPathway,
    NcsPathwayType,
)
from ..utils import calculate_raster_area, log


# For now, will set this manually but for future implementation, consider
# calculating this automatically based on the pixel size and CRS of the
# reference layer. This area is in hectares i.e. 300m by 300m pixel size.
MEAN_REFERENCE_LAYER_AREA = 9.0

LOG_PREFIX = "Carbon Calculation"


def _validate_and_transform_extent(
    scenario_extent: typing.Tuple, reference_extent_crs_str: str
) -> typing.Optional[QgsRectangle]:
    """Validates and transforms the scenario extent to WGS84 if needed.

    :param scenario_extent: The scenario extent tuple.
    :type scenario_extent: typing.Tuple

    :param reference_extent_crs_str: The CRS string of the reference extent.
    :type reference_extent_crs_str: str

    :returns: The validated and potentially reprojected extent, or None if invalid.
    :rtype: typing.Optional[QgsRectangle]
    """
    reference_extent = QgsRectangle(
        float(scenario_extent[0]),
        float(scenario_extent[2]),
        float(scenario_extent[1]),
        float(scenario_extent[3]),
    )

    # Exit if already in WGS84
    if reference_extent_crs_str == "EPSG:4326":
        return reference_extent

    # Validate and reproject if needed
    reference_extent_crs = QgsCoordinateReferenceSystem(reference_extent_crs_str)
    if not reference_extent_crs.isValid():
        log(f"{LOG_PREFIX} - Scenario extent CRS is invalid.", info=False)
        return None

    try:
        # Update to use project overload
        coordinate_xform = QgsCoordinateTransform(
            reference_extent_crs,
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsCoordinateTransformContext(),
        )
        return coordinate_xform.transformBoundingBox(reference_extent)
    except Exception as e:
        log(
            f"{LOG_PREFIX} - Unable to reproject scenario extent CRS to WGS84 of reference layer. Error: {e}",
            info=False,
        )
        return None


def _get_intersecting_pixel_values(
    ncs_protect_pathways_layer: QgsRasterLayer,
    reference_layer_path: str,
    reference_layer_name: str,
    calculation_type: str,
) -> typing.List[float]:
    """Extracts pixel values from a reference layer that intersect with NCS pathways.

    This is a manual, pixel-by-pixel analysis that overcomes the limitations
    of the raster calculator and zonal statistics tools, which use the intersection
    of the center point of the reference pixel to determine whether the reference
    pixel will be considered in the computation.

    :param ncs_protect_pathways_layer: Layer containing an aggregate of protect NCS pathways.
    The CRS needs to be WGS84 otherwise the result will be incorrect. In addition,
    the layer needs to be in binary form i.e. a pixel value of 1 represents a
    valid value and 0 represents a non-valid or nodata value.
    :type ncs_protect_pathways_layer: QgsRasterLayer

    :param reference_layer_path: Path to the reference carbon layer.
    :type reference_layer_path: str

    :param reference_layer_name: Name for the reference layer.
    :type reference_layer_name: str

    :param calculation_type: Type of calculation (e.g., "Irrecoverable Carbon", "Stored Carbon").
    :type calculation_type: str

    :returns: List of intersecting pixel values. Returns an empty list if there are
    any errors during the operation or no intersections are found.
    :rtype: typing.List[float]
    """
    # Validate input layer
    if not ncs_protect_pathways_layer.isValid():
        log(
            f"{LOG_PREFIX} - Input union of protect NCS pathways is invalid.",
            info=False,
        )
        return []

    # Validate reference layer path
    norm_source_path = os.path.normpath(reference_layer_path)
    if not os.path.exists(norm_source_path):
        log(
            f"{LOG_PREFIX} - {calculation_type} - Data source for reference "
            f"layer {norm_source_path} does not exist.",
            info=False,
        )
        return []

    # Load and validate reference layer
    reference_layer = QgsRasterLayer(norm_source_path, reference_layer_name)
    if not reference_layer.isValid():
        log(
            f"{LOG_PREFIX} - Reference {calculation_type} layer is invalid.",
            info=False,
        )
        return []

    # Check CRS compatibility
    if reference_layer.crs() != ncs_protect_pathways_layer.crs():
        log(
            f"{LOG_PREFIX} - Final computation might be incorrect as protect NCS "
            f"pathways and reference {calculation_type} layer have different CRSs.",
            info=False,
        )

    # Get and validate scenario extent
    scenario_extent = settings_manager.get_value(Settings.SCENARIO_EXTENT)
    if scenario_extent is None:
        log(f"{LOG_PREFIX} - Scenario extent not defined.", info=False)
        return []

    # Get and validate scenario CRS
    reference_extent_crs_str = settings_manager.get_value(
        Settings.SCENARIO_CRS, default=""
    )
    if not reference_extent_crs_str:
        log(f"{LOG_PREFIX} - Scenario extent CRS not been defined.", info=False)
        return []

    # Transform extent to WGS84 if needed
    reference_extent = _validate_and_transform_extent(
        scenario_extent, reference_extent_crs_str
    )
    if reference_extent is None:
        return []

    # Check intersection
    ncs_pathways_extent = ncs_protect_pathways_layer.extent()
    if not reference_extent.intersects(ncs_pathways_extent):
        log(
            f"{LOG_PREFIX} - The protect NCS pathways layer does not intersect with "
            f"the reference {calculation_type} layer. "
            f"\nReference extent: {reference_extent.toString()} "
            f"\nProtect NCS pathway extent: {ncs_pathways_extent.toString()}",
            info=False,
        )
        return []

    # Constants for NCS pathway layer
    ncs_pixel_width = ncs_protect_pathways_layer.rasterUnitsPerPixelX()
    ncs_pixel_height = ncs_protect_pathways_layer.rasterUnitsPerPixelY()
    ncs_provider = ncs_protect_pathways_layer.dataProvider()

    # Reference extent properties
    ref_width = reference_extent.width()
    ref_height = reference_extent.height()
    ref_x_min = reference_extent.xMinimum()
    ref_y_max = reference_extent.yMaximum()

    # Specify extents for reading the reference layer
    reference_num_cols = math.floor(ref_width / reference_layer.rasterUnitsPerPixelX())
    reference_num_rows = math.floor(ref_height / reference_layer.rasterUnitsPerPixelY())

    # Initialize iterator
    reference_provider = reference_layer.dataProvider()
    reference_layer_iterator = QgsRasterIterator(reference_provider)
    reference_layer_iterator.startRasterRead(
        1, reference_num_cols, reference_num_rows, reference_extent
    )

    intersecting_pixel_values = []

    # Process reference layer blocks
    while True:
        result = reference_layer_iterator.readNextRasterPart(1)
        success, columns, rows, block, left, top = result

        if not success:
            break

        if not block.isValid():
            log(
                f"{LOG_PREFIX} - Invalid {calculation_type} layer raster block.",
                info=False,
            )
            break

        col_step = ref_width / columns
        row_step = ref_height / rows

        # Set invalid data bytes once per block
        invalid_data = None

        for r in range(rows):
            # Calculate y bounds once per row
            block_part_y_max = ref_y_max - r * row_step
            block_part_y_min = block_part_y_max - row_step

            for c in range(columns):
                if block.isNoData(r, c):
                    continue

                # Calculate x bounds
                block_part_x_min = ref_x_min + c * col_step
                block_part_x_max = block_part_x_min + col_step

                # Create analysis extent
                analysis_extent = QgsRectangle(
                    block_part_x_min,
                    block_part_y_min,
                    block_part_x_max,
                    block_part_y_max,
                )

                # Calculate required dimensions for NCS block
                ncs_cols = math.ceil(analysis_extent.width() / ncs_pixel_width)
                ncs_rows = math.ceil(analysis_extent.height() / ncs_pixel_height)

                # Get NCS block
                ncs_block = ncs_provider.block(1, analysis_extent, ncs_cols, ncs_rows)
                if not ncs_block.isValid():
                    log(
                        f"{LOG_PREFIX} - Invalid aggregated NCS pathway raster block.",
                        info=False,
                    )
                    continue

                # Initialization invalid data once
                if invalid_data is None:
                    invalid_data = QgsRasterBlock.valueBytes(ncs_block.dataType(), 0.0)

                ncs_block_data = ncs_block.data()

                # Check if the NCS block contains any valid data i.e. if the NCS
                # block within the reference block contains any other value
                # apart from the invalid value i.e. 0 pixel value.
                ncs_ba_set = set(
                    ncs_block_data[i] for i in range(ncs_block_data.size())
                )
                invalid_ba_set = set(
                    invalid_data[i] for i in range(invalid_data.size())
                )

                if ncs_ba_set - invalid_ba_set:
                    # We have valid overlapping pixels, store the reference value
                    intersecting_pixel_values.append(block.value(r, c))

    reference_layer_iterator.stopRasterRead(1)

    if len(intersecting_pixel_values) == 0:
        log(
            f"{LOG_PREFIX} - No protect NCS pathways were found in the reference layer.",
            info=False,
        )

    return intersecting_pixel_values


def calculate_irrecoverable_carbon_from_mean(
    ncs_pathways_layer: QgsRasterLayer,
) -> float:
    """Calculates the total irrecoverable carbon in tonnes for protect NCS pathways
    using the reference layer defined in settings that is based on the
    mean value per hectare.

    :param ncs_pathways_layer: Layer containing an aggregate of protect NCS pathways.
    :type ncs_pathways_layer: QgsRasterLayer

    :returns: The total irrecoverable carbon for protect NCS pathways.
    If there are any errors, returns -1.0. If no pathways found, returns 0.0.
    :rtype: float
    """
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
            Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH, default=""
        )

    if not reference_source_path:
        log(
            f"{LOG_PREFIX} - Data source for reference irrecoverable carbon layer not found.",
            info=False,
        )
        return -1.0

    log("Calculating the total irrecoverable carbon from mean...")

    intersecting_pixel_values = _get_intersecting_pixel_values(
        ncs_pathways_layer,
        reference_source_path,
        "mean_irrecoverable_carbon",
        "Irrecoverable Carbon",
    )

    # Empty list indicates that an error occurred
    if intersecting_pixel_values is None:
        return -1.0

    pixel_count = len(intersecting_pixel_values)
    if pixel_count == 0:
        return 0.0

    # Calculate using mean-based approach: mean × pixel_count × area_per_pixel
    ic_mean = sum(intersecting_pixel_values) / float(pixel_count)
    return MEAN_REFERENCE_LAYER_AREA * pixel_count * ic_mean


def calculate_stored_carbon(
    ncs_pathways_layer: QgsRasterLayer,
) -> float:
    """Calculates the total stored carbon in tonnes for protect NCS pathways
    by summing pixel values from the biomass reference layer defined in settings.

    :param ncs_pathways_layer: Layer containing an aggregate of protect NCS pathways.
    :type ncs_pathways_layer: QgsRasterLayer

    :returns: The total stored carbon for protect NCS pathways.
    If there are any errors, returns -1.0. If no pathways found, returns 0.0.
    :rtype: float
    """
    reference_source_path = settings_manager.get_value(
        Settings.STORED_CARBON_BIOMASS_PATH, default=""
    )

    if not reference_source_path:
        log(
            f"{LOG_PREFIX} - Data source for reference biomass layer not found.",
            info=False,
        )
        return -1.0

    log("Calculating the stored carbon...")

    intersecting_pixel_values = _get_intersecting_pixel_values(
        ncs_pathways_layer,
        reference_source_path,
        "biomass_stored_carbon",
        "Stored Carbon",
    )

    # Empty list indicates an error occurred
    if intersecting_pixel_values is None:
        return -1.0

    pixel_count = len(intersecting_pixel_values)
    if pixel_count == 0:
        return 0.0

    # Calculate by direct summation of pixel values
    return sum(intersecting_pixel_values)


@dataclass
class NcsPathwayCarbonInfo:
    """Container for NcsPathway layer and corresponding carbon
    impact value.
    """

    layer: QgsRasterLayer
    carbon_impact_per_ha: float


def calculate_manage_pathway_carbon(
    ncs_pathways_carbon_info: typing.List[NcsPathwayCarbonInfo],
) -> float:
    """Calculates the carbon impact in tonnes for manage NCS pathways
    by multiplying the area of the manage NCS pathway layers with
    the user-defined carbon impact rate for the specific NCS pathway.

    :param ncs_pathways_carbon_info: Container for pathway rasters
    and their corresponding carbon impact values.
    :type ncs_pathways_carbon_info: typing.List[NcsPathwayCarbonInfo]

    :returns: The total carbon impact for manage NCS pathways. If no
    pathways found, returns 0.0.
    :rtype: float
    """
    if not ncs_pathways_carbon_info:
        log(
            f"{LOG_PREFIX} - No pathways found for calculating "
            f"carbon impact for manage pathways.",
            info=False,
        )
        return 0.0

    log("Calculating carbon impact for manage pathways...")

    total_carbon = 0.0
    for carbon_info in ncs_pathways_carbon_info:
        area = calculate_raster_area(carbon_info.layer, 1)
        if area != -1.0:
            total_carbon += area * carbon_info.carbon_impact_per_ha

    return total_carbon


class BasePathwaysCarbonCalculator:
    """Base class for carbon calculators for NCS pathways.

    This class encapsulates the common logic for preparing
    the NCS pathways.
    """

    def __init__(self, activity: typing.Union[str, Activity]):
        if isinstance(activity, str):
            activity = settings_manager.get_activity(activity)

        self._activity = activity

    @property
    def activity(self) -> Activity:
        """Gets the activity used to calculate carbon values.

        :returns: The activity for calculating carbon values.
        :rtype: Activity
        """
        return self._activity

    @property
    def calculation_type(self) -> str:
        """Returns the type of calculation being performed.
        Should be overridden by subclasses.

        :returns: The calculation type name.
        :rtype: str
        """
        return "Carbon"

    @property
    def pathway_type(self) -> NcsPathwayType:
        """Returns the NCS pathway type used in the carbon
        calculation. Needs to be overridden in subclasses.

        :returns: NCS pathway type to be applied in the calculation.
        :rtype:
        """
        return NcsPathwayType.UNDEFINED

    def get_pathways(self) -> typing.List[NcsPathway]:
        """Returns NCS pathways based on the type defined in
        subclass implementations.

        :returns: NCS pathways of the type defined in the
        subclass. If the type of the NCS pathway in the
        activity is not defined, then it will be excluded
        from the list.
        """
        if self.pathway_type == NcsPathwayType.UNDEFINED:
            return []

        if self._activity is None:
            log(
                f"{LOG_PREFIX} - The activity is invalid, null reference.",
                info=False,
            )
            return None

        if len(self._activity.pathways) == 0:
            log(
                f"{LOG_PREFIX} - There are no pathways in "
                f"{self._activity.name} activity.",
                info=False,
            )
            return None

        type_pathways = [
            pathway
            for pathway in self._activity.pathways
            if pathway.pathway_type == self.pathway_type
        ]

        return type_pathways

    def run(self) -> float:
        """Calculates carbon value for the referenced activity.

        Subclasses need to implement this function.

        :returns: The total carbon value.
        :rtype: float
        """
        raise NotImplementedError("Subclasses must implement the 'run' function.")


class BaseProtectPathwaysCarbonCalculator(BasePathwaysCarbonCalculator):
    """Base class for carbon calculators that process protect pathways.

    This class encapsulates the common logic for preparing and processing
    protect NCS pathways before calculating carbon values.
    """

    @property
    def pathway_type(self) -> NcsPathwayType:
        """Returns the NCS protect pathway type used in
        the carbon calculation.

        :returns: NCS protect pathway type applied in
        the calculation.
        :rtype:
        """
        return NcsPathwayType.PROTECT

    def _prepare_protect_pathways_layer(self) -> typing.Optional[QgsRasterLayer]:
        """Prepares a binary, reprojected layer from all protect pathways in the activity.

        :returns: The prepared raster layer or None if an error occurs.
        :rtype: typing.Optional[QgsRasterLayer]
        """
        protect_pathways = self.get_pathways()

        if len(protect_pathways) == 0:
            log(
                f"{LOG_PREFIX} - There are no protect pathways in "
                f"{self._activity.name} activity.",
                info=False,
            )
            return None

        protect_layers = [pathway.to_map_layer() for pathway in protect_pathways]
        valid_protect_layers = [layer for layer in protect_layers if layer.isValid()]
        if len(valid_protect_layers) == 0:
            log(
                f"{LOG_PREFIX} - There are no valid protect pathway layers in "
                f"{self._activity.name} activity.",
                info=False,
            )
            return None

        if len(valid_protect_layers) != len(protect_layers):
            log(
                f"{LOG_PREFIX} - Some protect pathway layers are invalid and will be "
                f"excluded from the {self.calculation_type.lower()} calculation.",
                info=False,
            )

        processing_context = QgsProcessingContext()
        protect_data_sources = [layer.source() for layer in valid_protect_layers]

        # First merge the protect NCS pathways into one raster
        merge_args = {
            "INPUT": protect_data_sources,
            "PCT": False,
            "SEPARATE": False,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        merge_result = None
        try:
            log(
                f"{LOG_PREFIX} - Merging protect NCS pathways: {', '.join(protect_data_sources)}..."
            )
            merge_result = processing.run(
                "gdal:merge",
                merge_args,
                context=processing_context,
            )
        except QgsProcessingException as ex:
            log(
                f"{LOG_PREFIX} - Error creating a union of protect NCS pathways.",
                info=False,
            )
            return None

        merged_layer_path = merge_result["OUTPUT"]
        merged_layer = QgsRasterLayer(merged_layer_path, "merged_pathways")
        if not merged_layer.isValid():
            log(
                f"{LOG_PREFIX} - Merged protect pathways layer is invalid.",
                info=False,
            )
            return None

        # Perform a binary transformation to get only the valid pixels for analysis
        boolean_args = {
            "INPUT": merged_layer_path,
            "REF_LAYER": merged_layer_path,
            "NODATA_AS_FALSE": True,
            "DATA_TYPE": 0,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        boolean_result = None
        try:
            log(
                f"{LOG_PREFIX} - Performing binary conversion of merged protect NCS pathways..."
            )
            boolean_result = processing.run(
                "native:rasterlogicalor",
                boolean_args,
                context=processing_context,
            )
        except QgsProcessingException as ex:
            log(
                f"{LOG_PREFIX} - Error creating a binary of merged protect NCS pathways.",
                info=False,
            )
            return None

        binary_layer_path = boolean_result["OUTPUT"]
        binary_layer = QgsRasterLayer(binary_layer_path, "binary_pathways")
        if not binary_layer.isValid():
            log(
                f"{LOG_PREFIX} - Binary protect pathways layer is invalid.",
                info=False,
            )
            return None

        # Reproject the aggregated protect raster if required
        if binary_layer.crs() != QgsCoordinateReferenceSystem("EPSG:4326"):
            log(
                f"{LOG_PREFIX} - Binary protect pathways layer has a different CRS from "
                f"the reference {self.calculation_type.lower()} dataset."
            )
            reproject_args = {
                "INPUT": binary_layer_path,
                "SOURCE_CRS": binary_layer.crs(),
                "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:4326"),
                "RESAMPLING": 0,
                "DATA_TYPE": 0,
                "OPTIONS": "COMPRESS=DEFLATE|PREDICTOR=2|ZLEVEL=9",
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                "EXTRA": "--config CHECK_DISK_FREE_SPACE NO",
            }
            reproject_result = None
            try:
                log(f"{LOG_PREFIX} - Re-projecting binary protected NCS pathways...")
                reproject_result = processing.run(
                    "gdal:warpreproject",
                    reproject_args,
                    context=QgsProcessingContext(),
                )
            except QgsProcessingException as ex:
                log(
                    f"{LOG_PREFIX} - Error re-projecting the "
                    "binary protect NCS pathways.",
                    info=False,
                )
                return None

            binary_layer_path = reproject_result["OUTPUT"]

        reprojected_protect_layer = QgsRasterLayer(
            binary_layer_path, "reprojected_protect_pathway"
        )
        if not reprojected_protect_layer.isValid():
            log(
                f"{LOG_PREFIX} - Reprojected protect pathways layer is invalid.",
                info=False,
            )
            return None

        return reprojected_protect_layer

    def _calculate_carbon(self, prepared_layer: QgsRasterLayer) -> float:
        """Performs the actual carbon calculation. Should be overridden by subclasses.

        :param prepared_layer: The prepared protect pathways layer.
        :type prepared_layer: QgsRasterLayer

        :returns: The calculated carbon value.
        :rtype: float
        """
        raise NotImplementedError(
            "Subclasses must implement the protected _calculate_carbon function."
        )

    def run(self) -> float:
        """Calculates the total carbon value for the referenced activity.

        :returns: The total carbon value. If there are no protect NCS pathways,
        returns 0.0. If errors occur, returns -1.0.
        :rtype: float
        """
        prepared_layer = self._prepare_protect_pathways_layer()
        if prepared_layer is None:
            return 0.0

        total_carbon = self._calculate_carbon(prepared_layer)

        if total_carbon == -1.0:
            log(
                f"{LOG_PREFIX} - Error occurred in calculating the total "
                f"{self.calculation_type.lower()}. See preceding logs for details.",
                info=False,
            )
        else:
            log(
                f"Finished calculating the total {self.calculation_type.lower()} "
                f"of {self._activity.name} as {total_carbon!s}"
            )

        return total_carbon


class IrrecoverableCarbonCalculator(BaseProtectPathwaysCarbonCalculator):
    """Calculates the total irrecoverable carbon of an activity using
    the mean-based reference carbon layer.

    It specifically searches for protect pathways in the activity.
    If there are no protect pathways is found, it will return 0. This is
    designed to be called within a QgsExpressionFunction.
    """

    @property
    def calculation_type(self) -> str:
        return "Irrecoverable Carbon"

    def _calculate_carbon(self, prepared_layer: QgsRasterLayer) -> float:
        return calculate_irrecoverable_carbon_from_mean(prepared_layer)


class StoredCarbonCalculator(BaseProtectPathwaysCarbonCalculator):
    """Calculates the Stored carbon of an activity using
    the biomass reference layer.

    It specifically searches for protect pathways in the activity.
    If there are no protect pathways is found, it will return 0. This is
    designed to be called within a QgsExpressionFunction.
    """

    @property
    def calculation_type(self) -> str:
        return "Stored Carbon"

    def _calculate_carbon(self, prepared_layer: QgsRasterLayer) -> float:
        return calculate_stored_carbon(prepared_layer)


class ManagePathwaysCarbonCalculator(BasePathwaysCarbonCalculator):
    """Class for carbon calculation for manage NCS pathways."""

    @property
    def pathway_type(self) -> NcsPathwayType:
        """Returns the NCS manage pathway type used in
        the carbon calculation.

        :returns: NCS manage pathway type applied in
        the calculation.
        :rtype:
        """
        return NcsPathwayType.MANAGE

    @property
    def calculation_type(self) -> str:
        return "Manage Carbon Impact"

    def run(self) -> float:
        """Calculates the carbon impact for manage NCS pathways.

        :returns: The total carbon impact value. If there are
        no manage NCS pathways, returns 0.0. If errors occur,
        returns -1.0.
        :rtype: float
        """
        manage_pathways = self.get_pathways()

        if len(manage_pathways) == 0:
            log(
                f"{LOG_PREFIX} - There are no manage pathways in "
                f"{self._activity.name} activity.",
                info=False,
            )
            return 0.0

        manage_carbon_info = [
            NcsPathwayCarbonInfo(layer, pathway.type_options[CARBON_IMPACT_ATTRIBUTE])
            for pathway in manage_pathways
            for layer in [pathway.to_map_layer()]
            if layer.isValid() and CARBON_IMPACT_ATTRIBUTE in pathway.type_options
        ]

        if len(manage_carbon_info) == 0:
            log(
                f"{LOG_PREFIX} - There are no valid manage pathway layers in "
                f"{self._activity.name} activity.",
                info=False,
            )
            return 0.0

        if len(manage_carbon_info) != len(manage_pathways):
            log(
                f"{LOG_PREFIX} - Some manage pathway layers are invalid and will be "
                f"excluded from the {self.calculation_type.lower()} calculation.",
                info=False,
            )

        return calculate_manage_pathway_carbon(manage_carbon_info)


def calculate_activity_naturebase_carbon_impact(activity: Activity) -> float:
    """Calculates the carbon mitigation impact of an activity from Naturbase pathway.

    It sums the carbon mitigation values across each NCS Naturebase pathway that constitutes the
    activity.

    :param activity: The specific activity.
    :type activity: Activity

    :returns: Returns the total carbon impact of the activity, or -1.0
    if the activity does not exist or lacks Naturebase pathways.
    :rtype: float
    """
    if activity is None or len(activity.pathways) == 0:
        return -1.0

    pathways = [
        pathway
        for pathway in activity.pathways
        if pathway.name.startswith("Naturebase:")
        and isinstance(pathway.carbon_impact_value, Number)
    ]

    if not pathways:
        return -1.0

    return float(sum(p.carbon_impact_value for p in pathways))
