# -*- coding: utf-8 -*-

"""
 Item selection dialog  file
"""

import os
from qgis.PyQt import QtCore, QtGui, QtWidgets, QtNetwork

from qgis.PyQt.uic import loadUiType

from ..conf import settings_manager

from ..utils import tr


DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/items_selection_dialog.ui")
)


class ItemsSelectionDialog(QtWidgets.QDialog, DialogUi):
    """Dialog for handling items selection"""

    def __init__(self, parent, layer=None, models=[]):
        """Constructor"""
        super().__init__()
        self.setupUi(self)
        self.parent = parent
        self.layer = layer
        self.models = models

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

        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            model_uuid = item.data(QtCore.Qt.UserRole)
            model = settings_manager.get_implementation_model(str(model_uuid))

            layer_model_uuids = [model.uuid for model in self.models]
            model_layer_uuids = [layer.get("uuid") for layer in model.priority_layers]

            if (
                self.layer is not None
                and str(self.layer.get("uuid")) in model_layer_uuids
            ) or (model.uuid in layer_model_uuids):
                item.setCheckState(QtCore.Qt.Checked)

    def set_items(self):
        """Sets the item list in the dialog"""
        models = settings_manager.get_all_implementation_models()

        for model in models:
            list_widget_item = QtWidgets.QListWidgetItem(model.name)
            list_widget_item.setFlags(
                list_widget_item.flags() | QtCore.Qt.ItemIsUserCheckable
            )
            list_widget_item.setData(QtCore.Qt.UserRole, model.uuid)
            list_widget_item.setCheckState(QtCore.Qt.Unchecked)
            self.list_widget.addItem(list_widget_item)

    def selected_items(self):
        """Returns the selected items from the dialog"""
        models = settings_manager.get_all_implementation_models()
        items_text = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == QtCore.Qt.Checked:
                items_text.append(item.text())
        item_names = ",".join(items_text)
        items = [item for item in models if item.name in item_names]
        return items

    def unselected_items(self):
        """Returns unselected items from the dialog"""
        models = settings_manager.get_all_implementation_models()
        items_text = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == QtCore.Qt.Unchecked:
                items_text.append(item.text())
        item_names = ",".join(items_text)
        items = [item for item in models if item.name in item_names]
        return items

    def accept(self):
        """Saves the item selection"""
        self.parent.set_selected_models(self.selected_items(), self.unselected_items())
        super().accept()

    def select_all_clicked(self):
        """Slot for handling selection for all items."""
        for item_index in range(self.list_widget.count()):
            item_item = self.list_widget.item(item_index)
            item_item.setCheckState(QtCore.Qt.Checked)

    def clear_all_clicked(self):
        """Slot for handling clear fselection for all items."""
        for item_index in range(self.list_widget.count()):
            item_item = self.list_widget.item(item_index)
            item_item.setCheckState(QtCore.Qt.Unchecked)

    def toggle_selection_clicked(self):
        """Toggles all the current items selection."""
        for item_index in range(self.list_widget.count()):
            item_item = self.list_widget.item(item_index)
            state = item_item.checkState()
            if state == QtCore.Qt.Checked:
                item_item.setCheckState(QtCore.Qt.Unchecked)
            elif state == QtCore.Qt.Unchecked:
                item_item.setCheckState(QtCore.Qt.Checked)
