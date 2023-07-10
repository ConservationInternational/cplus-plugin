# -*- coding: utf-8 -*-
"""
Widget for the custom CPLUS layout map item.
"""

import os
import typing

from qgis.core import QgsLayoutItem, QgsProject
from qgis.gui import (
    QgsLayoutItemAbstractGuiMetadata,
    QgsLayoutItemBaseWidget,
    QgsLayoutItemPropertiesWidget,
)
from qgis.utils import iface

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.uic import loadUiType

from ..conf import settings_manager
from ..lib.reports.layout_items import CplusMapItem, CPLUS_MAP_ITEM_TYPE
from ..models.base import ModelComponentType
from ..utils import FileUtils, tr


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/map_layout_item_widget.ui")
)


CPLUS_ITEM_NAME = tr("CPLUS Map")


class CplusMapItemWidget(QgsLayoutItemBaseWidget, WidgetUi):
    """Widget for configuring the CPLUS layout map item."""

    def __init__(self, parent, layout_object: CplusMapItem):
        super().__init__(parent, layout_object)
        self.setupUi(self)

        self._map_item = layout_object

        # Common item properties widget
        self._prop_widget = QgsLayoutItemPropertiesWidget(self, layout_object)
        self.layout.insertWidget(2, self._prop_widget)

        self.rb_ncs_pathways.toggled.connect(self.on_select_ncs_pathway)
        self.rb_implementation_model.toggled.connect(
            self.on_select_implementation_model
        )
        self.rb_ncs_pathways.setChecked(True)

        self.cbo_model_items.currentIndexChanged.connect(self.on_layer_source_changed)

        self._update_ui()

    def _update_ui(self):
        """Update UI based on map item properties."""
        component_type = self._map_item.model_component_type
        if component_type == ModelComponentType.NCS_PATHWAY:
            self.rb_ncs_pathways.setChecked(True)

        elif component_type == ModelComponentType.IMPLEMENTATION_MODEL:
            self.rb_implementation_model.setChecked(True)

        component_id = self._map_item.model_component_id
        if not component_id:
            return

        idx = self.cbo_model_items.findData(component_id)
        if idx == -1:
            return

        self.cbo_model_items.setCurrentIndex(idx)

    def on_select_ncs_pathway(self, state):
        """Slot raised when NCS pathway radio button has been toggled.

        :param state: True is the button is checked, else False.
        :type state: bool
        """
        self.cbo_model_items.clear()
        if state:
            ncs_pathways = settings_manager.get_all_ncs_pathways()
            self._add_model_component_items(ncs_pathways)

    def on_select_implementation_model(self, state):
        """Slot raised when implementation model radio button has been toggled.

        :param state: True is the button is checked, else False.
        :type state: bool
        """
        self.cbo_model_items.clear()
        if state:
            imp_models = settings_manager.get_all_implementation_models()
            self._add_model_component_items(imp_models)

    def _add_model_component_items(self, model_items: typing.List):
        """Add model component items to the combobox."""
        self.cbo_model_items.blockSignals(True)

        self.cbo_model_items.clear()

        self.cbo_model_items.addItem("")
        for mi in model_items:
            self.cbo_model_items.addItem(mi.name, str(mi.uuid))

        self.cbo_model_items.blockSignals(False)

    def on_layer_source_changed(self, index: int):
        """Slot raised when the user has changed the layer source
        for the map item.

        :param index: Current index of the select item.
        :type index: int
        """
        if index == -1:
            return

        item_uuid = self.cbo_model_items.itemData(index)
        self._map_item.model_component_id = item_uuid


class CplusMapLayoutItemGuiMetadata(QgsLayoutItemAbstractGuiMetadata):
    """GUI metadata for a CPLUS map layout item."""

    def __init__(self):
        super().__init__(CPLUS_MAP_ITEM_TYPE, CPLUS_ITEM_NAME)

    def createItemWidget(self, item) -> QtWidgets.QWidget:
        """Factory override for the item widget."""
        return CplusMapItemWidget(None, item)

    def createItem(self, layout) -> QgsLayoutItem:
        """Factory override that returns the map item."""
        return CplusMapItem(layout)

    def visibleName(self) -> str:
        """Override for user-visible name identifying the item."""
        return CPLUS_ITEM_NAME

    def creationIcon(self) -> QtGui.QIcon:
        """Factory override for item icon."""
        return FileUtils.get_icon("mLayoutItemMap_temp.png")

    def newItemAddedToLayout(self, map_item: CplusMapItem):
        """Define action that is called when the CplusMapItem
        is added to a layout through the GUI.

        :param map_item: Mao item to be added to the layout.
        :type map_item: QgsLayoutItem
        """
        map_item.setBackgroundColor(QgsProject.instance().backgroundColor())
        map_canvas = iface.mapCanvas()
        if map_canvas is not None:
            map_item.setMapRotation(map_canvas.rotation())
            map_item.zoomToExtent(map_canvas.mapSettings().visibleExtent())

        items = map_item.layout().items()
        counter = 1
        for item in items:
            if isinstance(item, CplusMapItem):
                counter += 1

        map_item.setId(f"{CPLUS_ITEM_NAME} {counter!s}")

        # Use project CRS as default
        map_item.setCrs(QgsProject.instance().crs())
