# -*- coding: utf-8 -*-
"""Scenario comparison table information."""

from numbers import Number
import typing

from qgis.core import QgsBasicNumericFormat, QgsLayoutTableColumn, QgsTableCell
from qgis.PyQt import QtCore, QtGui

from ...models.base import ScenarioResult
from ...models.helpers import layer_from_scenario_result
from ...models.report import ScenarioAreaInfo
from ...utils import calculate_raster_value_area, log, tr


class ScenarioComparisonTableInfo(QtCore.QObject):
    """Get area information for the scenarios in the corresponding
    ScenarioResult objects.
    """

    NOT_AVAILABLE_STR = "N/A"
    AREA_DECIMAL_PLACES = 2

    area_calculated = QtCore.pyqtSignal(ScenarioAreaInfo)

    def __init__(self, results: typing.List[ScenarioResult], parent=None):
        super().__init__(parent)

        self._scenario_results = results
        self._activity_header_info = []
        self._contents = []
        self._area_calculated = False

        # Extract the header information
        for result in self._scenario_results:
            for activity in result.scenario.weighted_activities:
                activity_info = (
                    str(activity.uuid),
                    activity.name,
                    activity.style_pixel_value,
                )
                if activity_info in self._activity_header_info:
                    continue
                self._activity_header_info.append(activity_info)

    @property
    def columns(self) -> typing.List[QgsLayoutTableColumn]:
        """Headers for the scenario comparison table.

        The columns start with one titled 'Scenario' which will contain
        the scenario name in the rows.

        :returns: Table headers based on the activities in the scenarios.
        :rtype: list
        """
        columns = []

        scenario_name_column = QgsLayoutTableColumn(tr("Scenario"))
        columns.append(scenario_name_column)

        for activity_header in self._activity_header_info:
            activity_column = QgsLayoutTableColumn(activity_header[1])
            columns.append(activity_column)

        return columns

    def contents(self) -> typing.List[typing.List[QgsTableCell]]:
        """Calculates the area of scenario layers and creates the
        corresponding table rows for use in a QgsLayoutTable
        derivative.

        The `area_calculated` signal is emitted once for every scenario
        area calculated or acquired using alternative mechanisms.

        This function is idempotent and will only return the
        results from the first call. Subsequent calls will return
        the same result.

        :returns: A nested list containing area information for
        each scenario.
        :rtype: list
        """
        if self._area_calculated:
            return self._contents

        result_data = []

        for result in self._scenario_results:
            layer = layer_from_scenario_result(result)
            if layer is None:
                msg = (
                    f"Unable to calculate area for scenario comparison a"
                    f"s layer for {result.scenario.name} could not "
                    f"be created."
                )
                log(msg)
                continue

            area_info = calculate_raster_value_area(layer)
            int_area_info = {
                int(pixel_value): area for pixel_value, area in area_info.items()
            }
            scenario_area_info = ScenarioAreaInfo(
                result.scenario.name, result.scenario.uuid, int_area_info
            )
            self.area_calculated.emit(scenario_area_info)

            if len(int_area_info) == 0:
                msg = "No activity areas from the calculation"
                log(msg)

            row_data = []
            row_data.append(QgsTableCell(result.scenario.name))
            for header_info in self._activity_header_info:
                pixel_value = header_info[2]
                if pixel_value in int_area_info:
                    activity_area = int_area_info[pixel_value]
                else:
                    activity_area = self.NOT_AVAILABLE_STR

                area_cell = QgsTableCell(activity_area)
                if isinstance(activity_area, Number):
                    number_format = QgsBasicNumericFormat()
                    number_format.setThousandsSeparator(",")
                    number_format.setShowTrailingZeros(True)
                    number_format.setNumberDecimalPlaces(self.AREA_DECIMAL_PLACES)
                    area_cell.setNumericFormat(number_format)

                row_data.append(area_cell)

            result_data.append(row_data)

        self._contents = result_data
        self._area_calculated = True

        return self._contents
