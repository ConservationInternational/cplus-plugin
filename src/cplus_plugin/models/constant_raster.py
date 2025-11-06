# -*- coding: utf-8 -*-
"""Models for Constant Raster according to architectural specification."""

from __future__ import annotations
import os
import sys
import dataclasses
import typing
from datetime import datetime
from typing import NamedTuple
from qgis.core import QgsRasterLayer

from .base import LayerModelComponent, ModelComponentType
from ..definitions.constants import (
    PATH_ATTRIBUTE,
    COMPONENT_UUID_ATTRIBUTE,
    COMPONENT_ID_ATTRIBUTE,
    COMPONENT_TYPE_ATTRIBUTE,
    SKIP_RASTER_ATTRIBUTE,
    ENABLED_ATTRIBUTE,
    VALUE_INFO_ATTRIBUTE,
    NORMALIZED_ATTRIBUTE,
    ABSOLUTE_ATTRIBUTE,
    MIN_VALUE_ATTRIBUTE_KEY,
    MAX_VALUE_ATTRIBUTE_KEY,
    ALLOWABLE_MIN_ATTRIBUTE,
    ALLOWABLE_MAX_ATTRIBUTE,
    LAST_UPDATED_ATTRIBUTE,
    COMPONENTS_ATTRIBUTE,
    DISPLAY_NAME_ATTRIBUTE,
    RASTER_COLLECTION_ATTRIBUTE,
    INPUT_RANGE_ATTRIBUTE,
)


class InputRange(NamedTuple):
    """Range for input values with named min/max fields for readability."""

    min: float
    max: float


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
            NORMALIZED_ATTRIBUTE: self.normalized,
            ABSOLUTE_ATTRIBUTE: self.absolute,
        }

    @staticmethod
    def from_dict(d: dict) -> "ConstantRasterInfo":
        """Deserialize from dictionary."""
        return ConstantRasterInfo(
            normalized=float(d.get(NORMALIZED_ATTRIBUTE, 0.0)),
            absolute=float(d.get(ABSOLUTE_ATTRIBUTE, 0.0)),
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
    path: str = ""  # Note: Returns False for components (not a file path)
    skip_raster: bool = (
        False  # Skip raster creation for this component (default: False)
    )
    enabled: bool = True  # Whether this component is enabled
    component_id: str = ""
    component_type: ModelComponentType = ModelComponentType.UNKNOWN

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
        return self.component_id

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            VALUE_INFO_ATTRIBUTE: self.value_info.to_dict() if self.value_info else {},
            COMPONENT_UUID_ATTRIBUTE: str(self.component.uuid)
            if self.component
            else "",
            "prefix": self.prefix,
            "base_name": self.base_name,
            "suffix": self.suffix,
            PATH_ATTRIBUTE: self.path,
            SKIP_RASTER_ATTRIBUTE: self.skip_raster,
            ENABLED_ATTRIBUTE: self.enabled,
            COMPONENT_ID_ATTRIBUTE: self.component_id,
            COMPONENT_TYPE_ATTRIBUTE: (
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
        component_uuid = d.get(COMPONENT_UUID_ATTRIBUTE)
        if component_uuid:
            component = component_lookup(component_uuid)

        value_info_data = d.get(VALUE_INFO_ATTRIBUTE, {})
        value_info = (
            ConstantRasterInfo.from_dict(value_info_data)
            if value_info_data
            else ConstantRasterInfo()
        )

        component_type_str = d.get(
            COMPONENT_TYPE_ATTRIBUTE, ModelComponentType.UNKNOWN.value
        )
        component_type = ModelComponentType.from_string(component_type_str)

        return ConstantRasterComponent(
            value_info=value_info,
            component=component,
            prefix=d.get("prefix", ""),
            base_name=d.get("base_name", ""),
            suffix=d.get("suffix", ""),
            path=d.get(PATH_ATTRIBUTE, ""),
            skip_raster=bool(d.get(SKIP_RASTER_ATTRIBUTE, False)),
            enabled=bool(d.get(ENABLED_ATTRIBUTE, True)),
            component_id=d.get(COMPONENT_ID_ATTRIBUTE, ""),
            component_type=component_type,
        )

    def to_map_layer(self) -> typing.Optional[QgsRasterLayer]:
        """Convert to QGIS raster layer.

        :returns: QgsRasterLayer if path exists and is valid, None otherwise
        """
        if not self.path or not self.path.strip():
            return None

        if os.path.exists(self.path):
            layer_name = (
                self.component.name
                if self.component and hasattr(self.component, "name")
                else self.component_id
            )
            layer = QgsRasterLayer(self.path, layer_name)
            if layer.isValid():
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
    skip_raster: bool = False
    allowable_max: float = sys.float_info.max
    allowable_min: float = 0.0
    last_updated: str = ""  # ISO format timestamp of last modification

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
        """Get list of enabled components.

        Returns components where enabled is True. Note that skip_raster is
        independent - an enabled component may still skip raster creation
        and only generate metadata.

        :returns: List of enabled ConstantRasterComponent objects
        """
        return [c for c in self.components if c.enabled]

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
            if (
                self.min_value < metadata.input_range.min
                or self.max_value > metadata.input_range.max
            ):
                raise ValueError(
                    f"Normalization range ({self.min_value}, {self.max_value}) must be within "
                    f"input range ({metadata.input_range.min}, {metadata.input_range.max}) defined in metadata"
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
    input_range: InputRange = InputRange(
        min=0.0, max=100.0
    )  # Min and max for input values (e.g., 0-100 years)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        # Serialize raster_collection inline
        collection_dict = {}
        if self.raster_collection:
            collection_dict = {
                MIN_VALUE_ATTRIBUTE_KEY: self.raster_collection.min_value,
                MAX_VALUE_ATTRIBUTE_KEY: self.raster_collection.max_value,
                COMPONENT_TYPE_ATTRIBUTE: (
                    self.raster_collection.component_type.value
                    if self.raster_collection.component_type
                    else None
                ),
                ALLOWABLE_MIN_ATTRIBUTE: self.raster_collection.allowable_min,
                ALLOWABLE_MAX_ATTRIBUTE: self.raster_collection.allowable_max,
                SKIP_RASTER_ATTRIBUTE: self.raster_collection.skip_raster,
                LAST_UPDATED_ATTRIBUTE: self.raster_collection.last_updated,
                COMPONENTS_ATTRIBUTE: [
                    c.to_dict() for c in self.raster_collection.components
                ],
            }

        return {
            "id": self.id,
            DISPLAY_NAME_ATTRIBUTE: self.display_name,
            RASTER_COLLECTION_ATTRIBUTE: collection_dict,
            COMPONENT_TYPE_ATTRIBUTE: (
                self.component_type.value if self.component_type else None
            ),
            INPUT_RANGE_ATTRIBUTE: list(self.input_range),
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
            f"Component Name: {self.component_name}",
            f"Normalized Value: {self.normalized_value}",
            f"Normalization Range: {self.output_min} - {self.output_max}",
        ]

        return "\n".join(lines)
