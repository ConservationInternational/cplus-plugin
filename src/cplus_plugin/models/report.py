# -*- coding: utf-8 -*-

""" Data models for report production."""

import dataclasses
import typing
from uuid import UUID

from qgis.core import QgsFeedback, QgsRectangle

from .base import Scenario


@dataclasses.dataclass
class ReportContext:
    """Context information for generating a report."""

    template_path: str
    scenario: Scenario
    name: str
    scenario_output_dir: str
    project_file: str
    feedback: QgsFeedback
    output_layer_name: str


@dataclasses.dataclass
class ReportSubmitStatus:
    """Result of report submission process."""

    status: bool
    feedback: QgsFeedback


@dataclasses.dataclass
class ReportResult:
    """Detailed result information from a report generation
    run.
    """

    success: bool
    scenario_id: UUID
    output_dir: str
    # Error messages
    messages: typing.Tuple[str] = dataclasses.field(default_factory=tuple)
    # Layout name
    name: str = ""

    @property
    def pdf_path(self) -> str:
        """Returns the absolute path to the PDF file if the process
        completed successfully.

         Caller needs to verify if the file actually exists in the
         given location.

         :returns: Absolute path to the PDF file if the process
        completed successfully else an empty string.
        :rtype: str
        """
        if not self.output_dir or not self.name:
            return ""

        return f"{self.output_dir}/{self.name}.pdf"
