# -*- coding: utf-8 -*-

""" Data models for report production."""

import dataclasses
import typing
from uuid import UUID

from .base import Scenario


@dataclasses.dataclass
class ReportContext:
    """Context information for generating a report."""

    template_path: str
    output_dir: str
    scenario: Scenario
    name: str


@dataclasses.dataclass
class ReportResult:
    """Detailed result information from a report generation
    run.
    """

    success: bool
    scenario_id: UUID
    output_dir: str
    messages: typing.List[str] = dataclasses.field(default_factory=list)
