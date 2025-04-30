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
from ..utils import FileUtils, open_documentation, log
from ..models.base import PriorityLayerType
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
            self.cbo_default_layer.currentIndexChanged,
        ]

        for signal in ok_signals:
            signal.connect(self.update_ok_buttons)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        self._user_defined = True

        self.ncs_pathways = []
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
                (
                    self.map_layer_box.currentLayer() is not None
                    or (
                        self.map_layer_file_widget.filePath() is not None
                        and self.map_layer_file_widget.filePath() is not ""
                    )
                )
                or self._get_selected_default_layer() != {}
            )
        )
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled_state)

    def _disable_input_controls(self):
        """Disable key controls for PWL properties."""
        self.layer_name.setEnabled(False)
        self.map_layer_file_widget.setEnabled(False)
        self.map_layer_box.setEnabled(False)
        self.selected_pathways_le.setEnabled(False)
        self.select_pathways_btn.setEnabled(False)

    def initialize_ui(self):
        """Populate UI inputs when loading the dialog"""

        self.btn_help.setIcon(FileUtils.get_icon("mActionHelpContents_green.svg"))
        self.btn_help.clicked.connect(self.open_help)

        self.map_layer_file_widget.setStorageMode(QgsFileWidget.StorageMode.GetFile)

        self.select_pathways_btn.clicked.connect(self.open_layer_select_dialog)

        default_priority_layers = settings_manager.get_default_layers("priority_layer")
        self.cbo_default_layer.addItem("")
        self.cbo_default_layer.addItems([p["name"] for p in default_priority_layers])
        self.cbo_default_layer.setCurrentIndex(0)
        self.cbo_default_layer.currentIndexChanged.connect(
            self._on_default_layer_selection_changed
        )

        if self.layer is not None:
            # If its an NPV PWL, then disable controls as the information is managed
            # through the NPV manager. Only the description can be updated.
            pwl_type = self.layer.get("type", PriorityLayerType.DEFAULT.value)
            if pwl_type == PriorityLayerType.NPV:
                self._disable_input_controls()

            layer_path = self.layer.get("path")
            if layer_path.startswith("cplus://"):
                layer_uuid = layer_path.replace("cplus://", "")
                for i, layer in enumerate(default_priority_layers):
                    if layer["layer_uuid"] == layer_uuid:
                        self.cbo_default_layer.setCurrentIndex(i + 1)
                        break
            else:
                layer_uuids = [layer.get("uuid") for layer in PRIORITY_LAYERS]
                if (
                    not os.path.isabs(layer_path)
                    and self.layer.get("uuid") in layer_uuids
                ):
                    base_dir = settings_manager.get_value(Settings.BASE_DIR)
                    layer_path = f"{base_dir}/{PRIORITY_LAYERS_SEGMENT}/{layer_path}"
                self.map_layer_file_widget.setFilePath(layer_path)

            self.layer_name.setText(self.layer["name"])
            self.layer_description.setText(self.layer["description"])

            all_pathways = settings_manager.get_all_ncs_pathways()

            for pathway in all_pathways:
                model_layer_uuids = [
                    layer.get("uuid")
                    for layer in pathway.priority_layers
                    if layer is not None
                ]
                if str(self.layer.get("uuid")) in model_layer_uuids:
                    self.ncs_pathways.append(pathway)

            self.set_selected_items(self.ncs_pathways)

            self._user_defined = self.layer.get(USER_DEFINED_ATTRIBUTE, True)

    def open_layer_select_dialog(self):
        """Opens priority layer item selection dialog"""
        pathway_select_dialog = ItemsSelectionDialog(self, self.layer, self.ncs_pathways)
        pathway_select_dialog.exec_()

    def set_selected_items(self, pathways, removed_pathways=None):
        """Adds this dialog layer into the passed pathways and removes it from the
        unselected pathways passed as removed_pathways.

        :param pathways: Selected pathways.
        :type pathways: list

        :param removed_pathways: Pathways that dialog
        layer should be removed from.
        :type removed_pathways: list
        """
        removed_pathways = removed_pathways or []

        self.ncs_pathways = pathways

        pathway_names = [pathway.name for pathway in pathways]
        self.selected_pathways_le.setText(" , ".join(pathway_names))

        if not self.layer:
            return

        if len(removed_pathways) <= 0:
            all_pathways = settings_manager.get_all_ncs_pathways()
            removed_pathways = [
                pathway
                for pathway in all_pathways
                if pathway.name not in pathway_names
            ]

        for pathway in pathways:
            models_layer_uuids = [
                str(layer.get("uuid"))
                for layer in pathway.priority_layers
                if layer is not None
            ]
            if (
                self.layer is not None
                and str(self.layer.get("uuid")) not in models_layer_uuids
            ):
                pathway.priority_layers.append(self.layer)
                settings_manager.save_ncs_pathway(pathway)

            # remove redundant priority layers
            for layer in pathway.priority_layers:
                if layer is not None:
                    layer_settings = settings_manager.get_priority_layer(
                        str(layer.get("uuid"))
                    )
                    if layer_settings is None:
                        pathway.priority_layers.remove(layer)
                        settings_manager.save_ncs_pathway(pathway)

        for pathway in removed_pathways:
            for layer in pathway.priority_layers:
                if layer is None:
                    continue
                if str(layer.get("uuid")) == str(self.layer.get("uuid")):
                    pathway.priority_layers.remove(layer)
                    settings_manager.save_ncs_pathway(pathway)

    def accept(self):
        """Handles logic for adding new priority layer and an edit existing one."""
        layer_id = uuid.uuid4()
        layer_groups = []
        layer = {}
        layer_type = PriorityLayerType.DEFAULT.value
        if self.layer is not None:
            layer_id = self.layer.get("uuid")
            layer_groups = self.layer.get("groups", [])
            layer_type = self.layer.get("type", PriorityLayerType.DEFAULT.value)

        layer["uuid"] = str(layer_id)
        layer["name"] = self.layer_name.text()
        layer["description"] = self.layer_description.toPlainText()
        layer["groups"] = layer_groups

        default_layer = self._get_selected_default_layer()
        if default_layer:
            layer["path"] = "cplus://" + default_layer.get("layer_uuid")
        else:
            layer["path"] = self.map_layer_file_widget.filePath()

        layer["type"] = layer_type
        layer[USER_DEFINED_ATTRIBUTE] = self._user_defined

        settings_manager.save_priority_layer(layer)

        self.layer = layer
        self.set_selected_items(self.ncs_pathways)

        super().accept()

    def open_help(self):
        """Opens the user documentation for the plugin in a browser"""
        open_documentation(USER_DOCUMENTATION_SITE)

    def _get_selected_default_layer(self) -> dict:
        """Returns selected default layer.

        :return: layer dictionary
        :rtype: dict
        """
        layer_name = self.cbo_default_layer.currentText()
        if layer_name == "":
            return {}
        priority_layers = settings_manager.get_default_layers("priority_layer")
        layer = [p for p in priority_layers if p["name"] == layer_name]
        return layer[0] if layer else {}

    def _on_default_layer_selection_changed(self):
        """Event raised when default layer selection is changed."""
        layer = self._get_selected_default_layer()
        metadata = layer.get("metadata", {})
        self.layer_name.setText(metadata.get("name", layer.get("name", "")))
        self.layer_description.setPlainText(metadata.get("description", ""))
