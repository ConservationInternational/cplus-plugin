# -*- coding: utf-8 -*-
"""Custom CPLUS layout items."""

import typing

from qgis.core import (
    Qgis,
    QgsFillSymbol,
    QgsLayoutItemAbstractMetadata,
    QgsLayoutItemGroup,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemRegistry,
    QgsLayoutItemShape,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsProject,
    QgsRasterLayer,
    QgsTextFormat,
    QgsUnitTypes,
)
from qgis.PyQt import QtCore, QtGui

from ...models.base import ModelComponentType, ScenarioResult
from ...utils import FileUtils, get_report_font, tr


CPLUS_MAP_REPEAT_ITEM_TYPE = QgsLayoutItemRegistry.PluginItem + 2350


class CplusMapRepeatItem(QgsLayoutItemShape):
    """Defines an outline area within a layout where map items
    containing NCS pathway or activity will be drawn.
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
            "joinstyle": "miter",
        }
        symbol = QgsFillSymbol.createSimple(symbol_props)
        self.setSymbol(symbol)

        self._model_component_type = kwargs.pop(
            "model_component_type", ModelComponentType.UNKNOWN
        )

    @property
    def model_component_type(self) -> ModelComponentType:
        """Gets the model component type associated with
        this map item i.e. NCS pathway or activity.

        :returns: Type of the model component.
        :rtype: Enum
        """
        return self._model_component_type

    @model_component_type.setter
    def model_component_type(self, component_type: ModelComponentType):
        """Set the model component type associated with
        this map item i.e. NCS pathway or activity.

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


class CplusMapRepeatItemLayoutItemMetadata(QgsLayoutItemAbstractMetadata):
    """Metadata info of the cplus map repeat item."""

    def __init__(self):
        super().__init__(CPLUS_MAP_REPEAT_ITEM_TYPE, tr("CPLUS Map Repeat Area Item"))

    def createItem(self, layout) -> CplusMapRepeatItem:
        """Factory method that return the cplus map item."""
        return CplusMapRepeatItem(layout)


class BasicScenarioDetailsItem(QgsLayoutItemGroup):
    """Contains elements showing the basic details of a scenario such as a
    title, map and legend.
    """

    def __init__(self, *args, **kwargs):
        self._result: ScenarioResult = kwargs.pop("scenario_result", None)
        self._project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)

        self._add_scenario_layout_items()

        self._update_scenario_details()

    def _add_scenario_layout_items(self):
        """Add layout items for showing the scenario details."""
        reference_point = self.pagePositionWithUnits()
        reference_point_x = reference_point.x()
        reference_point_y = reference_point.y()

        title_color = QtGui.QColor(QtCore.Qt.white)
        label_margin = 1.2

        # Scenario name
        self._title_label = QgsLayoutItemLabel(self.layout())
        self.layout().addLayoutItem(self._title_label)
        self._title_label.attemptMove(reference_point, True, False, self.page())
        self._title_label.attemptResize(QgsLayoutSize(200, 2, self.layout().units()))
        self._title_label.setBackgroundColor(QtGui.QColor(3, 109, 0))
        self._title_label.setBackgroundEnabled(True)
        self._title_label.setHAlign(QtCore.Qt.AlignHCenter)
        self._title_label.setMargin(label_margin)
        self.set_label_font(self._title_label, 15, color=title_color)
        self.addItem(self._title_label)

        # Scenario description
        self._description_label = QgsLayoutItemLabel(self.layout())
        self.layout().addLayoutItem(self._description_label)
        description_ref_point = QgsLayoutPoint(
            reference_point_x, reference_point_y + 2, self.layout().units()
        )
        self._description_label.attemptMove(
            description_ref_point, True, False, self.page()
        )
        self._description_label.attemptResize(
            QgsLayoutSize(200, 10, self.layout().units())
        )
        self._description_label.setMargin(label_margin)
        self.set_label_font(self._description_label, 9)
        self.addItem(self._description_label)

        # Map for scenario HPA layer
        self._scenario_map = QgsLayoutItemMap(self.layout())
        self.layout().addLayoutItem(self._scenario_map)
        map_ref_point = QgsLayoutPoint(
            reference_point_x, reference_point_y + 15, self.layout().units()
        )
        self._scenario_map.attemptMove(map_ref_point, True, False, self.page())
        self._scenario_map.attemptResize(QgsLayoutSize(200, 50, self.layout().units()))
        normalized_scenario_name = self._result.scenario.name.lower().replace(" ", "_")
        self._scenario_map.setId(f"map_{normalized_scenario_name}")
        self.addItem(self._scenario_map)

    def _update_scenario_details(self):
        """Updates the layout items with the scenario information."""
        if self._result is None:
            return

        self._title_label.setText(self._result.scenario.name)
        self._description_label.setText(self._result.scenario.description)

        scenario_layer = self._get_scenario_layer_in_project()
        if scenario_layer is not None:
            self._scenario_map.setLayers([scenario_layer])

    def _get_scenario_layer_in_project(self) -> typing.Optional[QgsRasterLayer]:
        """Gets the scenario layer from the project.

        :returns: Raster layer corresponding to the scenario HPA.
        :rtype: QgsRasterLayer
        """
        if self._project is None:
            return None

        layer_root = self._project.layerTreeRoot()
        matching_tree_layers = [
            tl
            for tl in layer_root.findLayers()
            if tl.layer().name() == self._result.output_layer_name
        ]

        if len(matching_tree_layers) == 0:
            return None

        scenario_tree_layer = matching_tree_layers[0]
        return scenario_tree_layer.layer()

    @classmethod
    def set_label_font(
        cls,
        label: QgsLayoutItemLabel,
        size: float,
        bold: bool = False,
        italic: bool = False,
        color: QtGui.QColor = None,
    ):
        """Set font properties of the given layout label item.

        :param label: Label item whose font properties will
        be updated.
        :type label: QgsLayoutItemLabel

        :param size: Point size of the font.
        :type size: int

        :param bold: True if font is to be bold, else
        False (default).
        :type bold: bool

        :param italic: True if font is to be in italics, else
        False (default).
        :type italic: bool

        :param color: Color for the text or None for the default color.
        :type color: QtGui.QColor
        """
        font = get_report_font(size, bold, italic)
        version = Qgis.versionInt()

        # Text format size unit
        if version < 33000:
            unit_type = QgsUnitTypes.RenderUnit.RenderPoints
        else:
            unit_type = Qgis.RenderUnit.Points

        # Label font setting option
        if version < 32400:
            label.setFont(font)
            if color is not None:
                label.setFontColor(color)
        else:
            txt_format = QgsTextFormat()
            txt_format.setFont(font)
            txt_format.setSize(size)
            txt_format.setSizeUnit(unit_type)

            if color is not None:
                txt_format.setColor(color)

            label.setTextFormat(txt_format)

        label.refresh()
