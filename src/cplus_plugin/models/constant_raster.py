# -*- coding: utf-8 -*-
"""Models for Constant Raster according to architectural specification."""

from __future__ import annotations
import os
import dataclasses
import typing
from datetime import datetime
from qgis.core import QgsRasterLayer

from .base import LayerModelComponent, ModelComponentType
from ..definitions.constants import (
    PATH_ATTRIBUTE,
)


@dataclasses.dataclass
class ConstantRasterInfo:
    """Value information for a constant raster.

    This dataclass only handles value information (normalized and absolute values),
    File/layer information should be handled separately by ConstantRasterComponent.
    """

    normalized: float = 0.0  # Normalized value (0-1 range)
    absolute: float = 0.0  # Absolute constant value for creating rasters

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "normalized": self.normalized,
            "absolute": self.absolute,
        }

    @staticmethod
    def from_dict(d: dict) -> "ConstantRasterInfo":
        """Deserialize from dictionary."""
        return ConstantRasterInfo(
            normalized=float(d.get("normalized", 0.0)),
            absolute=float(d.get("absolute", 0.0)),
        )


@dataclasses.dataclass
class ConstantRasterComponent:
    """Individual constant raster with layer model component associations.

    This class links the ConstantRasterInfo with the specific layer model
    component (NcsPathway or Activity).
    Activities are stored by calling their type.
    """

    value_info: ConstantRasterInfo
    component: LayerModelComponent  # Either NcsPathway or Activity
    prefix: str = ""  # Prefix for naming
    base_name: str = ""  # Base component name
    suffix: str = ""  # Suffix for naming
    alias_name: str = ""
    path: str = ""  # Note: Returns False for components (not a file path)
    skip_raster: bool = True  # Skip raster creation for this component (default: True)
    enabled: bool = True  # Whether this component is enabled
    component_id: str = ""
    component_type: ModelComponentType = ModelComponentType.UNKNOWN
    qgis_map_layer: typing.Optional[QgsRasterLayer] = None

    def identifier(self) -> str:
        """Generate unique identifier by concatenating naming components.

        Uses prefix, base_name, and suffix to create the identifier.
        For example: "prefix_base_name_suffix" or just components that exist.
        """
        parts = []
        if self.prefix:
            parts.append(self.prefix)
        if self.base_name:
            parts.append(self.base_name)
        elif self.component:
            parts.append(getattr(self.component, "name", ""))
        if self.suffix:
            parts.append(self.suffix)

        if parts:
            return "_".join(parts)
        return self.alias_name or self.component_id

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "value_info": self.value_info.to_dict() if self.value_info else {},
            "component_uuid": str(self.component.uuid) if self.component else "",
            "prefix": self.prefix,
            "base_name": self.base_name,
            "suffix": self.suffix,
            "alias_name": self.alias_name,
            PATH_ATTRIBUTE: self.path,
            "skip_raster": self.skip_raster,
            "enabled": self.enabled,
            "component_id": self.component_id,
            "component_type": (
                self.component_type.value
                if self.component_type
                else ModelComponentType.UNKNOWN.value
            ),
        }

    @staticmethod
    def from_dict(
        d: dict, component_lookup: typing.Callable[[str], LayerModelComponent]
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
        value_info = (
            ConstantRasterInfo.from_dict(value_info_data)
            if value_info_data
            else ConstantRasterInfo()
        )

        component_type_str = d.get("component_type", ModelComponentType.UNKNOWN.value)
        component_type = ModelComponentType.from_string(component_type_str)

        return ConstantRasterComponent(
            value_info=value_info,
            component=component,
            prefix=d.get("prefix", ""),
            base_name=d.get("base_name", ""),
            suffix=d.get("suffix", ""),
            alias_name=d.get("alias_name", ""),
            path=d.get(PATH_ATTRIBUTE, ""),
            skip_raster=bool(d.get("skip_raster", True)),
            enabled=bool(d.get("enabled", True)),
            component_id=d.get("component_id", ""),
            component_type=component_type,
        )

    def to_map_layer(self) -> typing.Optional[QgsRasterLayer]:
        """Convert to QGIS raster layer.

        :returns: QgsRasterLayer if path exists and is valid, None otherwise
        """
        if not self.path or not self.path.strip():
            return None

        if self.qgis_map_layer:
            return self.qgis_map_layer

        if os.path.exists(self.path):
            layer = QgsRasterLayer(self.path, self.alias_name or self.component_id)
            if layer.isValid():
                self.qgis_map_layer = layer
                return layer

        return None


@dataclasses.dataclass
class ConstantRasterCollection:
    """Manages multiple ConstantRasterComponents.

    With a maker, this provides the option of skipping the creation
    of the constant raster collectively for all items in a collection
    or at a more granular level (ConstantRasterComponent). If skip_raster
    is True then the "path" attribute will always return False.
    """

    min_value: float = 0.0
    max_value: float = 1.0
    component_type: typing.Optional[ModelComponentType] = None
    components: typing.List[ConstantRasterComponent] = dataclasses.field(
        default_factory=list
    )
    skip_raster: bool = True
    allowable_max: float = 1.0
    allowable_min: float = 0.0

    def normalize(self) -> None:
        """Normalize the collection by updating min/max values based on components.

        This method analyzes all enabled components and updates both min_value/max_value
        and allowable_min/allowable_max based on the absolute values in component value_info objects.
        """
        enabled = self.enabled_components()
        if not enabled:
            return

        # Get all absolute values from enabled components
        values = [c.value_info.absolute for c in enabled if c.value_info]
        if not values:
            return

        # Update both sets of min/max
        self.min_value = min(values)
        self.max_value = max(values)
        self.allowable_min = min(values)
        self.allowable_max = max(values)

    def enabled_components(self) -> typing.List[ConstantRasterComponent]:
        """Get list of enabled components (where skip_raster is False).

        :returns: List of enabled ConstantRasterComponent objects
        """
        return [c for c in self.components if not c.skip_raster]

    def validate(
        self, metadata: typing.Optional["ConstantRasterMetadata"] = None
    ) -> bool:
        """Validate the collection configuration.

        :param metadata: Optional metadata to validate against input_range constraints
        :returns: True if valid, False otherwise
        :raises ValueError: If validation fails with details
        """
        if self.min_value >= self.max_value:
            raise ValueError(
                f"min_value ({self.min_value}) must be less than max_value ({self.max_value})"
            )

        if self.allowable_min >= self.allowable_max:
            raise ValueError(
                f"allowable_min ({self.allowable_min}) must be less than allowable_max ({self.allowable_max})"
            )

        if metadata is not None:
            input_min, input_max = metadata.input_range
            if self.min_value < input_min or self.max_value > input_max:
                raise ValueError(
                    f"Output range ({self.min_value}, {self.max_value}) must be within "
                    f"input range ({input_min}, {input_max}) defined in metadata"
                )

        return True

    def component_by_id(
        self, identifier: str
    ) -> typing.Optional[ConstantRasterComponent]:
        """Get component by its identifier (UUID).

        :param identifier: UUID of the component to retrieve
        :returns: ConstantRasterComponent if found, None otherwise
        """
        for component in self.components:
            if component.component_id == identifier:
                return component
            # Also check the component's UUID if available
            if component.component and str(component.component.uuid) == identifier:
                return component
        return None

    def component_by_identifier(
        self, identifier: str
    ) -> typing.Optional[ConstantRasterComponent]:
        """Get component by its identifier (UUID). Alias for component_by_id.

        :param identifier: UUID of the component to retrieve
        :returns: ConstantRasterComponent if found, None otherwise
        """
        return self.component_by_id(identifier)

    def add_component(self, component: ConstantRasterComponent) -> bool:
        """Add a component to the collection.

        :param component: ConstantRasterComponent to add
        :returns: True if added successfully, False if already exists
        """
        # Check if component already exists
        if self.component_by_id(component.component_id):
            return False

        self.components.append(component)
        return True

    def remove_component(self, identifier: str) -> bool:
        """Remove a component by its identifier.

        :param identifier: UUID of the component to remove
        :returns: True if removed, False if not found
        """
        component = self.component_by_id(identifier)
        if component:
            self.components.remove(component)
            return True
        return False

    def __len__(self) -> int:
        """Return the number of components in the collection."""
        return len(self.components)

    def __iter__(self):
        """Make collection iterable over components."""
        return iter(self.components)


@dataclasses.dataclass
class ConstantRasterContext:
    """Context for creating constant rasters.

    Provides configuration for the raster creation process including
    extent, resolution, CRS, and output directory.
    """

    component: typing.Optional[LayerModelComponent] = None  # Associated component
    extent: typing.Any = None  # QgsRectangle
    pixel_size: float = 30.0  # Default pixel size in map units
    crs: typing.Any = None  # QgsCoordinateReferenceSystem
    output_dir: str = ""  # Output directory for created rasters
    remove_existing: bool = True  # Whether to remove existing rasters

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
    raster_collection: typing.Optional[ConstantRasterCollection] = None
    deserializer: typing.Optional[typing.Callable] = None  # PyFunc
    component_type: typing.Optional[
        "ModelComponentType"
    ] = None  # Type this metadata applies to
    input_range: typing.Tuple[float, float] = (
        0.0,
        100.0,
    )  # Min and max for input values (e.g., 0-100 years)

    def to_dict(self) -> dict:
        """Serialize to dictionary (excluding deserializer)."""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "raster_collection": (
                self.raster_collection.to_dict() if self.raster_collection else {}
            ),
            "component_type": (
                self.component_type.value if self.component_type else None
            ),
            "input_range": list(self.input_range),
        }


