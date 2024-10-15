# -*- coding: utf-8 -*-
"""
MVC models for the metrics builder.
"""
import os
import typing

from qgis.PyQt import QtCore, QtGui

from ..models.report import MetricColumn

from ..utils import FileUtils, tr


class MetricColumnListItem(QtGui.QStandardItem):
    """Represents a single carbon layer path."""

    def __init__(self, name_column: typing.Union[str, MetricColumn]):
        super().__init__()

        self._column = None
        if isinstance(name_column, str):
            self._column = MetricColumn(name_column, name_column, "")
        else:
            self._column = name_column

        self.name = self._column.name

        column_icon = FileUtils.get_icon("table_column.svg")
        self.setIcon(column_icon)

    @property
    def name(self) -> str:
        """Gets the name of the column.

        :returns: The name of the column.
        :rtype: str
        """
        return self._column.name

    @name.setter
    def name(self, name: str):
        """Update the column name.

        :param name: Name of the column.
        :type name: str
        """
        self._column.name = name
        self.setText(name)
        self.setToolTip(name)

    @property
    def header(self) -> str:
        """Gets the column header.

        :returns: The column header.
        :rtype: str
        """
        return self._column.header

    @header.setter
    def header(self, header: str):
        """Update the column header.

        :param header: Header of the column.
        :type header: str
        """
        self._column.header = header

    @property
    def alignment(self) -> QtCore.Qt.AlignmentFlag:
        """Gest the alignment of the column text.

        :returns: The alignment of the column text.
        :rtype: QtCore.Qt.AlignmentFlag
        """
        return self._column.alignment

    @alignment.setter
    def alignment(self, alignment: QtCore.Qt.AlignmentFlag):
        """Update the column alignment.

        :param alignment: Alignment of the column text.
        :type alignment: QtCore.Qt.AlignmentFlag
        """
        self._column.alignment = alignment

    @property
    def expression(self) -> str:
        """Gets the column-wide expression used by activity
        metrics.

        :returns: The column-wide expression used by the activity
        metrics.
        :rtype: str
        """
        return self._column.expression

    @expression.setter
    def expression(self, expression: str):
        """Set the column-wide expression to be used by the activity
        metrics.

        :param expression: Column-wide expression to be used for
        activity metrics.
        :type expression: str
        """
        self._column.expression = expression

    @property
    def auto_calculated(self):
        """Indicates whether the column value is auto-calculated.

        :returns: True if the column value is auto-calculated else
        False.
        :rtype: bool
        """
        return self._column.auto_calculated

    @auto_calculated.setter
    def auto_calculated(self, auto_calculated: bool):
        """Set whether the column value is auto-calculated.

        :param auto_calculated: True if the column value is
        auto-calculated else False.
        :type auto_calculated: bool
        """
        self._column.auto_calculated = auto_calculated

    @property
    def is_valid(self) -> bool:
        """Returns the validity status of the item.

        The name and header label should be defined.

        :returns: True if valid, else False.
        :rtype: bool
        """
        if not self._column.name or not self._column.header:
            return False

        return True

    @property
    def model(self) -> MetricColumn:
        """Gets the underlying data model used in the item.

        :returns: The underlying data model used in the item.
        :rtype: MetricColumn
        """
        return self._column


class MetricColumnListModel(QtGui.QStandardItemModel):
    """View model for list-based metric column objects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)

    def add_new_column(self, name_column: typing.Union[str, MetricColumn]) -> bool:
        """Adds a new column to the model.

        :param name_column: Name of the column or metric column
        data model.
        :type name_column:

        :returns: True if the column was successfully added
        due to an already existing column with a similar name,
        else False.
        :rtype: bool
        """
        column_item = MetricColumnListItem(name_column)
        item = self.add_column(column_item)
        if item is None:
            return False

        return True

    def add_column(
        self, column_item: MetricColumnListItem
    ) -> typing.Optional[MetricColumnListItem]:
        """Adds a column item to the model.

        :param column_item: Column item to be added to the model.
        :type column_item: MetricColumnListItem

        :returns: The item successfully added to the model else
        None if the item could not be successfully added due to
        an already existing name in the model.
        :rtype: MetricColumnListItem or None
        """
        self.appendRow(column_item)

        return column_item
