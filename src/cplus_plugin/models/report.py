# -*- coding: utf-8 -*-

""" Data models for report production."""

import dataclasses
from enum import IntEnum
import typing
from uuid import UUID

from qgis.core import QgsFeedback, QgsLayoutTableColumn
from qgis.PyQt import QtCore

from .base import Activity, Scenario, ScenarioResult


@dataclasses.dataclass
class BaseReportContext:
    """Common context information for generating a scenario report."""

    template_path: str
    name: str
    project_file: str
    feedback: QgsFeedback


@dataclasses.dataclass
class ReportContext(BaseReportContext):
    """Context information for generating a scenario analysis report."""

    scenario: Scenario
    scenario_output_dir: str
    output_layer_name: str
    custom_metrics: bool


@dataclasses.dataclass
class ReportSubmitStatus:
    """Result of report submission process."""

    status: bool
    feedback: QgsFeedback
    identifier: str


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
    base_file_name: str = ""

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
        if not self.output_dir or not self.base_file_name:
            return ""

        return f"{self.output_dir}/{self.base_file_name}.pdf"


@dataclasses.dataclass
class ScenarioComparisonReportContext(BaseReportContext):
    """Contextual information related to the generation of scenario
    comparison report.
    """

    results: typing.List[ScenarioResult]
    output_dir: str


@dataclasses.dataclass
class ScenarioAreaInfo:
    """Contains information on the result of calculating a
    scenario's area.
    """

    name: str
    identifier: UUID
    area: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class RepeatAreaDimension:
    """Contains information for rendering repeat model items
    such as scenarios or activities in a CPlus repeat item.
    """

    rows: int
    columns: int
    width: float
    height: float


@dataclasses.dataclass
class MetricColumn:
    """This class contains information required to create
    custom columns for the activity table in a scenario
    analysis report.
    """

    name: str
    header: str
    expression: str
    alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignHCenter
    auto_calculated: bool = False

    def to_qgs_column(self) -> QgsLayoutTableColumn:
        """Convenience function that converts this object to a
        QgsLayoutTableColumn for use in a QgsLayoutTable.

        :returns: A layout column object containing the heading,
        horizontal alignment and width specified.
        :rtype: QgsLayoutTableColumn
        """
        layout_column = QgsLayoutTableColumn(self.header)
        layout_column.setHAlignment(self.alignment)
        layout_column.setWidth(0)

        return layout_column


class MetricType(IntEnum):
    """Type of metric or expression."""

    COLUMN = 0
    CELL = 1
    NOT_SET = 2
    UNKNOWN = 3

    @staticmethod
    def from_int(int_enum: int) -> "MetricType":
        """Creates the metric type enum from the
        corresponding int equivalent.

        :param int_enum: Integer representing the metric type.
        :type int_enum: int

        :returns: Metric type enum corresponding to the given
        int else unknown if not found.
        :rtype: MetricType
        """
        if int_enum == 0:
            return MetricType.COLUMN
        elif int_enum == 1:
            return MetricType.CELL
        elif int_enum == 2:
            return MetricType.NOT_SET
        else:
            return MetricType.UNKNOWN


@dataclasses.dataclass
class ActivityColumnMetric:
    """This class provides granular control of the metric
    applied in each activity's column.
    """

    activity: Activity
    metric_column: MetricColumn
    metric_type: MetricType = MetricType.NOT_SET
    expression: str = ""

    def is_valid(self) -> bool:
        """Checks if the activity column metric is valid.

        :returns: True if the activity column metric is
        valid else False.
        :rtype: bool
        """
        if self.activity is None or self.metric_column is None:
            return False

        if self.metric_type == MetricType.NOT_SET:
            return False

        if not self.expression:
            return False

        return True


@dataclasses.dataclass
class MetricConfiguration:
    """Container for metric column and
    activity column metric data models.
    """

    metric_columns: typing.List[MetricColumn]
    activity_metrics: typing.List[typing.List[ActivityColumnMetric]]

    def is_valid(self) -> bool:
        """Checks the validity of the configuration.

        It verifies if the number of metric columns matches the
        column mappings for activity metrics.

        :returns: True if the configuration is valid, else False.
        :rtype: bool
        """
        column_metrics_len = 0
        if len(self.activity_metrics) > 0:
            column_metrics_len = len(self.activity_metrics[0])

        return len(self.metric_columns) == column_metrics_len

    @property
    def activities(self) -> typing.List[Activity]:
        """Gets the activity models in the configuration.

        :returns: Activity models in the configuration.
        :rtype: typing.List[Activity]
        """
        activities = []
        for activity_row in self.activity_metrics:
            if len(activity_row) > 0:
                activities.append(activity_row[0].activity)

        return activities

    def find(
        self, activity_id: str, name_header: str
    ) -> typing.Optional[ActivityColumnMetric]:
        """Returns a matching activity column metric model
        for the activity with the given UUID and the corresponding
        metric column name or header label.

        :param activity_id: The activity's unique identifier.
        :type activity_id: str

        :param name_header: The metric column name or header to match.
        :type name_header: str

        :returns: Matching column metric or None if not found.
        :rtype: typing.Optional[ActivityColumnMetric]
        """

        def _search_list(model_list: typing.List, activity_identifier: str, name: str):
            for model in model_list:
                if isinstance(model, list):
                    yield from _search_list(model, activity_identifier, name)
                else:
                    if str(model.activity.uuid) == activity_identifier and (
                        model.metric_column.name == name
                        or model.metric_column.name == name
                    ):
                        yield model

        match = next(_search_list(self.activity_metrics, activity_id, name_header), -1)

        return match if match != -1 else None


@dataclasses.dataclass
class ActivityContextInfo:
    """Contains information about an activity for use in an expression context."""

    activity: Activity
    area: float


@dataclasses.dataclass
class MetricEvalResult:
    """Result of evaluating a metric."""

    success: bool
    value: typing.Any
