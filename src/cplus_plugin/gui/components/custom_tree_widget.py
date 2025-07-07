# -*- coding: utf-8 -*-

"""
 Custom tree widget class
"""

from qgis.PyQt.QtWidgets import QTreeWidget, QTreeWidgetItem
from qgis.PyQt.QtGui import QDropEvent
from qgis.PyQt import QtCore


SORT_ROLE = QtCore.Qt.UserRole + 2


class SortableTreeWidgetItem(QTreeWidgetItem):
    """Tree item that allows the use of a custom SORT_ROLE to sort items."""

    def __lt__(self, other) -> bool:
        column = self.treeWidget().sortColumn()
        return self.data(column, SORT_ROLE) < other.data(column, SORT_ROLE)


class CustomTreeWidget(QTreeWidget):
    """Class for the custom tree widget object, extending the QTreeWidget class
    and overriding the drag and drop behaviour.
    """

    child_dragged_dropped = QtCore.pyqtSignal(QTreeWidgetItem, list)

    def __int__(self):
        super()

    def dropEvent(self, event: QDropEvent):
        """Overrides the QTreeWidget dropEvent function, fetches the source item list
        and the target item and then emits a signal that can used to access the
        event source and target.

        :param event: Drop event object
        :type event: QDropEvent
        """
        current_index = self.indexAt(event.pos())
        target_item = self.itemFromIndex(current_index)

        source = event.source()
        source_items = source.selectedItems() if source else None

        if target_item is not None and source_items is not None:
            self.child_dragged_dropped.emit(target_item, source_items)
