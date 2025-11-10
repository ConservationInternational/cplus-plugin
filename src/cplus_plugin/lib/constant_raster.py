# -*- coding: utf-8 -*-
"""Processing utilities for constant rasters."""

import os
import typing
from datetime import datetime

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
    ConstantRasterInfo,
    ConstantRasterFileMetadata,
)
from ..models.base import ModelComponentType
from ..utils import log, tr
from ..conf import (
    settings_manager,
    save_constant_raster_collection,
    load_constant_raster_collection,
    get_all_constant_raster_metadata_ids,
)
from ..models.helpers import (
    get_constant_raster_dir,
    generate_constant_raster_filename,
    save_constant_raster_metadata,
    constant_raster_collection_to_dict,
    constant_raster_collection_from_dict,
)
from ..definitions.constants import (
    COMPONENT_ID_ATTRIBUTE,
    COMPONENT_UUID_ATTRIBUTE,
    SKIP_RASTER_ATTRIBUTE,
    ENABLED_ATTRIBUTE,
    ABSOLUTE_VALUE_ATTRIBUTE,
    COMPONENTS_ATTRIBUTE,
    MIN_VALUE_ATTRIBUTE_KEY,
    MAX_VALUE_ATTRIBUTE_KEY,
    ALLOWABLE_MIN_ATTRIBUTE,
    ALLOWABLE_MAX_ATTRIBUTE,
    LAST_UPDATED_ATTRIBUTE,
    PATH_ATTRIBUTE,
)


