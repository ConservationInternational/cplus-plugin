# -*- coding: utf-8 -*-
"""Models for Constant Raster Priority Weighting Layers (PWL)."""

from __future__ import annotations
import dataclasses
import typing

from .base import NcsPathway
from ..definitions.constants import (
    MIN_VALUE_ATTRIBUTE,  # "minimum_value"
    MAX_VALUE_ATTRIBUTE,  # "maximum_value"
    REMOVE_EXISTING_ATTRIBUTE,  # "remove_existing"
    NCS_PATHWAY_IDENTIFIER_PROPERTY,  # "pathway_identifier"
    ENABLED_ATTRIBUTE,  # "enabled"
    PATH_ATTRIBUTE,  # "path"
)


# ---------------------------
# String-backed enums (stable)
# ---------------------------
class _StrEnum(str):
    def __str__(self) -> str:  # pragma: no cover
        return str(self.value)


class InputMode(_StrEnum):
    RASTER_FILE = "raster_file"
    CONSTANT_VALUE = "constant_value"


class ScaleMode(_StrEnum):
    AUTO_MINMAX = "auto_minmax"
    MANUAL_MINMAX = "manual_minmax"


class Inversion(_StrEnum):
    NONE = "none"
    INVERT = "invert"


# ---------------------------
# Data models
# ---------------------------
@dataclasses.dataclass
class ConstantPwlItem:
    """One constant PWL definition for a single pathway."""

    pathway: NcsPathway
    enabled: bool = True
    input_mode: InputMode = InputMode.CONSTANT_VALUE
    raster_path: str = ""  # used when input_mode == RASTER_FILE
    constant_value: float = 0.0  # used when input_mode == CONSTANT_VALUE
    normalized_raster_path: str = ""  # set after normalization

    # --- convenience ---
    def has_input(self) -> bool:
        return (
            bool(self.raster_path) if self.input_mode == InputMode.RASTER_FILE else True
        )

    def is_constant(self) -> bool:
        return self.input_mode == InputMode.CONSTANT_VALUE

    def is_raster(self) -> bool:
        return self.input_mode == InputMode.RASTER_FILE

    def validate(self) -> None:
        if self.pathway is None:
            raise ValueError("ConstantPwlItem.pathway is required.")
        if self.is_raster() and not self.raster_path:
            raise ValueError("raster_path is required when input_mode == RASTER_FILE.")

    # --- core (de)serialization (enums by .name to match rest of app) ---
    def to_dict(self) -> dict:
        return {
            NCS_PATHWAY_IDENTIFIER_PROPERTY: str(self.pathway.uuid),
            ENABLED_ATTRIBUTE: self.enabled,
            "input_mode": self.input_mode.name,
            PATH_ATTRIBUTE: self.raster_path,
            "constant_value": float(self.constant_value),
            "normalized_raster_path": self.normalized_raster_path,
        }

    @staticmethod
    def from_dict(
        d: dict, pathway_lookup: typing.Callable[[str], NcsPathway]
    ) -> "ConstantPwlItem":
        p = pathway_lookup(d.get(NCS_PATHWAY_IDENTIFIER_PROPERTY))
        return ConstantPwlItem(
            pathway=p,
            enabled=bool(d.get(ENABLED_ATTRIBUTE, True)),
            input_mode=InputMode[d.get("input_mode", InputMode.CONSTANT_VALUE.name)],
            raster_path=d.get(PATH_ATTRIBUTE, "") or "",
            constant_value=float(d.get("constant_value", 0.0)),
            normalized_raster_path=d.get("normalized_raster_path", "") or "",
        )


@dataclasses.dataclass
class ConstantPwlCollection:
    """Collection and shared settings for constant PWL generation."""

    items: typing.List[ConstantPwlItem] = dataclasses.field(default_factory=list)
    min_value: float = 0.0
    max_value: float = 1.0
    scale_mode: ScaleMode = ScaleMode.AUTO_MINMAX
    invert_mode: Inversion = Inversion.NONE
    # Note: we store under REMOVE_EXISTING_ATTRIBUTE per repo convention
    # Semantics: "remove_existing" ≈ remove previously generated outputs when off/changed.
    remove_disabled: bool = True

    # --- convenience ---
    def enabled_items(self) -> typing.List[ConstantPwlItem]:
        return [i for i in self.items if i.enabled and i.has_input()]

    def validate(self) -> None:
        if self.scale_mode == ScaleMode.MANUAL_MINMAX:
            if self.min_value is None or self.max_value is None:
                raise ValueError(
                    "min_value and max_value are required for MANUAL_MINMAX."
                )
            if float(self.max_value) == float(self.min_value):
                raise ValueError(
                    "min_value and max_value must differ for MANUAL_MINMAX."
                )
        for it in self.items:
            it.validate()

    # --- core (de)serialization (uses constants for keys) ---
    def to_dict(self) -> dict:
        return {
            MIN_VALUE_ATTRIBUTE: float(self.min_value),
            MAX_VALUE_ATTRIBUTE: float(self.max_value),
            # Keep these as plain strings to match other saved collections
            "scale_mode": self.scale_mode.name,
            "invert_mode": self.invert_mode.name,
            REMOVE_EXISTING_ATTRIBUTE: bool(self.remove_disabled),
            "items": [i.to_dict() for i in self.items],
        }

    @staticmethod
    def from_dict(
        d: dict, pathway_lookup: typing.Callable[[str], NcsPathway]
    ) -> "ConstantPwlCollection":
        coll = ConstantPwlCollection(
            min_value=float(d.get(MIN_VALUE_ATTRIBUTE, 0.0)),
            max_value=float(d.get(MAX_VALUE_ATTRIBUTE, 1.0)),
            scale_mode=ScaleMode[d.get("scale_mode", ScaleMode.AUTO_MINMAX.name)],
            invert_mode=Inversion[d.get("invert_mode", Inversion.NONE.name)],
            remove_disabled=bool(d.get(REMOVE_EXISTING_ATTRIBUTE, True)),
        )
        coll.items = [
            ConstantPwlItem.from_dict(x, pathway_lookup) for x in d.get("items", [])
        ]
        return coll


# ---------------------------
# Preset builder (Years of Experience etc.)
# ---------------------------
def make_default_collection_for_pathways(
    pathways: typing.Iterable[NcsPathway],
    default_value: float = 0.0,
    enabled: bool = True,
) -> ConstantPwlCollection:
    items = [
        ConstantPwlItem(
            pathway=p,
            enabled=enabled,
            input_mode=InputMode.CONSTANT_VALUE,
            constant_value=float(default_value),
        )
        for p in pathways
    ]
    return ConstantPwlCollection(items=items)