@dataclasses.dataclass
class ConstantRasterFileMetadata:
    """Metadata for constant raster files.

    This dataclass represents the metadata that gets written to .meta.txt files
    alongside constant rasters, documenting how they were created.
    """

    raster_path: str
    component_id: str
    component_name: str
    component_type: str  # "NCS_PATHWAY" or "ACTIVITY"
    input_value: float
    normalized_value: float
    output_min: float
    output_max: float
    metadata_id: str
    created_timestamp: str = ""

    def to_text(self) -> str:
        """Format metadata as human-readable text.

        :returns: Formatted text suitable for writing to a .meta.txt file
        """
        timestamp = self.created_timestamp or datetime.utcnow().isoformat()

        lines = [
            "Constant Raster Metadata",
            "========================",
            "",
            f"Created: {timestamp}",
            f"Raster Path: {self.raster_path}",
            "",
            "Component Information:",
            f"  ID: {self.component_id}",
            f"  Name: {self.component_name}",
            f"  Type: {self.component_type}",
            "",
            "Values:",
            f"  Input Value: {self.input_value}",
            f"  Normalized Value: {self.normalized_value}",
            f"  Output Range: {self.output_min} - {self.output_max}",
            "",
            "Metadata:",
            f"  Type ID: {self.metadata_id}",
        ]

        return "\n".join(lines)
