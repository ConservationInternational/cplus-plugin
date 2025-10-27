# -*- coding: utf-8 -*-
"""Processing utilities for constant rasters."""

import os
import typing
from pathlib import Path

from qgis import processing
from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsProcessingException,
)

from ..models.constant_raster import (
    ConstantRasterCollection,
    ConstantRasterComponent,
    ConstantRasterConfig,
    ConstantRasterMetadata,
    ConstantRasterContext,
)
from ..utils import log, tr


class ConstantRasterProcessingUtils:
    """Utilities for constant raster processing and normalization.

    This class provides methods for creating, processing, and normalizing
    constant rasters according to the CPLUS framework requirements.
    """

    @staticmethod
    def create_constant_raster_metadata_collection(
        collection: ConstantRasterCollection,
        config: ConstantRasterConfig,
        feedback: typing.Optional[QgsProcessingFeedback] = None,
    ) -> ConstantRasterMetadata:
        """Create constant raster metadata from collection and config.

        This method processes the collection, normalizes rasters if needed,
        and creates metadata for the constant raster collection.

        :param collection: ConstantRasterCollection to process
        :param config: Configuration for raster creation
        :param feedback: Optional feedback for progress reporting
        :returns: ConstantRasterMetadata with processed information
        :raises QgsProcessingException: If processing fails
        """
        if feedback:
            feedback.pushInfo("Creating constant raster metadata collection")
            feedback.setProgress(0)

        # Validate collection
        try:
            collection.validate()
        except ValueError as e:
            if feedback:
                feedback.reportError(f"Collection validation failed: {str(e)}")
            raise QgsProcessingException(f"Invalid collection: {str(e)}")

        # Process each component
        total_components = len(collection.components)
        for idx, component in enumerate(collection.components):
            if feedback and feedback.isCanceled():
                raise QgsProcessingException("Processing canceled by user")

            if component.skip_value:
                if feedback:
                    feedback.pushInfo(f"Skipping component {component.component_id}")
                continue

            if feedback:
                progress = int((idx / total_components) * 100)
                feedback.setProgress(progress)
                feedback.pushInfo(
                    f"Processing component {idx + 1}/{total_components}: {component.alias_name or component.component_id}"
                )

            # Process the component raster
            try:
                ConstantRasterProcessingUtils._process_component_raster(
                    component, config, feedback
                )
            except Exception as e:
                if feedback:
                    feedback.reportError(f"Error processing component: {str(e)}")
                raise QgsProcessingException(f"Component processing failed: {str(e)}")

        # Create metadata
        metadata = ConstantRasterMetadata(
            id=f"constant_raster_{id(collection)}",
            display_name=config.value or "Constant Raster Collection",
            fcollection=collection,
        )

        if feedback:
            feedback.setProgress(100)
            feedback.pushInfo(
                "Constant raster metadata collection created successfully"
            )

        return metadata

    @staticmethod
    def _process_component_raster(
        component: ConstantRasterComponent,
        config: ConstantRasterConfig,
        feedback: typing.Optional[QgsProcessingFeedback] = None,
    ) -> None:
        """Process a single component raster.

        :param component: ConstantRasterComponent to process
        :param config: Configuration for raster creation
        :param feedback: Optional feedback for progress reporting
        :raises QgsProcessingException: If processing fails
        """
        if not component.value_info or not component.value_info.filename:
            if feedback:
                feedback.pushWarning(
                    f"Component {component.component_id} has no input raster"
                )
            return

        input_path = component.value_info.filename
        if not os.path.exists(input_path):
            raise QgsProcessingException(f"Input raster not found: {input_path}")

        # Load the raster
        raster_layer = QgsRasterLayer(input_path, "temp_raster")
        if not raster_layer.isValid():
            raise QgsProcessingException(f"Invalid raster layer: {input_path}")

        component.qgis_map_layer = raster_layer

        if feedback:
            feedback.pushInfo(f"Loaded raster: {input_path}")

        # If already normalized, skip normalization
        if component.value_info.normalized:
            if feedback:
                feedback.pushInfo("Raster already normalized, skipping normalization")
            return

        # Normalize the raster if needed
        if feedback:
            feedback.pushInfo("Normalizing raster...")

        # Normalization logic will be implemented based on requirements
        # This is a placeholder for the actual normalization algorithm
        component.value_info.normalized = True

    @staticmethod
    def normalize_raster(
        input_path: str,
        output_path: str,
        min_value: float,
        max_value: float,
        extent: typing.Optional[QgsRectangle] = None,
        resolution: typing.Optional[
            typing.Union[float, typing.Tuple[float, float]]
        ] = None,
        crs: typing.Optional[QgsCoordinateReferenceSystem] = None,
        context: typing.Optional[QgsProcessingContext] = None,
        feedback: typing.Optional[QgsProcessingFeedback] = None,
    ) -> str:
        """Normalize a raster to the specified value range using GDAL.

        This method scales the input raster values to fall within the
        specified min_value and max_value range using GDAL's translate
        with the -scale parameter.

        Formula: ((value - input_min) / (input_max - input_min)) * (max_value - min_value) + min_value

        :param input_path: Path to input raster
        :param output_path: Path for output normalized raster
        :param min_value: Minimum value for normalization
        :param max_value: Maximum value for normalization
        :param extent: Optional extent for clipping
        :param resolution: Optional resolution for resampling
        :param crs: Optional CRS for reprojection
        :param context: Processing context (follows plugin pattern)
        :param feedback: Optional feedback for progress reporting
        :returns: Path to normalized raster
        :raises QgsProcessingException: If normalization fails
        """
        if feedback:
            feedback.pushInfo(f"Normalizing raster: {input_path}")
            feedback.pushInfo(f"Target range: [{min_value}, {max_value}]")

        # Load input raster to get statistics
        raster_layer = QgsRasterLayer(input_path, "input_raster")
        if not raster_layer.isValid():
            raise QgsProcessingException(f"Invalid input raster: {input_path}")

        # Get raster statistics
        provider = raster_layer.dataProvider()
        band = 1  # Assuming single band
        stats = provider.bandStatistics(band)

        input_min = stats.minimumValue
        input_max = stats.maximumValue
        input_range = input_max - input_min

        if feedback:
            feedback.pushInfo(
                f"Input raster stats - min: {input_min}, max: {input_max}"
            )

        if input_range == 0:
            raise QgsProcessingException("Input raster has no variation (min == max)")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Create processing context if not provided
        if context is None:
            context = QgsProcessingContext()

        # Build GDAL translate parameters
        # Using -scale to normalize: -scale <src_min> <src_max> <dst_min> <dst_max>
        alg_params = {
            "INPUT": input_path,
            "OUTPUT": output_path,
            "SCALE": f"{input_min},{input_max},{min_value},{max_value}",
            "DATA_TYPE": 6,  # Float32
        }

        # Add optional extent if provided
        if extent:
            extent_string = (
                f"{extent.xMinimum()},{extent.xMaximum()},"
                f"{extent.yMinimum()},{extent.yMaximum()}"
            )
            if crs:
                extent_string += f" [{crs.authid()}]"
            alg_params["PROJWIN"] = extent_string

        # Add optional CRS if provided
        if crs:
            alg_params["TARGET_CRS"] = crs.authid()

        # Add optional resolution if provided
        if resolution:
            if isinstance(resolution, tuple):
                alg_params["TR"] = f"{resolution[0]} {resolution[1]}"
            else:
                alg_params["TR"] = f"{resolution} {resolution}"

        try:
            if feedback:
                feedback.pushInfo("Running GDAL translate with normalization...")

            # Run GDAL translate following plugin pattern
            result = processing.run(
                "gdal:translate", alg_params, context=context, feedback=feedback
            )

            if feedback:
                feedback.pushInfo(f"Normalization complete: {output_path}")

            return result["OUTPUT"]

        except Exception as ex:
            err_msg = tr("Error normalizing raster")
            log(f"{err_msg}: {str(ex)}", info=False)
            raise QgsProcessingException(f"{err_msg}: {str(ex)}")

    @staticmethod
    def create_constant_raster(
        value: float,
        extent: QgsRectangle,
        pixel_size: float,
        crs: QgsCoordinateReferenceSystem,
        output_path: str,
        context: typing.Optional[QgsProcessingContext] = None,
        feedback: typing.Optional[QgsProcessingFeedback] = None,
    ) -> str:
        """Create a constant raster with a specified value.

        Uses the same pattern as NPV PWL creation in lib/financials.py.
        Creates a raster where all pixels have the same constant value.

        :param value: Constant value for all pixels in the raster
        :param extent: Spatial extent for the raster
        :param pixel_size: Pixel size (resolution) for the raster
        :param crs: Coordinate reference system
        :param output_path: Path for output raster
        :param context: Processing context (follows plugin pattern)
        :param feedback: Optional feedback for progress reporting
        :returns: Path to created raster
        :raises QgsProcessingException: If creation fails
        """
        if feedback:
            feedback.pushInfo(f"Creating constant raster with value: {value}")
            feedback.pushInfo(f"Extent: {extent.toString()}")
            feedback.pushInfo(f"CRS: {crs.authid()}")
            feedback.pushInfo(f"Pixel size: {pixel_size}")
            feedback.pushInfo(
                f"Extent coords: xmin={extent.xMinimum()}, xmax={extent.xMaximum()}, ymin={extent.yMinimum()}, ymax={extent.yMaximum()}"
            )

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Create processing context if not provided
        if context is None:
            context = QgsProcessingContext()

        # Format extent string for QGIS processing
        # Format: "xmin,xmax,ymin,ymax [CRS_ID]"
        extent_string = (
            f"{extent.xMinimum()},{extent.xMaximum()},"
            f"{extent.yMinimum()},{extent.yMaximum()} "
            f"[{crs.authid()}]"
        )

        # Build algorithm parameters (same pattern as create_npv_pwls)
        alg_params = {
            "EXTENT": extent_string,
            "TARGET_CRS": crs.authid(),
            "PIXEL_SIZE": pixel_size,
            "NUMBER": value,  # Constant value for all pixels
            "OUTPUT": output_path,
        }

        try:
            if feedback:
                feedback.pushInfo("Running native:createconstantrasterlayer...")
                feedback.pushInfo(f"Algorithm parameters: {alg_params}")

            # Run QGIS processing following plugin pattern (same as financials.py:183-189)
            result = processing.run(
                "native:createconstantrasterlayer",
                alg_params,
                context=context,
                feedback=feedback,
            )

            if feedback:
                feedback.pushInfo(f"Constant raster created: {output_path}")
                feedback.pushInfo(f"Result: {result}")

            return result["OUTPUT"]

        except QgsProcessingException as ex:
            err_msg = tr("Error creating constant raster")
            log(f"{err_msg}: {str(ex)}", info=False)
            raise QgsProcessingException(f"{err_msg}: {str(ex)}")

    @staticmethod
    def validate_raster(
        raster_path: str, feedback: typing.Optional[QgsProcessingFeedback] = None
    ) -> bool:
        """Validate that a raster file is valid and can be loaded.

        :param raster_path: Path to raster file
        :param feedback: Optional feedback for reporting
        :returns: True if valid, False otherwise
        """
        if not os.path.exists(raster_path):
            if feedback:
                feedback.reportError(f"Raster file not found: {raster_path}")
            return False

        raster_layer = QgsRasterLayer(raster_path, "validation_raster")
        if not raster_layer.isValid():
            if feedback:
                feedback.reportError(f"Invalid raster file: {raster_path}")
            return False

        if feedback:
            feedback.pushInfo(f"Raster validation passed: {raster_path}")

        return True

    @staticmethod
    def get_raster_info(raster_path: str) -> typing.Dict[str, typing.Any]:
        """Get information about a raster file.

        :param raster_path: Path to raster file
        :returns: Dictionary with raster information
        :raises QgsProcessingException: If raster cannot be loaded
        """
        raster_layer = QgsRasterLayer(raster_path, "info_raster")
        if not raster_layer.isValid():
            raise QgsProcessingException(f"Cannot load raster: {raster_path}")

        provider = raster_layer.dataProvider()
        extent = raster_layer.extent()
        crs = raster_layer.crs()

        info = {
            "path": raster_path,
            "width": raster_layer.width(),
            "height": raster_layer.height(),
            "bands": raster_layer.bandCount(),
            "crs": crs.authid() if crs.isValid() else "Unknown",
            "extent": {
                "xmin": extent.xMinimum(),
                "xmax": extent.xMaximum(),
                "ymin": extent.yMinimum(),
                "ymax": extent.yMaximum(),
            },
        }

        # Get band statistics if available
        if raster_layer.bandCount() > 0:
            stats = provider.bandStatistics(1)
            info["statistics"] = {
                "min": stats.minimumValue,
                "max": stats.maximumValue,
                "mean": stats.mean,
                "stddev": stats.stdDev,
            }

        return info


