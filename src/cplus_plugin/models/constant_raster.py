# -*- coding: utf-8 -*-
"""Models for Constant Raster according to architectural specification."""

from __future__ import annotations
import dataclasses
import typing
from qgis.core import QgsRasterLayer, QgsProcessingFeedback

from .base import LayerModelComponent, ModelComponentType, PriorityLayerType
from ..definitions.constants import (
    NCS_PATHWAY_IDENTIFIER_PROPERTY,
    ENABLED_ATTRIBUTE,
    PATH_ATTRIBUTE,
)


@dataclasses.dataclass
class ConstantRasterInfo:
    """Basic information about a constant raster.

    This can be extended depending on the requirements of capturing
    information related to the management of the constant raster.
    """

    filename: str = ""
    layer: str = ""  # Layer name or identifier
    normalized: bool = False
    absolute: float = 0.0  # Absolute constant value for creating rasters

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "filename": self.filename,
            "layer": self.layer,
            "normalized": self.normalized,
            "absolute": self.absolute,
        }

    @staticmethod
    def from_dict(d: dict) -> "ConstantRasterInfo":
        """Deserialize from dictionary."""
        return ConstantRasterInfo(
            filename=d.get("filename", ""),
            layer=d.get("layer", ""),
            normalized=bool(d.get("normalized", False)),
            absolute=float(d.get("absolute", 0.0)),
        )


@dataclasses.dataclass
class ConstantRasterComponent:
    """Individual constant raster with layer model component associations.

    This class links the ConstantRasterInfo with the specific layer model
    component (NcsPathway or Activity). Already defined in cplus.models,
    an Activity or NcsPathway can be associated with a ConstantRasterComponent.
    Activities are stored by calling their type.
    """

    value_info: ConstantRasterInfo
    component: LayerModelComponent  # Either NcsPathway or Activity
    uuids: str = ""
    alias_name: str = ""
    path: str = ""  # Note: Returns False for components (not a file path)
    skip_value: bool = False
    component_id: str = ""
    component_type: ModelComponentType = ModelComponentType.UNKNOWN
    qgis_map_layer: typing.Optional[QgsRasterLayer] = None

    def _identifier_by_id(self) -> str:
        """Generate unique identifier by concatenating component identifiers.

        For example, if an activity has name "Climate Project" and a pathway
        has name "Pilot Planting", the concatenated name becomes
        "Climate Project Pilot Planting" (suffix pattern for naming).
        """
        if self.component:
            base_name = getattr(self.component, 'name', '')
            if self.alias_name:
                return f"{base_name} {self.alias_name}"
            return base_name
        return self.alias_name or self.uuids

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "value_info": self.value_info.to_dict() if self.value_info else {},
            "component_uuid": str(self.component.uuid) if self.component else "",
            "uuids": self.uuids,
            "alias_name": self.alias_name,
            PATH_ATTRIBUTE: self.path,
            "skip_value": self.skip_value,
            "component_id": self.component_id,
            "component_type": self.component_type.value if self.component_type else ModelComponentType.UNKNOWN.value,
        }

    @staticmethod
    def from_dict(
        d: dict,
        component_lookup: typing.Callable[[str], LayerModelComponent]
    ) -> "ConstantRasterComponent":
        """Deserialize from dictionary.

        :param d: Dictionary data
        :param component_lookup: Function to retrieve component by UUID
        :returns: ConstantRasterComponent instance
        """
        component = None
        component_uuid = d.get("component_uuid")
        if component_uuid:
            component = component_lookup(component_uuid)

        value_info_data = d.get("value_info", {})
        value_info = ConstantRasterInfo.from_dict(value_info_data) if value_info_data else ConstantRasterInfo()

        component_type_str = d.get("component_type", ModelComponentType.UNKNOWN.value)
        component_type = ModelComponentType.from_string(component_type_str)

        return ConstantRasterComponent(
            value_info=value_info,
            component=component,
            uuids=d.get("uuids", ""),
            alias_name=d.get("alias_name", ""),
            path=d.get(PATH_ATTRIBUTE, ""),
            skip_value=bool(d.get("skip_value", False)),
            component_id=d.get("component_id", ""),
            component_type=component_type,
        )


