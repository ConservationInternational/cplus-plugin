# -*- coding: utf-8 -*-
"""Custom layout items."""

import typing

from qgis.core import (
    QgsLayoutItemAbstractMetadata,
    QgsLayoutItemMap,
    QgsLayoutItemRegistry,
)
from qgis.PyQt import QtGui

from ...models.base import ModelComponentType
from ...utils import FileUtils, tr


CPLUS_MAP_ITEM_TYPE = QgsLayoutItemRegistry.PluginItem + 2350


class CplusMapItem(QgsLayoutItemMap):
    """Renders NCS pathway or implementation
    model.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_component_id = kwargs.pop("model_component_id", "")
        self._model_component_type = kwargs.pop(
            "model_component_type",
            ModelComponentType.UNKNOWN
        )

    @property
    def model_component_id(self) -> str:
        """Gets the unique identifier for the NCS
        pathway or implementation model component that
        is linked to this map item.

        :returns: The unique identifier of the
        model component.
        :rtype: str
        """
        return self._model_component_id

    @model_component_id.setter
    def model_component_id(self, component_id: str):
        """Set the unique identifier of the NCS pathway
        or implementation model component associated
        with this map item.

        :param component_id: Unique identifier of the
        model component.
        :type component_id: str
        """
        self._model_component_id = component_id

    @property
    def model_component_type(self) -> ModelComponentType:
        """Gets the model component type associated with
        this map item i.e. NCS pathway or implementation
        model.

        :returns: Type of the model component.
        :rtype: Enum
        """
        return self._model_component_type

    @model_component_type.setter
    def model_component_type(
            self,
            component_type: ModelComponentType
    ):
        """Set the model component type associated with
        this map item i.e. NCS pathway or implementation
        model.

        :param component_type: Type of the model component.
        :type component_type: Enum
        """
        self._model_component_type = component_type

    def type(self):
        """Return item's unique type identifier."""
        return CPLUS_MAP_ITEM_TYPE

    def visibleName(self) -> str:
        """Override for visible name of the item."""
        return tr("CPLUS Map Item")

    def visiblePluralName(self) -> str:
        """Override for plural name of the items."""
        return tr("CPLUS Map Items")

    def icon(self) -> QtGui.QIcon:
        """Override for custom CPLUS map item."""
        return FileUtils.get_icon("mLayoutItemMap_temp.png")

    def writePropertiesToElement(self, el, document, context):
        """Override saving of item properties."""
        status = super().writePropertiesToElement(el, document, context)
        if status:
            el.setAttribute(
                "modelComponentId",
                self._model_component_id
            )
            el.setAttribute(
                "modelComponentType",
                self._model_component_type.value
            )

        return status

    def readPropertiesFromElement(self, element, document, context):
        """Override reading of item properties."""
        status = super().readPropertiesFromElement(element, document, context)
        if status:
            self._model_component_id = element.attribute(
                "modelComponentId",
                ""
            )
            model_component_type = element.attribute("modelComponentType", "")
            self._model_component_type = ModelComponentType.from_string(
                model_component_type
            )

        return status


class CplusMapItemLayoutItemMetadata(QgsLayoutItemAbstractMetadata):
    """Metadata info of the cplus map item."""

    def __init__(self):
        super().__init__(CPLUS_MAP_ITEM_TYPE, tr("CPLUS Map Item"))

    def createItem(self, layout) -> CplusMapItem:
        """Factory method that return the Cplus map item."""
        return CplusMapItem(layout)
