# -*- coding: utf-8 -*-
"""Custom CPLUS layout items."""

import typing

from qgis.core import (
    QgsFillSymbol,
    QgsLayoutItemAbstractMetadata,
    QgsLayoutItemRegistry,
    QgsLayoutItemShape
)
from qgis.PyQt import QtGui

from ...models.base import ModelComponentType
from ...utils import FileUtils, tr


CPLUS_MAP_REPEAT_ITEM_TYPE = QgsLayoutItemRegistry.PluginItem + 2350


class CplusMapRepeatItem(QgsLayoutItemShape):
    """Defines an outline area within a layout where map items
    containing NCS pathway or implementation model will be
    drawn.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setShapeType(QgsLayoutItemShape.Shape.Rectangle)

        # We shall use a frame so that it can be turned off / on
        # using the item properties UI. The symbol is just a proxy.
        # Symbol properties
        symbol_props = {
            "color": "229,182,54,0",
            "style": "solid",
            "outline_style": "dash",
            "line_color": "132,192,68",
            "outline_width": "0",
            "joinstyle": "miter"
        }
        symbol = QgsFillSymbol.createSimple(symbol_props)
        self.setSymbol(symbol)

        self._model_component_type = kwargs.pop(
            "model_component_type", ModelComponentType.UNKNOWN
        )

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
    def model_component_type(self, component_type: ModelComponentType):
        """Set the model component type associated with
        this map item i.e. NCS pathway or implementation
        model.

        :param component_type: Type of the model component.
        :type component_type: Enum
        """
        self._model_component_type = component_type

    def type(self):
        """Return item's unique type identifier."""
        return CPLUS_MAP_REPEAT_ITEM_TYPE

    def visibleName(self) -> str:
        """Override for visible name of the item."""
        return tr("CPLUS Map Repeat Area Item")

    def visiblePluralName(self) -> str:
        """Override for plural name of the items."""
        return tr("CPLUS Map Repeat Area Items")

    def icon(self) -> QtGui.QIcon:
        """Override for custom CPLUS map item."""
        return FileUtils.get_icon("mLayoutItemMap_cplus.svg")

    def writePropertiesToElement(self, el, document, context):
        """Override saving of item properties."""
        status = super().writePropertiesToElement(el, document, context)
        if status:
            el.setAttribute("modelComponentType", self._model_component_type.value)

        return status

    def readPropertiesFromElement(self, element, document, context):
        """Override reading of item properties."""
        status = super().readPropertiesFromElement(element, document, context)
        if status:
            model_component_type = element.attribute("modelComponentType", "")
            self._model_component_type = ModelComponentType.from_string(
                model_component_type
            )

        return status


class CplusMapRepeatItemLayoutItemMetadata(
    QgsLayoutItemAbstractMetadata
):
    """Metadata info of the cplus map repeat item."""

    def __init__(self):
        super().__init__(
            CPLUS_MAP_REPEAT_ITEM_TYPE,
            tr("CPLUS Map Repeat Area Item")
        )

    def createItem(self, layout) -> CplusMapRepeatItem:
        """Factory method that return the cplus map item."""
        return CplusMapRepeatItem(layout)