@dataclasses.dataclass
class ConstantRasterCollection:
    """Manages multiple ConstantRasterComponents.

    With a maker, this provides the option of skipping the creation
    of the constant raster collectively for all items in a collection
    or at a more granular level (ConstantRasterComponent). If skip_realer
    is True then the "path" attribute will always return False.
    """

    filter_value: float = 0.0
    total_value: float = 1.0
    components: typing.List[ConstantRasterComponent] = dataclasses.field(default_factory=list)
    skip_raster: bool = False  # skip_realer option from diagram

    def enabled_components(self) -> typing.List[ConstantRasterComponent]:
        """Get components that are enabled (not skipped)."""
        return [c for c in self.components if not c.skip_value]

    def component_by_id(self, component_id: str) -> typing.Optional[ConstantRasterComponent]:
        """Get component by its component ID (UUID).

        :param component_id: UUID of the component to retrieve
        :returns: ConstantRasterComponent if found, None otherwise
        """
        for component in self.components:
            if component.component_id == component_id:
                return component
            # Also check the component's UUID if available
            if component.component and str(component.component.uuid) == component_id:
                return component
        return None

    def normalize(self) -> None:
        """Normalize the collection by updating min/max values based on components.

        This method analyzes all enabled components and updates filter_value
        (minimum) and total_value (maximum) based on the absolute values
        in the component value_info objects.
        """
        enabled = self.enabled_components()
        if not enabled:
            return

        # Get all absolute values from enabled components
        values = [c.value_info.absolute for c in enabled if c.value_info]
        if not values:
            return

        # Update min/max
        self.filter_value = min(values)
        self.total_value = max(values)

    def validate(self) -> None:
        """Validate the collection configuration."""
        if self.total_value == self.filter_value:
            raise ValueError("filter_value and total_value must differ.")

        for component in self.components:
            if not component.value_info:
                raise ValueError(f"Component {component.component_id} missing value_info.")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "filter_value": float(self.filter_value),
            "total_value": float(self.total_value),
            "skip_raster": bool(self.skip_raster),
            "components": [c.to_dict() for c in self.components],
        }

    @staticmethod
    def from_dict(
        d: dict,
        component_lookup: typing.Callable[[str], LayerModelComponent]
    ) -> "ConstantRasterCollection":
        """Deserialize from dictionary.

        :param d: Dictionary data
        :param component_lookup: Function to retrieve component by UUID
        :returns: ConstantRasterCollection instance
        """
        components_data = d.get("components", [])
        components = [
            ConstantRasterComponent.from_dict(comp_dict, component_lookup)
            for comp_dict in components_data
        ]

        return ConstantRasterCollection(
            filter_value=float(d.get("filter_value", 0.0)),
            total_value=float(d.get("total_value", 1.0)),
            skip_raster=bool(d.get("skip_raster", False)),
            components=components,
        )


@dataclasses.dataclass
class ConstantRasterConfig:
    """Configuration for creating constant rasters in QGIS.

    Basic information for creating a constant raster in QGIS.
    """

    component: ConstantRasterComponent
    value: str = ""
    extent: typing.Any = None  # Could be QgsRectangle
    resolution: typing.Any = None  # Could be float or tuple
    base_dir: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "component": self.component.to_dict() if self.component else {},
            "value": self.value,
            "extent": str(self.extent) if self.extent else "",
            "resolution": str(self.resolution) if self.resolution else "",
            "base_dir": self.base_dir,
        }


@dataclasses.dataclass
class ConstantRasterContext:
    """Context for creating constant rasters.

    Provides configuration for the raster creation process including
    extent, resolution, CRS, and output directory.
    """

    extent: typing.Any = None  # QgsRectangle
    pixel_size: float = 30.0  # Default pixel size in map units
    crs: typing.Any = None  # QgsCoordinateReferenceSystem
    output_dir: str = ""  # Output directory for created rasters

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "extent": str(self.extent) if self.extent else "",
            "pixel_size": self.pixel_size,
            "crs": str(self.crs.authid()) if self.crs else "",
            "output_dir": self.output_dir,
        }


@dataclasses.dataclass
class ConstantRasterMetadata:
    """Metadata for constant rasters.

    Stores metadata including the deserializer callable (PyFunc).
    """

    id: str = ""
    display_name: str = ""
    fcollection: typing.Optional[ConstantRasterCollection] = None
    deserializer: typing.Optional[typing.Callable] = None  # PyFunc
    component_type: typing.Optional["ModelComponentType"] = None  # Type this metadata applies to
    input_range: typing.Tuple[float, float] = (0.0, 100.0)  # Min and max for input values (e.g., 0-100 years)

    def to_dict(self) -> dict:
        """Serialize to dictionary (excluding deserializer)."""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "fcollection": self.fcollection.to_dict() if self.fcollection else {},
            "component_type": self.component_type.value if self.component_type else None,
            "input_range": list(self.input_range),
        }


