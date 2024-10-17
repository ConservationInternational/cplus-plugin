# -*- coding: utf-8 -*-
"""
MVC models for the metrics builder.
"""
from enum import IntEnum
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


class MoveDirection(IntEnum):
    """Move an item up or down."""

    UP = 0
    DOWN = 1


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
        existing_column = self.column_exists(column_item.name)
        if existing_column:
            return None

        self.appendRow(column_item)

        return column_item

    def column_exists(self, name: str) -> bool:
        """Checks if a column with the given name exists.

        :param name: Name of the column.
        :type name: str

        :returns: True if the column name exists, else False.
        :rtype: bool
        """
        item = self.item_from_name(name)

        if item is None:
            return False

        return True

    def item_from_name(self, name: str) -> typing.Optional[MetricColumnListItem]:
        """Gets the model item from the column name.

        It performs a case-insensitive search of
        the first matching model item.

        :param name: Name of the column.
        :type name:str

        :returns: The first matching model item if
        found else None.
        :rtype: MetricColumnListItem
        """
        items = self.findItems(name, QtCore.Qt.MatchFixedString)

        if len(items) > 0:
            return items[0]

        return None

    def remove_column(self, name: str) -> bool:
        """Removes the column matching the given name.

        :param name: Name of the column to be removed.
        :type name: str

        :returns: True if the column was successfully
        removed else False if there is no column matching
        the given name.
        :rtype: bool
        """
        item = self.item_from_name(name)

        if item is None:
            return False

        return self.removeRows(item.row(), 1)

    def move_column_up(self, row: int) -> int:
        """Moves the column item in the given row one level up.

        :param row: Column item in the given row to be moved up.
        :type row: int

        :returns: New position of the column item or -1 if the column
        item was not moved up.
        :rtype: int
        """
        return self.move_column(row, MoveDirection.UP)

    def move_column_down(self, row: int) -> int:
        """Moves the column item in the given row one level down.

        :param row: Column item in the given row to be moved down.
        :type row: int

        :returns: New position of the column item or -1 if the column
        item was not moved down.
        :rtype: int
        """
        return self.move_column(row, MoveDirection.DOWN)

    def move_column(self, row: int, direction: MoveDirection) -> int:
        """Moves the column item in the given row one by a level
        up or down as defined in the direction.

        :param row: Position of the column item to be moved.
        :type row: int

        :param direction: Direction to move the column item.
        :type direction: MoveDirection

        :returns: New position of the column item or -1 if the column
        item was not moved.
        :rtype: int
        """
        if direction == MoveDirection.UP and row < 1:
            return -1
        elif direction == MoveDirection.DOWN and row >= self.rowCount() - 1:
            return -1

        item = self.takeRow(row)
        if item is None:
            return -1

        if direction == MoveDirection.UP:
            new_position = row - 1
        elif direction == MoveDirection.DOWN:
            new_position = row + 1

        self.insertRow(new_position, item)

        return new_position
