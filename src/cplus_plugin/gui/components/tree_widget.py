from qgis.PyQt.QtWidgets import QTreeWidget, QTreeWidgetItem
from qgis.PyQt.QtGui import QDropEvent
from qgis.PyQt import QtCore


class TreeWidget(QTreeWidget):
    child_draged_droped: QtCore.pyqtSignal(
        QTreeWidgetItem, int, int, QTreeWidgetItem, int
    )

    def __int__(self):
        super()

    def dropEvent(self, event: QDropEvent):
        kids = self.selectedItems()
        if kids.size() == 0:
            return
        start = self.indexFromItem(kids.at(0)).row()
        end = start
        parent = kids.at(0).parent()

        QTreeWidget.dropEvent(event)

        row = self.indexFromItem(kids.at(0)).row()
        destination = kids.at(0).parent()

        if not parent or not destination:
            event.setDropAction(QtCore.Qt.IgnoreAction)
            return

        self.child_draged_droped.emit(parent, start, end, destination, row)
