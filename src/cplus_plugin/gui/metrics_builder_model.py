# -*- coding: utf-8 -*-
"""
MVC models for the metrics builder.
"""
from enum import IntEnum
import typing

from qgis.PyQt import QtCore, QtGui

from ..definitions.constants import ACTIVITY_NAME

from ..models.base import Activity
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


class VerticalMoveDirection(IntEnum):
    """Move an item up or down."""

    UP = 0
    DOWN = 1


class HorizontalMoveDirection(IntEnum):
    """Move an item left or right."""

    LEFT = 0
    RIGHT = 1


class MetricColumnListModel(QtGui.QStandardItemModel):
    """View model for list-based metric column objects."""

    column_added = QtCore.pyqtSignal(MetricColumnListItem)
    column_removed = QtCore.pyqtSignal(int)
    column_moved = QtCore.pyqtSignal(MetricColumnListItem, VerticalMoveDirection)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)

    @property
    def column_items(self) -> typing.List[MetricColumnListItem]:
        """Gets all the column items in the model.

        :returns: All the column items in the model.
        :rtype: typing.List[MetricColumnListItem]
        """
        return [self.item(r) for r in range(self.rowCount())]

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

        self.column_added.emit(column_item)

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

        status = self.removeRows(item.row(), 1)

        if status:
            self.column_removed.emit(item)

        return status

    def move_column_up(self, row: int) -> int:
        """Moves the column item in the given row one level up.

        :param row: Column item in the given row to be moved up.
        :type row: int

        :returns: New position of the column item or -1 if the column
        item was not moved up.
        :rtype: int
        """
        return self.move_column(row, VerticalMoveDirection.UP)

    def move_column_down(self, row: int) -> int:
        """Moves the column item in the given row one level down.

        :param row: Column item in the given row to be moved down.
        :type row: int

        :returns: New position of the column item or -1 if the column
        item was not moved down.
        :rtype: int
        """
        return self.move_column(row, VerticalMoveDirection.DOWN)

    def move_column(self, row: int, direction: VerticalMoveDirection) -> int:
        """Moves the column item in the given row one by a level
        up or down as defined in the direction.

        :param row: Position of the column item to be moved.
        :type row: int

        :param direction: Direction to move the column item.
        :type direction: VerticalMoveDirection

        :returns: New position of the column item or -1 if the column
        item was not moved.
        :rtype: int
        """
        if direction == VerticalMoveDirection.UP and row < 1:
            return -1
        elif direction == VerticalMoveDirection.DOWN and row >= self.rowCount() - 1:
            return -1

        item = self.takeRow(row)
        if item is None:
            return -1

        if direction == VerticalMoveDirection.UP:
            new_position = row - 1
        elif direction == VerticalMoveDirection.DOWN:
            new_position = row + 1

        self.insertRow(new_position, item)

        self.column_moved.emit(item, direction)

        return new_position


class ActivityNameTableItem(QtGui.QStandardItem):
    """Represents an activity name in the metrics table.."""

    def __init__(self, name: str):
        super().__init__()

        self.setEditable(False)

        self.setTextAlignment(QtCore.Qt.AlignCenter)

        background = self.background()
        background.setColor(QtCore.Qt.lightGray)
        background.setStyle(QtCore.Qt.SolidPattern)


class ActivityMetricTableModel(QtGui.QStandardItemModel):
    """View model for activity metrics in a table."""

    def __init__(self, parent=None, columns: typing.List[MetricColumn] = None):
        super().__init__(parent)

        self.setColumnCount(1)
        # Add default activity name header
        self.setHorizontalHeaderLabels([tr(ACTIVITY_NAME)])

        self._metric_columns = []
        if columns is not None:
            self._metric_columns = columns

    @property
    def metric_columns(self) -> typing.List[MetricColumn]:
        """Gets the metric columns used in the model to
        define the headers.

        :returns: Metric columns used in the model.
        :rtype: typing.List[MetricColumn]
        """
        return list(self._metric_columns)

    def add_column(self, column: MetricColumn):
        """Adds a column to the model based on the information
        in the metric column.

        :param column: Metric column containing information
        for defining the new column.
        :type column: MetricColumn
        """
        headers = [
            self.headerData(c, QtCore.Qt.Horizontal) for c in range(self.columnCount())
        ]
        headers.append(column.header)
        self.setHorizontalHeaderLabels(headers)
        self._metric_columns.append(column)

    def remove_column(self, index: int) -> bool:
        """Remove the column at the specified index.

        The index will be normalized to reflect the first
        metric column since index zero is reserved for the
        activity name column which is fixed.

        :param index: Index of the column to be removed.
        :type index: int

        :returns: True if the column was successfully
        removed else False.
        :rtype: bool
        """
        if index == -1:
            return False

        model_index = index + 1

        status = self.removeColumns(model_index, 1)

        del self._metric_columns[index]

        return status

    def update_column_properties(self, index: int, column: MetricColumn):
        """Updates the properties of an underlying metric column
        in the model.

        :param index: Index of the column to the updated.
        :type index: int

        :param column: Updated column metric object.
        :type column: MetricColumn
        """
        if index == -1:
            return False

        # Update header
        model_index = index + 1
        self.setHeaderData(
            model_index, QtCore.Qt.Horizontal, column.header, QtCore.Qt.DisplayRole
        )
        self._metric_columns[index] = column

    def add_activity(self, activity: Activity) -> bool:
        """Adds an activity row in the activity metrics table.

        :param activity: Activity to be added.
        :type activity: Activity

        :returns: True if the activity was successfully added
        else False.
        :rtype: bool
        """
        pass

    def move_column(
        self, current_index: int, direction: HorizontalMoveDirection
    ) -> int:
        """MOve the column in the specified index left or right depending on the
        move direction.

        :param current_index: Index of the column to be moved.
        :type current_index: int

        :param direction: Direction to move the column, either left or right.
        :type direction: HorizontalMoveDirection

        :returns: New position of the column or -1 if the column
        item was not moved.
        :rtype: int
        """
        # The activity name column will always be on the extreme left (LTR)
        if current_index <= 1 or current_index >= self.columnCount() - 1:
            return -1

        if direction == HorizontalMoveDirection.LEFT:
            new_index = current_index - 1
        else:
            new_index = current_index + 1

        # Move items
        column_items = self.takeColumn(current_index)
        self.insertColumn(new_index, column_items)

        # Move column header
        header_item = self.takeHorizontalHeaderItem(current_index)
        self.setHorizontalHeaderItem(new_index, header_item)

        return new_index

    def move_column_left(self, current_index: int) -> int:
        """Convenience method for moving a column to the left.

        :param current_index: Index of the column to be moved.
        :type current_index: int

        :returns: New position of the column or -1 if the column
        item was not moved.
        :rtype: int
        """
        return self.move_column(current_index, HorizontalMoveDirection.LEFT)

    def move_column_right(self, current_index: int) -> int:
        """Convenience method for moving a column to the right.

        :param current_index: Index of the column to be moved.
        :type current_index: int

        :returns: New position of the column or -1 if the column
        item was not moved.
        :rtype: int
        """
        return self.move_column(current_index, HorizontalMoveDirection.RIGHT)
