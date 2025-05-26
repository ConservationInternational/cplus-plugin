# -*- coding: utf-8 -*-

""" Data models for the financial elements of the tool."""

import dataclasses
import typing

from .base import NcsPathway


@dataclasses.dataclass
class NpvParameters:
    """Parameters for computing an NCS pathway's NPV."""

    years: int
    discount: float
    absolute_npv: float = 0.0
    normalized_npv: float = 0.0
    # Each tuple contains 3 elements i.e. revenue, costs and discount rates
    yearly_rates: typing.List[tuple] = dataclasses.field(default_factory=list)
    manual_npv: bool = False

    def __post_init__(self):
        """Set empty yearly rates for consistency."""
        for i in range(self.years):
            self.yearly_rates.append((None, None, None))


@dataclasses.dataclass
class NcsPathwayNpv:
    """Mapping of the NPV parameters to the corresponding NCS pathway."""

    params: NpvParameters
    enabled: bool
    pathway: typing.Optional[NcsPathway]

    @property
    def pathway_id(self) -> str:
        """Gets the identifier of the NCS pathway model.

        :returns: The unique identifier of the NCS pathway model
        else an empty string if no NCS pathway has been set.
        """
        if not self.pathway:
            return ""

        return str(self.pathway.uuid)

    @property
    def base_name(self) -> str:
        """Returns a proposed name for the NCS pathway NPV.

        An empty string will be return id the `pathway` attribute
        is not set.

        :returns: Proposed base name for the NCS pathway NPV.
        :rtype: str
        """
        if self.pathway is None:
            return ""

        return f"{self.pathway.name} NPV Norm"


@dataclasses.dataclass
class NcsPathwayNpvCollection:
    """Collection for all NcsPathwayNpv configurations
    that have been specified by the user.
    """

    minimum_value: float
    maximum_value: float
    use_computed: bool = True
    remove_existing: bool = False
    mappings: typing.List[NcsPathwayNpv] = dataclasses.field(default_factory=list)

    def pathway_npv(self, pathway_identifier: str) -> typing.Optional[NcsPathwayNpv]:
        """Gets the mapping of an NCS pathway's NPV mapping if defined.

        :param pathway_identifier: Unique identifier of an NCS pathway
        whose NPV mapping is to be retrieved.
        :type pathway_identifier: str

        :returns: The NCS pathway's NPV mapping else None if not found.
        :rtype: NcsPathwayNpv
        """
        matching_mapping = [
            pathway_npv
            for pathway_npv in self.mappings
            if pathway_npv.pathway_id == pathway_identifier
        ]

        return None if len(matching_mapping) == 0 else matching_mapping[0]

    def update_computed_normalization_range(self) -> bool:
        """Update the minimum and maximum normalization values
        based on the absolute values of the existing NcsPathwayNpv
        objects.

        Values for disabled Ncs pathway NPVs will be excluded from
        the computation.

        :returns: True if the min/max values were updated else False if
        there are no mappings or valid absolute NPV values defined.
        """
        if len(self.mappings) == 0:
            return False

        valid_npv_values = [
            pathway_npv.params.absolute_npv
            for pathway_npv in self._valid_npv_mappings()
        ]

        if len(valid_npv_values) == 0:
            return False

        self.minimum_value = min(valid_npv_values)
        self.maximum_value = max(valid_npv_values)

        return True

    def _valid_npv_mappings(self) -> typing.List[NcsPathwayNpv]:
        """Gets NPV mappings which have an absolute value defined and are enabled.

        :returns: A set of valid NPV mappings.
        :rtype: list
        """
        return [
            pathway_npv
            for pathway_npv in self.mappings
            if pathway_npv.params.absolute_npv is not None and pathway_npv.enabled
        ]

    def normalize_npvs(self) -> bool:
        """Normalize the NPV values of NCS pathway using the specified
        normalization range.

        If the absolute NPV values are less than or greater than the
        normalization range, then they will be truncated to 0.0 and 1.0
        respectively. To avoid such a situation from occurring, it is recommended
        to make sure that the ranges are synchronized using the latest absolute
        NPV values by calling `update_computed_normalization_range` before
        normalizing the NPVs.

        If there is only one NPV mapping, then assign a normalized value of 1.0.

        :returns: True if the NPVs were successfully normalized else False due
        to various reasons such as if the minimum value is greater than the
        maximum value, if the min/max values are the same, or if there are no NPV
        mappings.
        """
        valid_npv_mappings = self._valid_npv_mappings()
        if len(valid_npv_mappings) == 0:
            return False

        if len(valid_npv_mappings) == 1:
            pathway_npv = self.mappings[0]
            pathway_npv.params.normalized_npv = 1.0
            return True

        if self.minimum_value > self.maximum_value:
            return False

        norm_range = float(self.maximum_value - self.minimum_value)

        if norm_range == 0.0:
            return False

        for pathway_npv in valid_npv_mappings:
            absolute_npv = pathway_npv.params.absolute_npv
            if not absolute_npv:
                continue

            if absolute_npv <= self.minimum_value:
                normalized_npv = 0.0
            elif absolute_npv >= self.maximum_value:
                normalized_npv = 1.0
            else:
                normalized_npv = (absolute_npv - self.minimum_value) / norm_range

            pathway_npv.params.normalized_npv = normalized_npv

        return True


@dataclasses.dataclass
class NcsPathwayNpvPwl:
    """Convenience class that contains parameters for creating
    a PWL raster layer.
    """

    npv: NcsPathwayNpv
    extent: typing.List[float]
    crs: str
    pixel_size: float
