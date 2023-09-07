from qgis.PyQt.QtWidgets import QTreeWidget, QTreeWidgetItem
from qgis.PyQt.QtGui import QDropEvent
from qgis.PyQt import QtCore


class CustomTreeWidget(QTreeWidget):
    child_dragged_dropped = QtCore.pyqtSignal(QTreeWidgetItem, list)

    def __int__(self):
        super()

    def dropEvent(self, event: QDropEvent):
        current_index = self.indexAt(event.pos())
        target_item = self.itemFromIndex(current_index)

        source = event.source()
        source_items = source.selectedItems() if source else None

        if target_item is not None and source_items is not None:
            self.child_dragged_dropped.emit(target_item, source_items)