def create_constant_rasters(
    collection: ConstantRasterCollection,
    context: ConstantRasterContext,
    input_range: typing.Tuple[float, float] = (0.0, 100.0),
    feedback: typing.Optional[QgsProcessingFeedback] = None,
) -> typing.List[str]:
    """Create constant rasters for all enabled components in a collection.

    This function creates constant rasters based on the absolute values
    specified in each component's value_info. Uses two-step normalization:
    1. Normalize input values to [0,1] using input_range
    2. Remap to output range using collection's filter_value/total_value

    :param collection: ConstantRasterCollection containing components to process
    :param context: ConstantRasterContext with extent, CRS, and output settings
    :param input_range: Tuple of (min, max) for input values (e.g., 0-100 years)
    :param feedback: Optional feedback for progress reporting
    :returns: List of paths to created raster files
    :raises QgsProcessingException: If raster creation fails
    """
    if feedback:
        feedback.pushInfo("Starting constant raster creation")
        feedback.setProgress(0)

    # Validate inputs
    if not collection:
        raise QgsProcessingException("No collection provided")

    if not context.extent:
        raise QgsProcessingException("No extent provided in context")

    if not context.crs:
        raise QgsProcessingException("No CRS provided in context")

    # Get enabled components
    enabled_components = collection.enabled_components()
    if not enabled_components:
        if feedback:
            feedback.pushWarning("No enabled components found in collection")
        return []

    if feedback:
        feedback.pushInfo(f"Creating {len(enabled_components)} constant rasters")

    # Ensure output directory exists
    if context.output_dir and not os.path.exists(context.output_dir):
        os.makedirs(context.output_dir, exist_ok=True)

    created_rasters = []
    processing_context = QgsProcessingContext()

    # Process each component
    total_components = len(enabled_components)
    for idx, component in enumerate(enabled_components):
        if feedback and feedback.isCanceled():
            raise QgsProcessingException("Processing canceled by user")

        # Update progress
        if feedback:
            progress = int((idx / total_components) * 100)
            feedback.setProgress(progress)
            component_name = component.alias_name or component.component_id
            feedback.pushInfo(
                f"Processing {idx + 1}/{total_components}: {component_name}"
            )

        # Get the constant value
        if not component.value_info:
            if feedback:
                feedback.pushWarning(
                    f"Component {component.component_id} has no value_info, skipping"
                )
            continue

        absolute_value = component.value_info.absolute

        if feedback:
            feedback.pushInfo(f"DEBUG: Input value: {absolute_value}")
            feedback.pushInfo(
                f"DEBUG: Input range: {input_range[0]} - {input_range[1]}"
            )
            feedback.pushInfo(
                f"DEBUG: Output range: {collection.filter_value} - {collection.total_value}"
            )

        # TWO-STEP NORMALIZATION:

        # Step 1: Normalize input value to [0,1] using input_range
        input_min, input_max = input_range
        if input_max != input_min:
            normalized_0_1 = (absolute_value - input_min) / (input_max - input_min)
            # Clamp to [0,1]
            normalized_0_1 = max(0.0, min(1.0, normalized_0_1))
        else:
            # Edge case: if input range is invalid, use 0.5
            normalized_0_1 = 0.5

        if feedback:
            feedback.pushInfo(f"DEBUG: Step 1 - Normalized to [0,1]: {normalized_0_1}")

        # Step 2: Remap [0,1] to output range using collection's filter_value/total_value
        output_min = collection.filter_value
        output_max = collection.total_value
        constant_value = output_min + (normalized_0_1 * (output_max - output_min))

        if feedback:
            feedback.pushInfo(
                f"DEBUG: Step 2 - Remapped to output range: {constant_value}"
            )
            feedback.pushInfo(f"DEBUG: Final raster value: {constant_value}")

        # Generate output filename
        safe_name = (
            component.alias_name.replace(" ", "_").replace("/", "_")
            if component.alias_name
            else component.component_id
        )
        output_filename = f"constant_raster_{safe_name}.tif"
        output_path = (
            os.path.join(context.output_dir, output_filename)
            if context.output_dir
            else output_filename
        )

        try:
            # Create the constant raster
            if feedback:
                feedback.pushInfo(
                    f"Component: {component.alias_name or component.component_id}"
                )
                feedback.pushInfo(f"Absolute value: {absolute_value}")
                feedback.pushInfo(
                    f"Normalization range: {collection.filter_value} - {collection.total_value}"
                )
                feedback.pushInfo(f"Normalized value: {constant_value}")
                feedback.pushInfo(
                    f"Creating raster with normalized value {constant_value} at {output_path}"
                )

            created_path = ConstantRasterProcessingUtils.create_constant_raster(
                value=constant_value,
                extent=context.extent,
                pixel_size=context.pixel_size,
                crs=context.crs,
                output_path=output_path,
                context=processing_context,
                feedback=feedback,
            )

            # Update component with created raster path
            component.value_info.filename = created_path
            component.path = created_path

            created_rasters.append(created_path)

            if feedback:
                feedback.pushInfo(f"Successfully created: {created_path}")

        except Exception as e:
            error_msg = (
                f"Failed to create raster for {component.component_id}: {str(e)}"
            )
            if feedback:
                feedback.reportError(error_msg)
            log(error_msg, info=False)
            # Continue with other components even if one fails

    if feedback:
        feedback.setProgress(100)
        feedback.pushInfo(f"Completed: {len(created_rasters)} rasters created")

    return created_rasters
