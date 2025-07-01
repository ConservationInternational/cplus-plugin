# -*- coding: utf-8 -*-
"""
Dialog for creating or editing an NCS pathway entry.
"""

import os
import typing
import uuid

from qgis.core import Qgis, QgsMapLayerProxyModel, QgsRasterLayer
from qgis.gui import QgsGui, QgsMessageBar

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.uic import loadUiType

from ..conf import Settings, settings_manager
from ..definitions.defaults import (
    ONLINE_DEFAULT_PREFIX,
    ICON_PATH,
    USER_DOCUMENTATION_SITE,
)
from ..models.base import (
    DataSourceType,
    LayerType,
    NcsPathway,
    NcsPathwayType,
    LayerSource,
)
from ..utils import FileUtils, open_documentation, tr, log

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/ncs_pathway_editor_dialog.ui")
)


class NcsPathwayEditorDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for creating or editing an NCS pathway entry."""

    def __init__(self, parent=None, ncs_pathway=None, excluded_names=None):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        self._message_bar = QgsMessageBar()
        self.vl_notification.addWidget(self._message_bar)

        self.txt_description.textChanged.connect(self.description_changed)

        self.buttonBox.accepted.connect(self._on_accepted)
        self.btn_add_layer.clicked.connect(self._on_select_file)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        help_icon = FileUtils.get_icon("mActionHelpContents_green.svg")
        self.btn_help.setIcon(help_icon)
        self.btn_help.clicked.connect(self.open_help)

        self.cbo_default_layer_source.addItems(
            [LayerSource.CPLUS.value, LayerSource.NATUREBASE.value]
        )
        self.cbo_default_layer_source.currentIndexChanged.connect(
            self._on_default_layer_source_selection_changed
        )
        self.naturebase_list = []
        self.cplus_list = []

        pathways = settings_manager.get_default_layers("ncs_pathway")
        self.cbo_default_layer.addItem("")
        # Populate the default layer combobox with available pathways
        for pathway in pathways:
            source = pathway.get("source", "").lower()
            if source == LayerSource.CPLUS.value.lower():
                self.cplus_list.append(pathway)
            elif source == LayerSource.NATUREBASE.value.lower():
                self.naturebase_list.append(pathway)

        items = sorted([p["name"] for p in self.cplus_list])
        self.cbo_default_layer.addItems(items)
        self.cbo_default_layer.setCurrentIndex(0)
        self.cbo_default_layer.currentIndexChanged.connect(
            self._on_default_layer_selection_changed
        )

        # Pathway type
        self._pathway_type_group = QtWidgets.QButtonGroup(self)
        self._pathway_type_group.addButton(
            self.rb_protection, NcsPathwayType.PROTECT.value
        )
        self._pathway_type_group.addButton(
            self.rb_restoration, NcsPathwayType.RESTORE.value
        )
        self._pathway_type_group.addButton(
            self.rb_management, NcsPathwayType.MANAGE.value
        )

        # Data source type
        self._data_source_type_group = QtWidgets.QButtonGroup(self)
        self._data_source_type_group.setExclusive(True)
        self._data_source_type_group.addButton(
            self.rb_local, DataSourceType.LOCAL.value
        )
        self._data_source_type_group.addButton(
            self.rb_online, DataSourceType.ONLINE.value
        )
        self._data_source_type_group.idToggled.connect(self._on_data_source_changed)
        self.rb_local.setChecked(True)

        # Configure map combobox
        self.cbo_layer.setAllowEmptyLayer(True, tr("<Layer not set>"))
        self.cbo_layer.setFilters(QgsMapLayerProxyModel.Filter.RasterLayer)

        self._excluded_names = excluded_names
        if excluded_names is None:
            self._excluded_names = []

        self._edit_mode = False
        self._layer = None
        self._ncs_pathway = ncs_pathway
        if self._ncs_pathway is not None:
            self._edit_mode = True
            self._layer = self._ncs_pathway.to_map_layer()
            self._update_controls()

    @property
    def ncs_pathway(self) -> NcsPathway:
        """Returns a reference to the NcsPathway object.

        :returns: Reference to the NcsPathway object.
        :rtype: NcsPathway
        """
        return self._ncs_pathway

    @property
    def edit_mode(self) -> bool:
        """Returns the state of the editor.

        :returns: True if the editor is editing an existing NcsPathway
        object, else False if its creating a new object.
        :rtype: bool
        """
        return self._edit_mode

    @property
    def layer(self) -> QgsRasterLayer:
        """Returns the raster layer specified by the user,
        either existing layers in the map canvas or from the
        selected file.

        :returns: The raster layer specified by the user or
        None if not set.
        :rtype: QgsRasterLayer
        """
        return self._layer

    def description_changed(self):
        """Slot to handle description text changes, it currently
        limits the number of characters to only be 300 characters
        per description
        """

        description = self.txt_description.toPlainText()
        if len(description) > 300:
            self.txt_description.setPlainText(description[:300])

    def _update_controls(self):
        """Update controls with data from the NcsPathway object."""
        if self._ncs_pathway is None:
            return

        self.txt_name.setText(self._ncs_pathway.name)
        self.txt_description.setPlainText(self._ncs_pathway.description)

        if self._ncs_pathway.pathway_type == NcsPathwayType.PROTECT:
            self.rb_protection.setChecked(True)
        if self._ncs_pathway.pathway_type == NcsPathwayType.RESTORE:
            self.rb_restoration.setChecked(True)
        if self._ncs_pathway.pathway_type == NcsPathwayType.MANAGE:
            self.rb_management.setChecked(True)

        if self._ncs_pathway.path.startswith(ONLINE_DEFAULT_PREFIX):
            self.rb_online.setChecked(True)
        else:
            self.rb_local.setChecked(True)

        if self._layer:
            layer_path = self._layer.source()
            self._add_layer_path(layer_path)
        if self._ncs_pathway.layer_uuid:
            pathways = settings_manager.get_default_layers("ncs_pathway")
            for i, layer in enumerate(pathways):
                if layer["source"].lower() == LayerSource.NATUREBASE.value.lower():
                    self.cbo_default_layer_source.setCurrentIndex(1)
                else:
                    self.cbo_default_layer_source.setCurrentIndex(0)

                if layer["layer_uuid"] == self._ncs_pathway.layer_uuid:
                    self.cbo_default_layer.setCurrentIndex(i + 1)
                    break

    def _on_data_source_changed(self, button_id: int, toggled: bool):
        """Slot raised when the data source type button group has
        been toggled.
        """
        if not toggled:
            return

        if button_id == DataSourceType.LOCAL.value:
            self.data_source_stacked_widget.setCurrentIndex(0)
        elif button_id == DataSourceType.ONLINE.value:
            self.data_source_stacked_widget.setCurrentIndex(1)

    def _add_layer_path(self, layer_path: str):
        """Select or add layer path to the map layer combobox."""
        matching_index = -1
        num_layers = self.cbo_layer.count()
        for index in range(num_layers):
            layer = self.cbo_layer.layer(index)
            if layer is None:
                continue
            if os.path.normpath(layer.source()) == os.path.normpath(layer_path):
                matching_index = index
                break

        if matching_index == -1:
            self.cbo_layer.setAdditionalItems([layer_path])
            # Set added path as current item
            self.cbo_layer.setCurrentIndex(num_layers)
        else:
            self.cbo_layer.setCurrentIndex(matching_index)

    def _show_warning_message(self, message):
        """Shows a warning message in the message bar."""
        self._message_bar.pushMessage(message, Qgis.MessageLevel.Warning)

    def validate(self) -> bool:
        """Validates if name and layer have been specified.

        :returns: True if user input (i.e. name and layer) have been set.
        :rtype: True
        """
        status = True

        self._message_bar.clearWidgets()

        name = self.txt_name.text()
        if not name:
            msg = tr("NCS pathway name cannot be empty.")
            self._show_warning_message(msg)
            status = False

        if name.lower() in self._excluded_names:
            msg = tr("name has already been used.")
            self._show_warning_message(f"'{name}' {msg}")
            status = False

        if not self.txt_description.toPlainText():
            msg = tr("Description cannot be empty.")
            self._show_warning_message(msg)
            status = False

        if self._pathway_type_group.checkedId() == -1:
            msg = tr("The NCS pathway type is not specified.")
            self._show_warning_message(msg)
            status = False

        layer = self._get_selected_map_layer()
        default_layer = self._get_selected_default_layer()
        data_source_type_id = self._data_source_type_group.checkedId()

        if data_source_type_id == DataSourceType.LOCAL.value and layer is None:
            msg = tr("Local map layer not specified.")
            self._show_warning_message(msg)
            status = False
        elif (
            data_source_type_id == DataSourceType.ONLINE.value
            and len(default_layer) == 0
        ):
            msg = tr("Online default layer not specified.")
            self._show_warning_message(msg)
            status = False

        if (
            data_source_type_id == DataSourceType.LOCAL.value
            and layer
            and not layer.isValid()
        ):
            msg = tr("Local map layer is not valid.")
            self._show_warning_message(msg)
            status = False

        return status

    def _create_update_ncs_pathway(self):
        """Create or update NcsPathway from user input."""
        layer = self._get_selected_map_layer()
        if layer:
            self._layer = layer

        if self._ncs_pathway is None:
            self._ncs_pathway = NcsPathway(
                uuid.uuid4(),
                self.txt_name.text(),
                self.txt_description.toPlainText(),
                user_defined=True,
            )
        else:
            # Update mode
            self._ncs_pathway.name = self.txt_name.text()
            self._ncs_pathway.description = self.txt_description.toPlainText()

        selected_pathway_type_id = self._pathway_type_group.checkedId()
        if selected_pathway_type_id == NcsPathwayType.PROTECT.value:
            self._ncs_pathway.pathway_type = NcsPathwayType.PROTECT
        elif selected_pathway_type_id == NcsPathwayType.RESTORE.value:
            self._ncs_pathway.pathway_type = NcsPathwayType.RESTORE
        elif selected_pathway_type_id == NcsPathwayType.MANAGE.value:
            self._ncs_pathway.pathway_type = NcsPathwayType.MANAGE

        self._ncs_pathway.layer_type = LayerType.RASTER

        data_source_type_id = self._data_source_type_group.checkedId()
        if data_source_type_id == DataSourceType.LOCAL.value:
            self._ncs_pathway.path = self._layer.source()
        elif data_source_type_id == DataSourceType.ONLINE.value:
            default_layer = self._get_selected_default_layer()
            self._ncs_pathway.path = ONLINE_DEFAULT_PREFIX + default_layer.get(
                "layer_uuid"
            )

    def _get_selected_map_layer(self) -> QgsRasterLayer:
        """Returns the currently selected map layer or None if there is
        no item in the combobox.
        """
        layer = self.cbo_layer.currentLayer()

        if layer is None:
            layer_paths = self.cbo_layer.additionalItems()
            current_path = self.cbo_layer.currentText()
            if current_path in layer_paths:
                layer_name = os.path.basename(current_path)
                layer = QgsRasterLayer(current_path, layer_name)

        return layer

    def _get_selected_default_layer(self) -> dict:
        """Returns selected default layer.

        :return: layer dictionary
        :rtype: dict
        """
        layer_name = self.cbo_default_layer.currentText()
        if layer_name == "":
            return {}
        pathways = settings_manager.get_default_layers("ncs_pathway")
        layer = [p for p in pathways if p["name"] == layer_name]
        return layer[0] if layer else {}

    def open_help(self, activated: bool):
        """Opens the user documentation for the plugin in a browser."""
        open_documentation(USER_DOCUMENTATION_SITE)

    def _on_accepted(self):
        """Validates user input before closing."""
        if not self.validate():
            return

        self._create_update_ncs_pathway()
        self.accept()

    def _on_select_file(self, activated: bool):
        """Slot raised to upload a raster layer."""
        data_dir = settings_manager.get_value(Settings.LAST_DATA_DIR, "")
        if not data_dir and self._layer:
            data_path = self._layer.source()
            if os.path.exists(data_path):
                data_dir = os.path.dirname(data_path)

        if not data_dir:
            data_dir = "/home"

        filter_tr = tr("All files")

        layer_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("Select NCS Pathway Layer"),
            data_dir,
            f"{filter_tr} (*.*)",
            options=QtWidgets.QFileDialog.DontResolveSymlinks,
        )
        if not layer_path:
            return

        existing_paths = self.cbo_layer.additionalItems()
        if layer_path in existing_paths:
            return

        self.cbo_layer.setAdditionalItems([])

        self._add_layer_path(layer_path)
        settings_manager.set_value(Settings.LAST_DATA_DIR, os.path.dirname(layer_path))

    def _on_default_layer_selection_changed(self):
        """Event raised when default layer selection is changed."""
        layer = self._get_selected_default_layer()
        metadata = layer.get("metadata", {})
        self.txt_name.setText(metadata.get("name", layer.get("name", "")))
        self.txt_description.setPlainText(metadata.get("description", ""))
        # remove selection from cbo_layer
        self.cbo_layer.setAdditionalItems([])

    def _on_default_layer_source_selection_changed(self):
        """Event raised when online layer source selection is changed."""
        source = self.cbo_default_layer_source.currentText()
        if source.lower() == LayerSource.CPLUS.value.lower():
            items = sorted([p["name"] for p in self.cplus_list])
        elif source == LayerSource.NATUREBASE.value:
            items = sorted([p["name"] for p in self.naturebase_list])
        self.cbo_default_layer.clear()
        self.cbo_default_layer.addItem("")
        self.cbo_default_layer.addItems(items)
