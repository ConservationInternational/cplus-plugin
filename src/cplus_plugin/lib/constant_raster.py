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

    @staticmethod
    def create_constant_rasters(
        collection: ConstantRasterCollection,
        context: ConstantRasterContext,
        input_range: typing.Tuple[float, float] = None,
        feedback: typing.Optional[QgsProcessingFeedback] = None,
        metadata_id: str = None,
    ) -> typing.List[str]:
        """Create constant rasters for all enabled components in a collection.

        This function creates constant rasters based on the absolute values
        specified in each component's value_info. Uses two-step normalization:
        1. Normalize input values to [0,1] using actual min/max from component values
        2. Remap to output range using collection's min_value/max_value

        :param collection: ConstantRasterCollection containing components to process
        :param context: ConstantRasterContext with extent, CRS, and output settings
        :param input_range: DEPRECATED - min/max are now calculated from actual component values
        :param feedback: Optional feedback for progress reporting
        :param metadata_id: Metadata ID for determining file naming (e.g., "years_experience_pathway")
        :returns: List of paths to created raster files
        :raises QgsProcessingException: If raster creation fails
        """
        if feedback:
            feedback.pushInfo("Starting constant raster creation")
            feedback.setProgress(0)

        # Validate inputs
        if not collection:
            raise QgsProcessingException("No collection provided")

        # Log skip_raster status
        log(
            f"Constant raster collection skip_raster value: {collection.skip_raster}",
            info=True,
        )
        if collection.skip_raster:
            if feedback:
                feedback.pushInfo(
                    "skip_raster=True: Generating metadata files only (skipping raster creation)"
                )
            log(
                "skip_raster=True: Will generate metadata files only, not raster files",
                info=True,
            )

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

        # STEP 1: Use input_range for normalization (not actual component values)
        # input_range defines the theoretical range (e.g., 0-100 years)
        input_min, input_max = input_range

        if feedback:
            feedback.pushInfo(
                f"Input range for normalization: min={input_min}, max={input_max}"
            )

        # Import helper functions for filename generation and metadata
        from ..models.helpers import (
            get_constant_raster_dir,
            generate_constant_raster_filename,
            save_constant_raster_metadata,
        )

        # Determine the actual output directory using hierarchical structure
        if metadata_id and collection.component_type:
            # Use hierarchical directory structure
            base_dir = context.output_dir or os.path.join(
                os.path.expanduser("~"), "cplus"
            )
            actual_output_dir = get_constant_raster_dir(
                base_dir, collection.component_type, metadata_id
            )
        else:
            # Fallback to flat structure if metadata_id not provided
            actual_output_dir = context.output_dir or os.path.join(
                os.path.expanduser("~"), "cplus", "constant_rasters"
            )

        # Ensure output directory exists
        if actual_output_dir and not os.path.exists(actual_output_dir):
            os.makedirs(actual_output_dir, exist_ok=True)
            if feedback:
                feedback.pushInfo(f"Created output directory: {actual_output_dir}")

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
                feedback.pushInfo(f"Component value: {absolute_value}")
                feedback.pushInfo(f"Input range: {input_min} - {input_max}")
                feedback.pushInfo(
                    f"Output range: {collection.min_value} - {collection.max_value}"
                )

            # TWO-STEP NORMALIZATION:

            # Step 1: Normalize input value to [0,1] using input_range
            if input_max != input_min:
                normalized_0_1 = (absolute_value - input_min) / (input_max - input_min)
                # Clamp to [0,1] range
                normalized_0_1 = max(0.0, min(1.0, normalized_0_1))
            else:
                # Edge case: input range is zero, normalize to 0.5
                normalized_0_1 = 0.5

            if feedback:
                feedback.pushInfo(f"Step 1 - Normalized to [0,1]: {normalized_0_1}")

            # Step 2: Remap [0,1] to user-specified output range
            output_min = collection.min_value
            output_max = collection.max_value
            constant_value = output_min + (normalized_0_1 * (output_max - output_min))

            if feedback:
                feedback.pushInfo(
                    f"Step 2 - Remapped to output range: {constant_value}"
                )
                feedback.pushInfo(f"Final raster value: {constant_value}")

            # Generate output filename using helper
            if metadata_id and component.alias_name:
                # Use descriptive filename with value and unit
                output_filename = generate_constant_raster_filename(
                    component.alias_name, absolute_value, metadata_id
                )
            else:
                # Fallback to old naming scheme
                safe_name = (
                    component.alias_name.replace(" ", "_").replace("/", "_")
                    if component.alias_name
                    else component.component_id
                )
                output_filename = f"constant_raster_{safe_name}.tif"

            output_path = os.path.join(actual_output_dir, output_filename)

            try:
                # Create the constant raster only if skip_raster is False
                if not collection.skip_raster:
                    if feedback:
                        feedback.pushInfo(
                            f"Component: {component.alias_name or component.component_id}"
                        )
                        feedback.pushInfo(f"Absolute value: {absolute_value}")
                        feedback.pushInfo(
                            f"Normalization range: {collection.min_value} - {collection.max_value}"
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

                    if feedback:
                        feedback.pushInfo(f"Successfully created: {created_path}")
                else:
                    # Skip raster creation, just use the output path
                    created_path = output_path
                    log(
                        f"Skipped raster creation for {output_filename} (skip_raster=True)",
                        info=True,
                    )

                # Always save metadata file (even when skip_raster=True)
                if metadata_id:
                    try:
                        meta_path = save_constant_raster_metadata(
                            raster_path=created_path,
                            component_id=component.component_id,
                            component_name=component.alias_name
                            or component.component_id,
                            input_value=absolute_value,
                            normalized_value=constant_value,
                            output_min=collection.min_value,
                            output_max=collection.max_value,
                            metadata_id=metadata_id,
                            component_type=(
                                collection.component_type.value
                                if collection.component_type
                                else "unknown"
                            ),
                        )
                        if feedback:
                            feedback.pushInfo(f"Saved metadata: {meta_path}")
                        log(f"Saved metadata: {meta_path}", info=True)
                    except Exception as meta_error:
                        if feedback:
                            feedback.pushWarning(
                                f"Failed to save metadata: {str(meta_error)}"
                            )
                        log(f"Failed to save metadata: {str(meta_error)}", info=False)

                # Update component with raster path
                component.value_info.filename = created_path
                component.path = created_path

                created_rasters.append(created_path)

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


class ConstantRasterRegistry:
    """Registry for managing constant raster metadata and collections."""

    _metadata_store: typing.Dict[str, ConstantRasterMetadata] = {}
    _serializers: typing.Dict[str, typing.Callable] = {}
    _deserializers: typing.Dict[str, typing.Callable] = {}

    @classmethod
    def register_metadata(cls, metadata: ConstantRasterMetadata) -> bool:
        """Register constant raster metadata."""
        if metadata.id in cls._metadata_store:
            return False
        cls._metadata_store[metadata.id] = metadata
        return True

    @classmethod
    def metadata_ids(cls) -> typing.List[str]:
        """Get list of all registered metadata IDs."""
        return list(cls._metadata_store.keys())

    @classmethod
    def metadata_by_id(
        cls, metadata_identifier: str
    ) -> typing.Optional[ConstantRasterMetadata]:
        """Get metadata by its identifier."""
        return cls._metadata_store.get(metadata_identifier)

    @classmethod
    def metadata_by_component_type(
        cls, component_type: "ModelComponentType"
    ) -> typing.List[ConstantRasterMetadata]:
        """Get metadata filtered by component type."""
        from ..models.base import ModelComponentType

        result = []
        for metadata in cls._metadata_store.values():
            if metadata.component_type is not None:
                if metadata.component_type == component_type:
                    result.append(metadata)
                continue

            if not metadata.fcollection or not metadata.fcollection.components:
                continue

            for component in metadata.fcollection.components:
                if component.component_type == component_type:
                    result.append(metadata)
                    break

        return result

    @classmethod
    def collection_by_id(
        cls, metadata_id: str
    ) -> typing.Optional[ConstantRasterCollection]:
        """Get collection by metadata ID."""
        metadata = cls._metadata_store.get(metadata_id)
        if metadata:
            return metadata.fcollection
        return None

    @classmethod
    def collection_by_component_type(
        cls, component_type: "ModelComponentType"
    ) -> typing.List[ConstantRasterCollection]:
        """Get collections filtered by component type."""
        result = []
        for metadata in cls.metadata_by_component_type(component_type):
            if metadata.fcollection:
                result.append(metadata.fcollection)
        return result

    @classmethod
    def model_type_components(
        cls, model_identifier: str, component_type: "ModelComponentType"
    ) -> typing.List[ConstantRasterComponent]:
        """Get components for a specific model identifier and component type."""
        result = []
        for metadata in cls.metadata_by_component_type(component_type):
            if metadata.fcollection:
                component = metadata.fcollection.component_by_identifier(
                    model_identifier
                )
                if component:
                    result.append(component)
        return result

    @classmethod
    def pathway_components(
        cls, pathway_identifier: str
    ) -> typing.List[ConstantRasterComponent]:
        """Get all constant raster components for a specific pathway."""
        from ..models.base import ModelComponentType

        return cls.model_type_components(
            pathway_identifier, ModelComponentType.NCS_PATHWAY
        )

    @classmethod
    def activity_components(
        cls, activity_identifier: str
    ) -> typing.List[ConstantRasterComponent]:
        """Get all constant raster components for a specific activity."""
        from ..models.base import ModelComponentType

        return cls.model_type_components(
            activity_identifier, ModelComponentType.ACTIVITY
        )

    @classmethod
    def save(cls):
        """Save all registered metadata to settings."""
        from qgis.core import QgsSettings
        import json

        settings = QgsSettings()
        settings.beginGroup("cplus/constant_rasters")

        for metadata_id, metadata in cls._metadata_store.items():
            if metadata.fcollection:
                collection_data = {
                    "min_value": metadata.fcollection.min_value,
                    "max_value": metadata.fcollection.max_value,
                    "allowable_min": metadata.fcollection.allowable_min,
                    "allowable_max": metadata.fcollection.allowable_max,
                    "skip_raster": metadata.fcollection.skip_raster,
                    "components": [],
                }

                for component in metadata.fcollection.components:
                    absolute_value = (
                        component.value_info.absolute if component.value_info else 0.0
                    )
                    component_data = {
                        "component_id": component.component_id,
                        "absolute_value": absolute_value,
                        "skip_value": component.skip_value,
                        "alias_name": component.alias_name,
                    }
                    collection_data["components"].append(component_data)

                json_str = json.dumps(collection_data)
                settings.setValue(metadata_id, json_str)

        settings.endGroup()

    @classmethod
    def load(cls):
        """Load metadata from settings."""
        from qgis.core import QgsSettings
        import json

        settings = QgsSettings()
        settings.beginGroup("cplus/constant_rasters")

        for metadata_id in settings.childKeys():
            if metadata_id in cls._metadata_store:
                try:
                    json_str = settings.value(metadata_id, "{}")
                    collection_data = json.loads(json_str)
                    metadata = cls._metadata_store[metadata_id]

                    if metadata.fcollection and collection_data:
                        metadata.fcollection.min_value = collection_data.get(
                            "min_value", 0.0
                        )
                        metadata.fcollection.max_value = collection_data.get(
                            "max_value", 1.0
                        )
                        metadata.fcollection.allowable_min = collection_data.get(
                            "allowable_min", 0.0
                        )
                        metadata.fcollection.allowable_max = collection_data.get(
                            "allowable_max", 1.0
                        )
                        metadata.fcollection.skip_raster = collection_data.get(
                            "skip_raster", True
                        )

                        metadata.fcollection.components.clear()

                        components_data = collection_data.get("components", [])
                        for saved_component in components_data:
                            from ..models.constant_raster import (
                                ConstantRasterComponent,
                                ConstantRasterInfo,
                            )

                            component = ConstantRasterComponent(
                                value_info=ConstantRasterInfo(
                                    absolute=saved_component.get("absolute_value", 0.0)
                                ),
                                component=None,
                                component_id=saved_component.get("component_id", ""),
                                skip_value=saved_component.get("skip_value", False),
                                alias_name=saved_component.get("alias_name", ""),
                            )
                            metadata.fcollection.components.append(component)

                except Exception as e:
                    log(
                        f"Error loading constant raster state for {metadata_id}: {str(e)}",
                        info=False,
                    )

        settings.endGroup()

    @classmethod
    def __iter__(cls):
        """Make registry iterable over metadata objects."""
        return iter(cls._metadata_store.values())


# Global registry instance
constant_raster_registry = ConstantRasterRegistry
