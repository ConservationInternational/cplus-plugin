# -*- coding: utf-8 -*-

""" Data models for the financial elements of the tool."""

import dataclasses
import typing

from .base import Activity, ModelComponentType
from .constant_raster import (
    ConstantRasterCollection,
    ConstantRasterComponent,
    ConstantRasterInfo,
)


@dataclasses.dataclass
class NpvParameters(ConstantRasterInfo):
    """Parameters for computing an activity's NPV."""

    years: int = 0
    discount: float = 0.0
    # Each tuple contains 3 elements i.e. revenue, costs and discount rates
    yearly_rates: typing.List[tuple] = dataclasses.field(default_factory=list)
    manual_npv: bool = False

    def __post_init__(self):
        """Set empty yearly rates for consistency."""
        for i in range(self.years):
            self.yearly_rates.append((None, None, None))


@dataclasses.dataclass
class ActivityNpv(ConstantRasterComponent):
    """Mapping of the NPV parameters to the corresponding activity."""

    @property
    def activity_id(self) -> str:
        """Gets the identifier of the activity model.

        :returns: The unique identifier of the activity model
        else an empty string if no activity has been set.
        """
        if self.component_type != ModelComponentType.ACTIVITY:
            return ""

        return self.component_id

    @property
    def activity(self) -> typing.Optional[Activity]:
        """Wrapper for legacy support returning the activity model.

        :return: The activity if defined else None.
        :rtype: Activity
        """
        if not isinstance(self.component, Activity):
            return None

        return self.component

    @activity.setter
    def activity(self, activity: Activity):
        """Wrapper for setting the model component.

        :param activity: Model component for the NPV.
        :type activity: Activity
        """
        self.component = activity

    @property
    def params(self) -> typing.Optional[NpvParameters]:
        """Wrapper for legacy support returning the activity's
        parameters object.

        :returns: The activity's parameters object or None if not
        specified.
        :rtype: NpvParameters
        """
        if not isinstance(self.value_info, NpvParameters):
            return None

        return self.value_info

    @params.setter
    def params(self, params: NpvParameters):
        """Wrapper for legacy support setting the activity's
        parameters object.

        :param params: Activity parameters object.
        :type params: NpvParameters
        """
        self.value_info = params

    @property
    def base_name(self) -> str:
        """Returns a proposed name for the NCS pathway NPV.

        An empty string will be return id the `pathway` attribute
        is not set.

        :returns: Proposed base name for the NCS pathway NPV.
        :rtype: str
        """
        if self.activity is None:
            return ""

        return f"{self.activity.name} NPV Norm"


@dataclasses.dataclass
class ActivityNpvCollection(ConstantRasterCollection):
    """Collection for all ActivityNpv configurations
    that have been specified by the user.
    """

    use_computed: bool = True
    remove_existing: bool = False

    def activity_npv(self, activity_identifier: str) -> typing.Optional[ActivityNpv]:
        """Gets the mapping of an activity's NPV mapping if defined.

        :param activity_identifier: Unique identifier of an activity
        whose NPV mapping is to be retrieved.
        :type activity_identifier: str

        :returns: The activity's NPV mapping else None if not found.
        :rtype: ActivityNpv
        """
        matching_mapping = [
            activity_npv
            for activity_npv in self.mappings
            if activity_npv.activity_id == activity_identifier
        ]

        return None if len(matching_mapping) == 0 else matching_mapping[0]

    @property
    def mappings(self) -> typing.List[ActivityNpv]:
        """Get the mapping of activity NPVs.

        This is a wrapper only used for legacy support.

        :returns: List of activity NPV mappings.
        :rtype: typing.List[ActivityNpv]
        """
        return [
            activity_npv
            for activity_npv in self.components
            if isinstance(activity_npv, ActivityNpv)
        ]

    @mappings.setter
    def mappings(self, mappings: typing.List[ActivityNpv]):
        """Set the activity NPV mappings.

        This is a wrapper only used for legacy support.

        :param mappings: Collection of activity NPVs.
        :type mappings: typing.List[ActivityNpv]
        """
        self.components = mappings

    def update_computed_normalization_range(self) -> bool:
        """Update the minimum and maximum normalization values
        based on the absolute values of the existing ActivityNpv
        objects.

        Values for disabled activity NPVs will be excluded from
        the computation.

        :returns: True if the min/max values were updated else False if
        there are no mappings or valid absolute NPV values defined.
        """
        if len(self.mappings) == 0:
            return False

        valid_npv_values = [
            activity_npv.params.absolute for activity_npv in self._valid_npv_mappings()
        ]

        if len(valid_npv_values) == 0:
            return False

        self.min_value = min(valid_npv_values)
        self.max_value = max(valid_npv_values)

        return True

    def _valid_npv_mappings(self) -> typing.List[ActivityNpv]:
        """Gets NPV mappings which have an absolute value defined and are enabled.

        :returns: A set of valid NPV mappings.
        :rtype: list
        """
        return [
            activity_npv
            for activity_npv in self.mappings
            if activity_npv.params.absolute is not None and activity_npv.enabled
        ]

    def normalize(self):
        """Normalize minimum and maximum values of the valid mappings in
        the collection.

        Overrides base class implementation.
        """
        self.update_computed_normalization_range()
        _ = self.normalize_npvs()

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
            activity_npv = self.mappings[0]
            activity_npv.params.normalized = 1.0
            return True

        if self.min_value > self.max_value:
            return False

        norm_range = float(self.max_value - self.min_value)

        if norm_range == 0.0:
            return False

        for activity_npv in valid_npv_mappings:
            absolute_npv = activity_npv.params.absolute
            if not absolute_npv:
                continue

            if absolute_npv <= self.min_value:
                normalized_npv = 0.0
            elif absolute_npv >= self.max_value:
                normalized_npv = 1.0
            else:
                normalized_npv = (absolute_npv - self.min_value) / norm_range

            activity_npv.params.normalized = normalized_npv

        return True
