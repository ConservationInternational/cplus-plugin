# -*- coding: utf-8 -*-

""" Data models for report production."""

import dataclasses
from enum import IntEnum
import re
import typing
from uuid import UUID

from qgis.core import (
    QgsBasicNumericFormat,
    QgsFallbackNumericFormat,
    QgsFeedback,
    QgsLayoutTableColumn,
    QgsNumericFormat,
)
from qgis.PyQt import QtCore

from cplus_core.models.base import Activity, Scenario, ScenarioResult


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
    format_as_number: bool = True
    number_formatter: QgsNumericFormat = QgsFallbackNumericFormat

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

    @staticmethod
    def create_default_column(
        name: str, header: str, expression: str = ""
    ) -> "MetricColumn":
        """Creates a default metric column.

        :py:attr:`~format_as_number` is set to True and
        :py:attr:`~number_formatter` is set to two decimals
        places with a thousands' comma separator.

        :param name: Unique column name.
        :type name: str

        :param header: Label that will be used in the
        activity metrics table.
        :type header: str

        :param expression: Column expression. Default is an
        empty string.
        :type expression: str

        :returns: Metric column object.
        :rtype: MetricColumn
        """
        number_formatter = MetricColumn.default_formatter()

        column = MetricColumn(name, header, expression)
        column.number_formatter = number_formatter

        return column

    @staticmethod
    def default_formatter() -> QgsNumericFormat:
        """Returns a default number formatter with two
        decimals places and a comma for thousands'
        separator.

        :returns: Basic number formatter.
        :rtype: QgsNumericFormat
        """
        number_formatter = QgsBasicNumericFormat()
        number_formatter.setThousandsSeparator(",")
        number_formatter.setShowTrailingZeros(True)
        number_formatter.setNumberDecimalPlaces(2)

        return number_formatter


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

    @staticmethod
    def create() -> "MetricConfiguration":
        """Creates an empty metric configuration.

        :returns: An empty metric configuration.
        :rtype: MetricConfiguration
        """
        return MetricConfiguration([], [[]])

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
class MetricConfigurationProfile:
    """Profile with unique identifiers for a metrics configuration."""

    name: str
    config: MetricConfiguration

    @property
    def id(self) -> str:
        """Gets a cleaned profile name that has been stripped of spaces, special
        characters and in lower case.

        :returns: Cleaned version of the `name` attribute.
        :rtype: str
        """
        if not self.name.strip():
            return ""

        return (
            re.sub(r"[ %:/,\\\[\]<>*?]", "_", self.name.strip())
            .replace(" ", "")
            .lower()
        )

    def is_valid(self) -> bool:
        """Checks if the profile is valid.

        Checks if the name is specified or if the metric
        configuration is valid.

        :returns: True if the profile is valid else False.
        :rtype: bool
        """
        if not self.name.strip() or not self.config.is_valid():
            return False

        return True


@dataclasses.dataclass
class MetricProfileCollection:
    """Collection of `MetricConfigurationProfile` objects."""

    # Uses pofile ID
    current_profile: str = ""
    profiles: typing.List[MetricConfigurationProfile] = dataclasses.field(
        default_factory=list
    )

    @property
    def identifiers(self) -> typing.Dict[str, str]:
        """Gets a collection of profile IDs and corresponding names.

        Invalid profiles are excluded from the collection.

        :returns: A collection of profile IDs and corresponding names.
        :rtype: dict
        """
        return {
            profile.id: profile.name for profile in self.profiles if profile.is_valid()
        }

    def profile_exists(self, profile_id: str) -> bool:
        """Checks if a profile with the given ID exists in the collection.

        :returns: True if the profile ID exists else False.
        :rtype: bool
        """
        return profile_id in self.identifiers

    def add_profile(self, profile: MetricConfigurationProfile) -> bool:
        """Add a metric profile to the collection.

        It checks if there is an existing profile with a
        similar ID and if the profile is valid.

        :param profile: Metric profile to be added to the collection.
        :type profile: MetricConfigurationProfile

        :returns: True if the metric profile was successfully added else
        False if the profile is invalid or there exists one with a
        similar ID in the collection.
        :rtype: bool
        """
        if not profile.is_valid() or self.profile_exists(profile.id):
            return False

        self.profiles.append(profile)

        return True

    def remove_profile(self, profile_id: str) -> bool:
        """Remove a metric profile from the collection.

        :returns: True if the profile was successfully removed else
        False if the profile with the given ID does not exist in
        the collection.
        :rtype: bool
        """
        if not self.profile_exists(profile_id):
            return False

        self.profiles = [
            profile for profile in self.profiles if profile.id != profile_id
        ]

        return True

    def get_profile(
        self, profile_id: str
    ) -> typing.Optional[MetricConfigurationProfile]:
        """Gets a metric profile with the given ID.

        :param profile_id: ID of the metric profile to retrieve.
        :type profile_id: str

        :returns: Metric profile matching the given ID or None if
        not found.
        :rtype: MetricConfigurationProfile
        """
        profiles = [profile for profile in self.profiles if profile.id == profile_id]

        return profiles[0] if profiles else None

    def get_current_profile(self) -> typing.Optional[MetricConfigurationProfile]:
        """Helper function that retrieves the current metric profile if it has
        been specified in the attribute.

        :returns: Current metric profile object or None if not specified
        or not found in the collection.
        :rtype: MetricConfigurationProfile
        """
        if not self.current_profile:
            return None

        return self.get_profile(self.current_profile)


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
