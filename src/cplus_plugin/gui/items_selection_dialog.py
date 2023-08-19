# -*- coding: utf-8 -*-

"""
 Item selection dialog  file
"""

import os
from qgis.PyQt import QtCore, QtGui, QtWidgets, QtNetwork

from qgis.core import Qgis, QgsProject

from qgis.PyQt.uic import loadUiType

from ..conf import settings_manager, Settings

from ..utils import log, tr


DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/items_selection_dialog.ui")
)


class ItemsSelectionDialog(QtWidgets.QDialog, DialogUi):
    """Dialog for handling items selection"""

    def __init__(self, parent):
        """Constructor"""
        super().__init__()
        self.setupUi(self)
        self.parent = parent

        select_all_btn = QtWidgets.QPushButton(tr("Select All"))
        select_all_btn.setToolTip(tr("Select the all listed items"))
        select_all_btn.clicked.connect(self.select_all_clicked)
        self.mButtonBox.addButton(select_all_btn, QtWidgets.QDialogButtonBox.ActionRole)

        clear_all_btn = QtWidgets.QPushButton(tr("Clear Selection"))
        clear_all_btn.setToolTip(tr("Clear the current selection"))
        clear_all_btn.clicked.connect(self.clear_all_clicked)
        self.mButtonBox.addButton(clear_all_btn, QtWidgets.QDialogButtonBox.ActionRole)

        toggle_selection_btn = QtWidgets.QPushButton(tr("Toggle Selection"))
        toggle_selection_btn.clicked.connect(self.toggle_selection_clicked)
        self.mButtonBox.addButton(
            toggle_selection_btn, QtWidgets.QDialogButtonBox.ActionRole
        )

        self.mButtonBox.accepted.connect(self.accept)

        self.set_items()

        profile = settings_manager.get_current_profile()
        custom_properties = settings_manager.get_templates_custom_properties(
            self.parent.template.id, profile.id
        )

        for index in range(self.list_widget.count()):
            item_item = self.list_widget.item(index)
            if custom_properties["item_names"] is not None:
                if item_item.text() in custom_properties["item_names"]:
                    item_item.setCheckState(QtCore.Qt.Checked)

    def set_items(self):
        items_values = QgsProject.instance().mapItems().values()

        item_names = [f"{item.name()}" for item in items_values]
        for name in item_names:
            list_widget_item = QtWidgets.QListWidgetItem(name)
            list_widget_item.setFlags(
                list_widget_item.flags() | QtCore.Qt.ItemIsUserCheckable
            )
            list_widget_item.setCheckState(QtCore.Qt.Unchecked)
            self.list_widget.addItem(list_widget_item)

    def selected_items(self):
        item_items_text = []
        for index in range(self.list_widget.count()):
            item_item = self.list_widget.item(index)
            if item_item.checkState() == QtCore.Qt.Checked:
                item_items_text.append(item_item.text())
        item_names = ",".join(item_items_text)
        items = [
            item
            for item in QgsProject.instance().mapItems().values()
            if item.name() in item_names
        ]
        return items

    def accept(self):
        self.parent.set_selected_items(self.selected_items())
        super().accept()

    def select_all_clicked(self):
        for item_index in range(self.list_widget.count()):
            item_item = self.list_widget.item(item_index)
            item_item.setCheckState(QtCore.Qt.Checked)

    def clear_all_clicked(self):
        for item_index in range(self.list_widget.count()):
            item_item = self.list_widget.item(item_index)
            item_item.setCheckState(QtCore.Qt.Unchecked)

    def toggle_selection_clicked(self):
        for item_index in range(self.list_widget.count()):
            item_item = self.list_widget.item(item_index)
            state = item_item.checkState()
            if state == QtCore.Qt.Checked:
                item_item.setCheckState(QtCore.Qt.Unchecked)
            elif state == QtCore.Qt.Unchecked:
                item_item.setCheckState(QtCore.Qt.Checked)