class ConstantRasterProcessingUtils:
    """Utilities for constant raster processing.

    This class provides methods for creating and processing
    constant rasters according to the CPLUS framework requirements.
    """

    @staticmethod
    def create_constant_raster(
        value: float,
        raster_context: ConstantRasterContext,
        output_path: str,
        processing_context: typing.Optional[QgsProcessingContext] = None,
        feedback: typing.Optional[QgsProcessingFeedback] = None,
    ) -> str:
        """Create a constant raster with a specified value.

        Uses the same pattern as NPV PWL creation in lib/financials.py.
        Creates a raster where all pixels have the same constant value.

        :param value: Constant value for all pixels in the raster
        :param raster_context: ConstantRasterContext with extent, CRS, pixel size, etc.
        :param output_path: Path for output raster
        :param processing_context: QGIS processing context (optional)
        :param feedback: Optional feedback for progress reporting
        :returns: Path to created raster
        :raises QgsProcessingException: If creation fails
        """
        # Extract parameters from context
        extent = raster_context.extent
        pixel_size = raster_context.pixel_size
        crs = raster_context.crs

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
        if processing_context is None:
            processing_context = QgsProcessingContext()

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
                context=processing_context,
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
            PATH_ATTRIBUTE: raster_path,
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
        2. Remap to normalization range using collection's min_value/max_value

        :param collection: ConstantRasterCollection containing components to process
        :param context: ConstantRasterContext with extent, CRS, and output settings
        :param input_range: DEPRECATED - min/max are now calculated from actual component values
        :param feedback: Optional feedback for progress reporting
        :param metadata_id: Metadata ID for determining file naming (e.g., "years_experience_activity")
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

        # STEP 1: Use input_range for normalization
        # input_range defines the theoretical range (e.g., 0-100 years)
        input_min, input_max = input_range

        if feedback:
            feedback.pushInfo(
                f"Input range for normalization: min={input_min}, max={input_max}"
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

        # Create timestamped session folder for this raster creation session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(actual_output_dir, timestamp)
        os.makedirs(session_dir, exist_ok=True)
        if feedback:
            feedback.pushInfo(f"Created session directory: {session_dir}")

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
                component_name = (
                    component.component.name
                    if component.component and hasattr(component.component, "name")
                    else component.component_id
                )
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
                    f"Normalization range: {collection.min_value} - {collection.max_value}"
                )

            # TWO-STEP NORMALIZATION:

            # Step 1: Normalize input value to [0,1] using input_range
            if input_max != input_min:
                normalized_0_1 = (absolute_value - input_min) / (input_max - input_min)
            else:
                # Edge case: input range is zero (min == max), skip this component
                if feedback:
                    feedback.pushWarning(
                        f"Skipping component {component.component_id}: input range is zero (min == max)"
                    )
                continue

            if feedback:
                feedback.pushInfo(f"Step 1 - Normalized to [0,1]: {normalized_0_1}")

            # Step 2: Remap [0,1] to user-specified normalization range
            output_min = collection.min_value
            output_max = collection.max_value
            constant_value = output_min + (normalized_0_1 * (output_max - output_min))

            if feedback:
                feedback.pushInfo(
                    f"Step 2 - Remapped to normalization range: {constant_value}"
                )
                feedback.pushInfo(f"Final raster value: {constant_value}")

            # Generate output filename using helper
            component_name = (
                component.component.name
                if component.component and hasattr(component.component, "name")
                else component.component_id
            )
            if metadata_id and component_name:
                # Use descriptive filename with value and unit
                output_filename = generate_constant_raster_filename(
                    component_name, absolute_value, metadata_id
                )
            else:
                # Fallback to old naming scheme
                safe_name = component_name.replace(" ", "_").replace("/", "_")
                output_filename = f"constant_raster_{safe_name}.tif"

            output_path = os.path.join(session_dir, output_filename)

            try:
                # Create the constant raster only if skip_raster is False
                if not collection.skip_raster:
                    if feedback:
                        component_name = (
                            component.component.name
                            if component.component
                            and hasattr(component.component, "name")
                            else component.component_id
                        )
                        feedback.pushInfo(f"Component: {component_name}")
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
                        raster_context=context,
                        output_path=output_path,
                        processing_context=processing_context,
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
                        component_name = (
                            component.component.name
                            if component.component
                            and hasattr(component.component, "name")
                            else component.component_id
                        )

                        # Create metadata object
                        file_metadata = ConstantRasterFileMetadata(
                            raster_path="" if collection.skip_raster else created_path,
                            component_id=component.component_id,
                            component_name=component_name,
                            component_type=(
                                collection.component_type.value
                                if collection.component_type
                                else "unknown"
                            ),
                            input_value=absolute_value,
                            normalized_value=constant_value,
                            output_min=collection.min_value,
                            output_max=collection.max_value,
                            metadata_id=metadata_id,
                        )

                        meta_path = save_constant_raster_metadata(
                            file_metadata, session_dir
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
                # Note: value_info only stores normalized/absolute values
                # File path stored at component level
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

    def __init__(self):
        """Initialize the registry with empty stores."""
        self._metadata_store: typing.Dict[str, ConstantRasterMetadata] = {}

    def add_metadata(self, metadata: ConstantRasterMetadata) -> bool:
        """Add constant raster metadata to the registry.

        :param metadata: ConstantRasterMetadata to add
        :returns: True if added successfully, False if metadata with same ID already exists
        """
        if metadata.id in self._metadata_store:
            return False
        self._metadata_store[metadata.id] = metadata
        return True

    def metadata_ids(self) -> typing.List[str]:
        """Get list of all registered metadata IDs."""
        return list(self._metadata_store.keys())

    def metadata_by_id(
        self, metadata_identifier: str
    ) -> typing.Optional[ConstantRasterMetadata]:
        """Get metadata by its identifier.

        :param metadata_identifier: Identifier for the metadata to retrieve
        :returns: ConstantRasterMetadata if found, None otherwise
        """
        try:
            return self._metadata_store.get(metadata_identifier)
        except Exception as e:
            log(
                f"Error retrieving metadata by ID '{metadata_identifier}': {str(e)}",
                info=False,
            )
            return None

    def metadata_by_component_type(
        self, component_type: "ModelComponentType"
    ) -> typing.List[ConstantRasterMetadata]:
        """Get metadata filtered by component type."""

        result = []
        for metadata in self._metadata_store.values():
            if metadata.component_type is not None:
                if metadata.component_type == component_type:
                    result.append(metadata)
                continue

            if (
                not metadata.raster_collection
                or not metadata.raster_collection.components
            ):
                continue

            for component in metadata.raster_collection.components:
                if component.component_type == component_type:
                    result.append(metadata)
                    break

        return result

    def collection_by_id(
        self, metadata_id: str
    ) -> typing.Optional[ConstantRasterCollection]:
        """Get collection by metadata ID."""
        metadata = self._metadata_store.get(metadata_id)
        if metadata:
            return metadata.raster_collection
        return None

    def collection_by_component_type(
        self, component_type: "ModelComponentType"
    ) -> typing.List[ConstantRasterCollection]:
        """Get collections filtered by component type."""
        return [
            metadata.raster_collection
            for metadata in self.metadata_by_component_type(component_type)
            if metadata.raster_collection
        ]

    def model_type_components(
        self, model_identifier: str, component_type: "ModelComponentType"
    ) -> typing.List[ConstantRasterComponent]:
        """Get components for a specific model identifier and component type."""
        result = []
        for metadata in self.metadata_by_component_type(component_type):
            if metadata.raster_collection:
                component = metadata.raster_collection.component_by_identifier(
                    model_identifier
                )
                if component:
                    result.append(component)
        return result

    def activity_components(
        self, activity_identifier: str
    ) -> typing.List[ConstantRasterComponent]:
        """Get all constant raster components for a specific activity."""
        return self.model_type_components(
            activity_identifier, ModelComponentType.ACTIVITY
        )

    def save(self):
        """Save all registered metadata to settings.

        Uses metadata.serializer if provided, otherwise uses default serializer.
        """
        for metadata_id, metadata in self._metadata_store.items():
            if metadata.raster_collection:
                # Use custom serializer if provided, otherwise use default
                if metadata.serializer:
                    collection_data = metadata.serializer(metadata.raster_collection)
                else:
                    collection_data = constant_raster_collection_to_dict(
                        metadata.raster_collection
                    )

                save_constant_raster_collection(metadata_id, collection_data)

    def load(self):
        """Load metadata from settings.

        Uses metadata.deserializer if provided, otherwise uses default deserializer.
        """
        for metadata_id in get_all_constant_raster_metadata_ids():
            if metadata_id in self._metadata_store:
                try:
                    collection_data = load_constant_raster_collection(metadata_id)
                    if not collection_data:
                        continue

                    metadata = self._metadata_store[metadata_id]

                    if metadata.raster_collection is not None:
                        # Get all activities for reference
                        model_components = settings_manager.get_all_activities()

                        # Use custom deserializer if provided, otherwise use default
                        if metadata.deserializer:
                            loaded_collection = metadata.deserializer(
                                collection_data, model_components
                            )
                        else:
                            loaded_collection = constant_raster_collection_from_dict(
                                collection_data, model_components
                            )

                        if loaded_collection:
                            # Copy values to existing collection
                            metadata.raster_collection.min_value = (
                                loaded_collection.min_value
                            )
                            metadata.raster_collection.max_value = (
                                loaded_collection.max_value
                            )
                            metadata.raster_collection.allowable_min = (
                                loaded_collection.allowable_min
                            )
                            metadata.raster_collection.allowable_max = (
                                loaded_collection.allowable_max
                            )
                            metadata.raster_collection.skip_raster = (
                                loaded_collection.skip_raster
                            )
                            metadata.raster_collection.last_updated = (
                                loaded_collection.last_updated
                            )
                            metadata.raster_collection.components = (
                                loaded_collection.components
                            )

                            # Store saved UUIDs for later population
                            components_data = collection_data.get(
                                COMPONENTS_ATTRIBUTE, []
                            )
                            for idx, saved_component in enumerate(components_data):
                                if idx < len(metadata.raster_collection.components):
                                    component = metadata.raster_collection.components[
                                        idx
                                    ]
                                    saved_uuid = saved_component.get(
                                        COMPONENT_UUID_ATTRIBUTE
                                    ) or saved_component.get(COMPONENT_ID_ATTRIBUTE)
                                    if saved_uuid:
                                        component._saved_component_uuid = saved_uuid

                except Exception as e:
                    log(
                        f"Error loading constant raster state for {metadata_id}: {str(e)}",
                        info=False,
                    )

    def remove_metadata(self, metadata_id: str) -> bool:
        """Remove metadata from the registry.

        :param metadata_id: ID of the metadata to remove
        :returns: True if removed successfully, False if not found
        """
        if metadata_id in self._metadata_store:
            del self._metadata_store[metadata_id]
            return True
        return False

    def items(self) -> typing.List[ConstantRasterMetadata]:
        """Get list of all registered metadata items.

        :returns: List of ConstantRasterMetadata objects
        """
        return list(self._metadata_store.values())

    def __len__(self) -> int:
        """Return the number of registered metadata items."""
        return len(self._metadata_store)

    def __iter__(self):
        """Make registry iterable over metadata objects."""
        return iter(self._metadata_store.values())


# Global registry instance (singleton)
constant_raster_registry = ConstantRasterRegistry()
