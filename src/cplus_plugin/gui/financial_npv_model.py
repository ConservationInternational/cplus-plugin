# -*- coding: utf-8 -*-
"""
View model for computation of financial NPV values.
"""
import os
import typing

from qgis.PyQt import QtCore, QtGui

from ..definitions.constants import (
    DISCOUNTED_VALUE_HEADER,
    MAX_YEARS,
    TOTAL_PROJECTED_COSTS_HEADER,
    TOTAL_PROJECTED_REVENUES_HEADER,
    YEAR_HEADER,
)

from ..utils import FileUtils, tr


class FinancialNpvModel(QtGui.QStandardItemModel):
    """View model for costs and revenues used in NPV computation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)

        # Headers
        self.setHorizontalHeaderLabels(
            [
                tr(YEAR_HEADER),
                tr(TOTAL_PROJECTED_REVENUES_HEADER),
                tr(TOTAL_PROJECTED_COSTS_HEADER),
                tr(DISCOUNTED_VALUE_HEADER),
            ]
        )

    def add_year_row(self) -> int:
        """Adds a new row for the year.

        The year number is automatically set.

        :returns: The newly added row number, or
        -1 if the row was not added.
        :rtype: int
        """
        if self.rowCount() >= MAX_YEARS:
            return -1

        year_number = self.rowCount() + 1
        year_item = QtGui.QStandardItem(str(year_number))
        year_item.setEditable(False)
        year_item.setTextAlignment(QtCore.Qt.AlignCenter)
        year_background = year_item.background()
        year_background.setColor(QtCore.Qt.lightGray)
        year_background.setStyle(QtCore.Qt.SolidPattern)
        year_item.setBackground(year_background)

        revenue_item = QtGui.QStandardItem()
        revenue_item.setEditable(True)
        revenue_item.setTextAlignment(QtCore.Qt.AlignCenter)

        cost_item = QtGui.QStandardItem()
        cost_item.setEditable(True)
        cost_item.setTextAlignment(QtCore.Qt.AlignCenter)

        discount_item = QtGui.QStandardItem()
        discount_item.setEditable(False)
        discount_item.setTextAlignment(QtCore.Qt.AlignCenter)
        discount_background = discount_item.background()
        discount_background.setColor(QtCore.Qt.lightGray)
        discount_background.setStyle(QtCore.Qt.SolidPattern)
        discount_item.setBackground(discount_background)

        self.appendRow([year_item, revenue_item, cost_item, discount_item])

        return year_number

    def append_years(self, number_years: int):
        """Appends new rows based on the number of years specified.

        :param number_years: Number of rows to be added.
        :type number_years: int
        """
        for i in range(number_years):
            row_number = self.add_year_row()
            if row_number == -1:
                break

    def set_number_of_years(self, number_years: int):
        """Sets the number of years by adding or removing rows to
        match the number of years.

        :param number_years: Number of years to be used in
        the computation.
        :type number_years: int
        """
        if self.rowCount() < number_years:
            # Append additional years
            additional_years = number_years - self.rowCount()
            self.append_years(additional_years)
        elif self.rowCount() > number_years:
            # Remove extra years
            remove_years = self.rowCount() - number_years
            self.removeRows(self.rowCount() - remove_years, remove_years)