class ConstantRasterRegistry:
    """Registry for managing constant raster metadata and collections.

    The serializer and deserializer are callables which define how
    the ConstantRasterCollection will be loaded and saved in the
    settings by the ConstantRasterRegistry when load() and 'save'
    are called respectively. There will be a default implementation
    provided via cplus.models.helpers; however if the plugin uses
    a subclassed ConstantRasterCollection then there might be a
    need to specify custom (de)serializers.
    """

    _metadata_store: typing.Dict[str, ConstantRasterMetadata] = {}
    _serializers: typing.Dict[str, typing.Callable] = {}
    _deserializers: typing.Dict[str, typing.Callable] = {}

    @classmethod
    def register_metadata(cls, metadata: ConstantRasterMetadata) -> bool:
        """Register constant raster metadata.

        :param metadata: Metadata object to register
        :returns: True if registered successfully, False if ID already exists
        """
        if metadata.id in cls._metadata_store:
            return False

        cls._metadata_store[metadata.id] = metadata
        return True

    @classmethod
    def register_serializer(cls, collection_type: str, serializer: typing.Callable):
        """Register a custom serializer for a collection type.

        :param collection_type: Type identifier for the collection
        :param serializer: Callable that serializes the collection
        """
        cls._serializers[collection_type] = serializer

    @classmethod
    def register_deserializer(cls, collection_type: str, deserializer: typing.Callable):
        """Register a custom deserializer for a collection type.

        :param collection_type: Type identifier for the collection
        :param deserializer: Callable that deserializes the collection
        """
        cls._deserializers[collection_type] = deserializer

    @classmethod
    def get_serializer(cls, collection_type: str) -> typing.Optional[typing.Callable]:
        """Get registered serializer for a collection type."""
        return cls._serializers.get(collection_type)

    @classmethod
    def get_deserializer(cls, collection_type: str) -> typing.Optional[typing.Callable]:
        """Get registered deserializer for a collection type."""
        return cls._deserializers.get(collection_type)

    @classmethod
    def metadata_ids(cls) -> typing.List[str]:
        """Get list of all registered metadata IDs.

        :returns: List of metadata IDs
        """
        return list(cls._metadata_store.keys())

    @classmethod
    def metadata_by_component_type(
        cls, component_type: "ModelComponentType"
    ) -> typing.List[ConstantRasterMetadata]:
        """Get metadata filtered by component type.

        :param component_type: Type of component (NCS_PATHWAY or ACTIVITY)
        :returns: List of metadata objects for the specified component type
        """
        from .base import ModelComponentType

        result = []
        for metadata in cls._metadata_store.values():
            # First check if metadata has a component_type field
            if metadata.component_type is not None:
                if metadata.component_type == component_type:
                    result.append(metadata)
                continue

            # Fallback: check components in the collection
            if not metadata.fcollection or not metadata.fcollection.components:
                continue

            # Check if any component matches the type
            for component in metadata.fcollection.components:
                if component.component_type == component_type:
                    result.append(metadata)
                    break

        return result

    @classmethod
    def collection_by_id(cls, metadata_id: str) -> typing.Optional[ConstantRasterCollection]:
        """Get collection by metadata ID.

        :param metadata_id: ID of the metadata
        :returns: ConstantRasterCollection if found, None otherwise
        """
        metadata = cls._metadata_store.get(metadata_id)
        if metadata:
            return metadata.fcollection
        return None

    @classmethod
    def save(cls):
        """Save all registered metadata to settings.

        This method persists the state of all collections (component values,
        output ranges, etc.) to QgsSettings so they can be restored later.
        """
        from qgis.core import QgsSettings
        import json
        from ..utils import log

        settings = QgsSettings()
        settings.beginGroup("cplus/constant_rasters")

        log(f"Saving constant raster state for {len(cls._metadata_store)} metadata items", info=True)

        # Save each metadata's collection state
        for metadata_id, metadata in cls._metadata_store.items():
            if metadata.fcollection:
                collection_data = {
                    'filter_value': metadata.fcollection.filter_value,
                    'total_value': metadata.fcollection.total_value,
                    'skip_raster': metadata.fcollection.skip_raster,
                    'components': []
                }

                log(f"Saving {metadata_id}: {len(metadata.fcollection.components)} components", info=True)

                # Save each component
                for component in metadata.fcollection.components:
                    absolute_value = component.value_info.absolute if component.value_info else 0.0
                    component_data = {
                        'component_id': component.component_id,
                        'absolute_value': absolute_value,
                        'skip_value': component.skip_value,
                        'alias_name': component.alias_name,
                    }
                    collection_data['components'].append(component_data)

                    log(f"  Component {component.component_id} ({component.alias_name}): value={absolute_value}, skip={component.skip_value}", info=True)

                # Store as JSON string
                json_str = json.dumps(collection_data)
                settings.setValue(metadata_id, json_str)
                log(f"Saved {metadata_id}: {json_str}", info=True)

        settings.endGroup()
        log("Constant raster state save completed", info=True)

    @classmethod
    def load(cls):
        """Load metadata from settings.

        This method restores the state of all collections from QgsSettings,
        including component values and output ranges.
        """
        from qgis.core import QgsSettings
        import json
        from ..utils import log

        settings = QgsSettings()
        settings.beginGroup("cplus/constant_rasters")

        log(f"Loading constant raster state from settings. Keys: {settings.childKeys()}", info=True)

        # Load each metadata's collection state
        for metadata_id in settings.childKeys():
            if metadata_id in cls._metadata_store:
                try:
                    json_str = settings.value(metadata_id, "{}")
                    log(f"Loading {metadata_id}: {json_str}", info=True)

                    collection_data = json.loads(json_str)
                    metadata = cls._metadata_store[metadata_id]

                    if metadata.fcollection and collection_data:
                        # Restore collection properties
                        metadata.fcollection.filter_value = collection_data.get('filter_value', 0.0)
                        metadata.fcollection.total_value = collection_data.get('total_value', 1.0)
                        metadata.fcollection.skip_raster = collection_data.get('skip_raster', False)

                        log(f"Restored collection properties: filter={metadata.fcollection.filter_value}, total={metadata.fcollection.total_value}", info=True)

                        # Clear existing components and restore from saved data
                        metadata.fcollection.components.clear()

                        # Recreate components from saved data
                        components_data = collection_data.get('components', [])
                        log(f"Restoring {len(components_data)} components", info=True)

                        for saved_component in components_data:
                            absolute_value = saved_component.get('absolute_value', 0.0)
                            component_id = saved_component.get('component_id', '')

                            log(f"Restoring component {component_id} with value {absolute_value}", info=True)

                            # Create a minimal component to hold the saved state
                            # The full component will be populated when the dialog loads
                            component = ConstantRasterComponent(
                                value_info=ConstantRasterInfo(absolute=absolute_value),
                                component=None,  # Will be set by dialog
                                component_id=component_id,
                                skip_value=saved_component.get('skip_value', False),
                                alias_name=saved_component.get('alias_name', ''),
                            )
                            metadata.fcollection.components.append(component)

                        log(f"Loaded {len(metadata.fcollection.components)} components into collection", info=True)

                except Exception as e:
                    # Log error but don't crash
                    log(f"Error loading constant raster state for {metadata_id}: {str(e)}", info=False)

        settings.endGroup()

    @classmethod
    def __iter__(cls):
        """Make registry iterable over metadata objects."""
        return iter(cls._metadata_store.values())

    @staticmethod
    def create_constant_raster_metadata_collection(
        collection: ConstantRasterCollection,
        config: ConstantRasterConfig,
        feedback: typing.Optional[QgsProcessingFeedback] = None
    ) -> ConstantRasterMetadata:
        """Create constant raster metadata from collection and config.

        This method processes the collection and creates metadata.
        The actual raster processing is delegated to ConstantRasterProcessingUtils.

        :param collection: ConstantRasterCollection to process
        :param config: Configuration for raster creation
        :param feedback: Optional feedback for progress reporting
        :returns: ConstantRasterMetadata with processed information
        """
        # This will be implemented in conjunction with ConstantRasterProcessingUtils
        metadata = ConstantRasterMetadata(
            id=f"constant_raster_{id(collection)}",
            display_name="Constant Raster Collection",
            fcollection=collection,
        )

        if feedback:
            feedback.pushInfo("Creating constant raster metadata collection")

        # Processing logic will be added when ConstantRasterProcessingUtils is implemented

        return metadata

    @classmethod
    def remove_metadata(cls, metadata_id: str) -> bool:
        """Remove metadata by ID.

        :param metadata_id: ID of metadata to remove
        :returns: True if removed, False if not found
        """
        # Implementation for removing stored metadata
        # This will integrate with settings when implemented
        return False

    @classmethod
    def list_collections(cls) -> typing.List[str]:
        """List all registered collection types.

        :returns: List of collection type identifiers
        """
        return list(set(list(cls._serializers.keys()) + list(cls._deserializers.keys())))


# Global registry instance
constant_raster_registry = ConstantRasterRegistry
