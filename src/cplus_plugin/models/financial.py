# -*- coding: utf-8 -*-

""" Data models for the financial elements of the tool."""

import dataclasses
from enum import IntEnum
import typing

from .base import Activity


@dataclasses.dataclass
class NpvParameters:
    """Parameters for computing an activity's NPV."""

    years: int
    discount: float
    absolute_npv: float
    normalized_npv: float
    # Each tuple contains 3 elements i.e. revenue, costs and discount rates
    yearly_rates: typing.List[tuple] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ActivityNpvMapping:
    """Mapping of the NPV parameters to the corresponding Activity model.
    """

    params: NpvParameters
    enabled: bool
    activity: Activity

    @property
    def activity_id(self) -> str:
        """Gets the identifier of the activity model.

        :returns: The unique identifier of the activity model else an
        empty string if no activity has been set.
        """
        if not self.activity:
            return ""

        return str(self.activity.uuid)


@dataclasses.dataclass
class ActivityNpvCollection:
    """Collection for all ActivityNpvMapping configurations that have been
    specified by the user.
    """
    minimum_value: float
    maximum_value: float
    use_computed: bool = False
    mappings: typing.List[ActivityNpvMapping] = dataclasses.field(default_factory=list)