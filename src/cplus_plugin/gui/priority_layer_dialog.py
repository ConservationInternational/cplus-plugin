# -*- coding: utf-8 -*-
"""
    Priority layer dialog
"""

import os
import uuid

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from qgis.PyQt.uic import loadUiType

from qgis.gui import QgsFileWidget

from ..conf import settings_manager, Settings
from ..utils import FileUtils, open_documentation
from ..definitions.defaults import ICON_PATH, PRIORITY_LAYERS, USER_DOCUMENTATION_SITE
from ..definitions.constants import PRIORITY_LAYERS_SEGMENT, USER_DEFINED_ATTRIBUTE

from .items_selection_dialog import ItemsSelectionDialog


DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/priority_layer_dialog.ui")
)


class PriorityLayerDialog(QtWidgets.QDialog, DialogUi):
    """Dialog that provide UI for priority layer details."""

    def __init__(
        self,
        layer=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.layer = layer

        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.map_layer_box.layerChanged.connect(self.map_layer_changed)

        ok_signals = [
            self.layer_name.textChanged,
            self.layer_description.textChanged,
            self.map_layer_file_widget.fileChanged,
            self.map_layer_box.layerChanged,
        ]

        for signal in ok_signals:
            signal.connect(self.update_ok_buttons)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        self._user_defined = True

        self.models = []
        self.initialize_ui()

    def map_layer_changed(self, layer):
        """Sets the file path of the selected layer in file path input

        :param layer: Qgis map layer
        :type layer: QgsMapLayer
        """
        if layer is not None:
            self.map_layer_file_widget.setFilePath(layer.source())

    def update_ok_buttons(self):
        """Responsible for changing the state of the
        dialog OK button.
        """
        enabled_state = (
            self.layer_name.text() != ""
            and self.layer_description.toPlainText() != ""
            and (
                self.map_layer_box.currentLayer() is not None
                or (
                    self.map_layer_file_widget.filePath() is not None
                    and self.map_layer_file_widget.filePath() is not ""
                )
            )
        )
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled_state)

    def initialize_ui(self):
        """Populate UI inputs when loading the dialog"""

        self.btn_help.setIcon(FileUtils.get_icon("mActionHelpContents.svg"))
        self.btn_help.clicked.connect(self.open_help)

        self.map_layer_file_widget.setStorageMode(QgsFileWidget.StorageMode.GetFile)

        self.select_models_btn.clicked.connect(self.open_layer_select_dialog)

        if self.layer is not None:
            layer_path = self.layer.get("path")

            layer_uuids = [layer.get("uuid") for layer in PRIORITY_LAYERS]
            if not os.path.isabs(layer_path) and self.layer.get("uuid") in layer_uuids:
                base_dir = settings_manager.get_value(Settings.BASE_DIR)
                layer_path = f"{base_dir}/{PRIORITY_LAYERS_SEGMENT}/{layer_path}"

            self.layer_name.setText(self.layer["name"])
            self.layer_description.setText(self.layer["description"])

            self.map_layer_file_widget.setFilePath(layer_path)

            all_models = settings_manager.get_all_implementation_models()

            for model in all_models:
                model_layer_uuids = [
                    layer.get("uuid")
                    for layer in model.priority_layers
                    if layer is not None
                ]
                if str(self.layer.get("uuid")) in model_layer_uuids:
                    self.models.append(model)

            self.set_selected_models(self.models)

            self._user_defined = self.layer.get(USER_DEFINED_ATTRIBUTE, True)

    def open_layer_select_dialog(self):
        """Opens priority layer item selection dialog"""
        model_select_dialog = ItemsSelectionDialog(self, self.layer, self.models)
        model_select_dialog.exec_()

    def set_selected_models(self, models, removed_models=[]):
        """Adds this dialog layer into the passed models and removes it from the
        unselected models passed as removed_models.

        :param models: Selected implementation models
        :type models: list

        :param removed_models: Implementation models that dialog
        layer should be removed from.
        :type removed_models: list

        """

        self.models = models

        models_names = [model.name for model in models]
        self.selected_models_le.setText(" , ".join(models_names))

        if not self.layer:
            return

        if len(removed_models) <= 0:
            all_models = settings_manager.get_all_implementation_models()
            removed_models = [
                model for model in all_models if model.name not in models_names
            ]

        for model in models:
            models_layer_uuids = [
                str(layer.get("uuid"))
                for layer in model.priority_layers
                if layer is not None
            ]
            if str(self.layer.get("uuid")) not in models_layer_uuids:
                model.priority_layers.append(self.layer)
                settings_manager.save_implementation_model(model)
        for model in removed_models:
            for layer in model.priority_layers:
                if str(layer.get("uuid")) == str(self.layer.get("uuid")):
                    model.priority_layers.remove(layer)
                    settings_manager.save_implementation_model(model)

    def accept(self):
        """Handles logic for adding new priority layer and edit existing one"""
        layer_id = uuid.uuid4()
        layer_groups = []
        layer = {}
        if self.layer is not None:
            layer_id = self.layer.get("uuid")
            layer_groups = self.layer.get("groups", [])

        layer["uuid"] = str(layer_id)
        layer["name"] = self.layer_name.text()
        layer["description"] = self.layer_description.toPlainText()
        layer["groups"] = layer_groups

        layer["path"] = self.map_layer_file_widget.filePath()
        layer[USER_DEFINED_ATTRIBUTE] = self._user_defined

        settings_manager.save_priority_layer(layer)

        self.layer = layer
        self.set_selected_models(self.models)

        super().accept()

    def open_help(self):
        """Opens the user documentation for the plugin in a browser"""
        open_documentation(USER_DOCUMENTATION_SITE)
