# -*- coding: utf-8 -*-
"""Processing utilities for constant rasters."""

import json
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
from ..utils import (
    get_constant_raster_dir,
    generate_constant_raster_filename,
    save_constant_raster_metadata,
    log,
    tr,
)
from ..conf import settings_manager, Settings
from ..models.helpers import (
    constant_raster_metadata_from_dict,
    constant_raster_metadata_to_dict,
)
from ..definitions.constants import (
    COMPONENT_ID_ATTRIBUTE,
    COMPONENT_UUID_ATTRIBUTE,
    COMPONENTS_ATTRIBUTE,
    ID_ATTRIBUTE,
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
            feedback.pushInfo(
                f"Data range for normalization: {collection.min_value} - {collection.max_value}"
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
                feedback.pushInfo(
                    f"Data range: {collection.min_value} - {collection.max_value}"
                )

            # Normalize to 0-1 scale using collection's data range
            data_range = collection.max_value - collection.min_value
            if data_range <= 0:
                # Single value case: min=0, max=value, result=1.0
                if collection.max_value > 0:
                    normalized_value = 1.0
                    if feedback:
                        feedback.pushInfo(f"Single value: treated as maximum (1.0)")
                else:
                    if feedback:
                        feedback.pushWarning(
                            f"Skipping component {component.component_id}: invalid data range"
                        )
                    continue
            else:
                normalized_value = (absolute_value - collection.min_value) / data_range

            if feedback:
                feedback.pushInfo(f"Normalized value (0-1): {normalized_value}")

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
                        feedback.pushInfo(f"Normalized value: {normalized_value}")
                        feedback.pushInfo(
                            f"Creating raster with value {normalized_value} at {output_path}"
                        )

                    created_path = ConstantRasterProcessingUtils.create_constant_raster(
                        value=normalized_value,
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
                            normalized_value=normalized_value,
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
        self._custom_type_definitions: typing.List[dict] = []

        # We keep track of known serializer/deserializer pairs by
        # metadata id so we can reconstruct collections during load
        self._serializers: typing.Dict[str, typing.Callable] = {}
        self._deserializers: typing.Dict[str, typing.Callable] = {}

    def add_metadata(self, metadata: ConstantRasterMetadata) -> bool:
        """Add constant raster metadata to the registry.

        :param metadata: ConstantRasterMetadata to add
        :returns: True if added successfully, False if metadata with same ID already exists
        """
        if metadata.id in self._metadata_store:
            return False

        self._metadata_store[metadata.id] = metadata

        # Register serializer/deserializer references for reconstruction
        if metadata.serializer:
            self._serializers[metadata.id] = metadata.serializer
        if metadata.deserializer:
            self._deserializers[metadata.id] = metadata.deserializer
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
        if metadata_identifier not in self._metadata_store:
            return None

        return self._metadata_store.get(metadata_identifier)

    def has_metadata(self, metadata_id: str) -> bool:
        """Check if the registry has a metadata item with the given identifier.

        :param metadata_id: Identifier of the metadata item.
        :type metadata_id: str

        :returns: True if the metadata exists in the collection else False.
        :rtype: bool
        """
        return True if self.metadata_by_id(metadata_id) else False

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

    def add_custom_type_definition(self, type_def: dict) -> bool:
        """Add a custom type definition to the registry.

        :param type_def: Dictionary with custom type definition (id, name, min_value, max_value, etc.)
        :returns: True if added successfully, False if already exists
        """
        # Check if already exists
        if any(
            t.get("id") == type_def.get("id") for t in self._custom_type_definitions
        ):
            return False
        self._custom_type_definitions.append(type_def)
        return True

    def remove_custom_type_definition(self, type_id: str) -> bool:
        """Remove a custom type definition from the registry.

        :param type_id: ID of the custom type to remove
        :returns: True if removed, False if not found
        """
        for i, type_def in enumerate(self._custom_type_definitions):
            if type_def.get("id") == type_id:
                self._custom_type_definitions.pop(i)
                return True
        return False

    def get_custom_type_definitions(self) -> typing.List[dict]:
        """Get all custom type definitions.

        :returns: List of custom type definition dictionaries
        """
        return self._custom_type_definitions.copy()

    def get_custom_type_definition(self, type_id: str) -> typing.Optional[dict]:
        """Get a specific custom type definition by ID.

        :param type_id: ID of the custom type
        :returns: Custom type definition dictionary, or None if not found
        """
        for type_def in self._custom_type_definitions:
            if type_def.get("id") == type_id:
                return type_def.copy()
        return None

    def update_custom_type_definition(self, type_id: str, updated_def: dict) -> bool:
        """Update a custom type definition.

        :param type_id: ID of the custom type to update
        :param updated_def: Dictionary with updated values
        :returns: True if updated, False if not found
        """
        for i, type_def in enumerate(self._custom_type_definitions):
            if type_def.get("id") == type_id:
                self._custom_type_definitions[i] = updated_def
                return True
        return False

    def save(self):
        """Save all registered metadata to settings.

        Uses metadata.serializer if provided, otherwise uses default serializer.
        Also saves custom type definitions.
        """
        metadata_collection = []
        for metadata_id, metadata in self._metadata_store.items():
            # choose serializer - registered one first, then metadata-level one
            serializer = self._serializers.get(metadata_id) or getattr(
                metadata, "serializer", None
            )
            if metadata.raster_collection is not None and serializer:
                metadata_dict = constant_raster_metadata_to_dict(metadata, serializer)
                metadata_collection.append(metadata_dict)

        # Save collection
        settings_manager.set_value(
            Settings.CONSTANT_RASTER_METADATA_REGISTRY, json.dumps(metadata_collection)
        )

        # Save custom type definitions
        settings_manager.save_custom_constant_raster_types(
            self._custom_type_definitions
        )

    def load(self):
        """Load metadata from settings.

        Uses metadata.deserializer if provided, otherwise uses default deserializer.
        Also loads custom type definitions.
        """
        self._metadata_store = {}
        self._custom_type_definitions = []

        metadata_registry = settings_manager.get_value(
            Settings.CONSTANT_RASTER_METADATA_REGISTRY
        )
        metadata_collection = json.loads(metadata_registry) if metadata_registry else []

        activities = settings_manager.get_all_activities()

        for metadata_dict in metadata_collection:
            metadata_id = metadata_dict.get(ID_ATTRIBUTE)
            if not metadata_id:
                log("Skipping metadata entry with no id.", info=False)
                continue

            # Prefer registry-registered deserializer, fall back to None
            deserializer = self._deserializers.get(metadata_id)
            serializer = self._serializers.get(metadata_id)
            metadata = None
            try:
                metadata = constant_raster_metadata_from_dict(
                    metadata_dict, deserializer, activities
                )
            except Exception as exc:
                log(
                    f"Failed to create metadata object from dict for id={metadata_id}: {exc}",
                    info=False,
                )
                continue

            if metadata is None:
                log(
                    f"Constant raster metadata is None for id={metadata_id}", info=False
                )
                continue

            # Patch serializers
            metadata.deserializer = deserializer
            metadata.serializer = serializer

            self.add_metadata(metadata)

            # Ensure registry maps are consistent with metadata object
            if getattr(metadata, "serializer", None):
                self._serializers[metadata_id] = metadata.serializer
            if getattr(metadata, "deserializer", None):
                self._deserializers[metadata_id] = metadata.deserializer

        # Load custom type definitions
        self._custom_type_definitions = (
            settings_manager.load_custom_constant_raster_types()
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

    def register_serializers(
        self,
        metadata_id: str,
        serializer: typing.Callable,
        deserializer: typing.Callable,
    ):
        """Register serializer/deserializer pair for the given metadata id.

        Useful when your plugin registers built-in types: call this after creating the metadata
        so load() can reconstruct them in future runs.

        :param metadata_id: Metadata ID for the callables to be registered.
        :type metadata_id: str

        :param serializer: Callable function for serializing to a dictionary.
        :type serializer: typing.Callable

        :param deserializer: Callable function for deserializing from a dictionary.
        :type deserializer: typing.Callable
        """
        if serializer:
            self._serializers[metadata_id] = serializer
        if deserializer:
            self._deserializers[metadata_id] = deserializer

    def serializers_from_metadata(self, metadata: ConstantRasterMetadata):
        """Registers serializer and deserializer pair from the metadata.

        :param metadata: Metadata object to extract serializer and
        deserializer functions.
        :type metadata: ConstantRasterMetadata
        """
        if metadata.serializer and metadata.deserializer:
            self.register_serializers(
                metadata.id, metadata.serializer, metadata.deserializer
            )

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


# Global registry instance
constant_raster_registry = ConstantRasterRegistry()
