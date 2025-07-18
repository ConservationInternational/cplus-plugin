# -*- coding: utf-8 -*-
"""
    Scenario dialog
"""

import os
from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from qgis.PyQt.uic import loadUiType

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsRectangle,
)

from qgis.utils import iface

from ..definitions.defaults import ICON_PATH, DEFAULT_CRS_ID
from ..models.base import AreaOfInterestSource


DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/scenario_dialog.ui")
)


class ScenarioDialog(QtWidgets.QDialog, DialogUi):
    """Dialog that provide UI for scenario details."""

    def __init__(
        self,
        scenario=None,
        scenario_result=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        self.scenario = scenario
        self.scenario_result = scenario_result

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        self.initialize_ui()

    def initialize_ui(self):
        """Populate UI inputs when loading the dialog"""

        if self.scenario is not None:
            self.scenario_name.setText(self.scenario.name)
            self.scenario_description.setText(self.scenario.description)

            # Area of Interest
            self.rb_studyarea.setEnabled(False)
            self.rb_extent.setEnabled(False)
            self.cbo_studyarea.setEnabled(False)
            if self.scenario.studyarea_path and os.path.exists(
                self.scenario.studyarea_path
            ):
                self._add_layer_path(self.scenario.studyarea_path)

            if self.scenario.clip_to_studyarea:
                self.on_aoi_source_changed(0, True)
                self.rb_studyarea.setChecked(True)
            else:
                self.rb_extent.setChecked(True)
                self.on_aoi_source_changed(1, True)

            # CRS Selector
            crs = QgsCoordinateReferenceSystem.fromEpsgId(DEFAULT_CRS_ID)
            if self.scenario.extent.crs:
                crs = QgsCoordinateReferenceSystem(self.scenario.extent.crs)

            if crs.isValid():
                self.crs_selector.setCrs(crs)

            self.crs_selector.setEnabled(False)

            self.extent_box.setOutputCrs(crs)
            map_canvas = iface.mapCanvas()
            self.extent_box.setCurrentExtent(
                map_canvas.mapSettings().destinationCrs().bounds(),
                map_canvas.mapSettings().destinationCrs(),
            )
            self.extent_box.setOutputExtentFromCurrent()
            self.extent_box.setMapCanvas(map_canvas)

            extent_list = self.scenario.extent.bbox
            if extent_list:
                default_extent = QgsRectangle(
                    float(extent_list[0]),
                    float(extent_list[2]),
                    float(extent_list[1]),
                    float(extent_list[3]),
                )

                self.extent_box.setOutputExtentFromUser(
                    default_extent,
                    crs,
                )

    def _add_layer_path(self, layer_path: str):
        """Select or add layer path to the map layer combobox."""
        matching_index = -1
        num_layers = self.cbo_studyarea.count()
        for index in range(num_layers):
            layer = self.cbo_studyarea.layer(index)
            if layer is None:
                continue
            if os.path.normpath(layer.source()) == os.path.normpath(layer_path):
                matching_index = index
                break

        if matching_index == -1:
            self.cbo_studyarea.setAdditionalItems([layer_path])
            self.cbo_studyarea.setCurrentIndex(num_layers)
        else:
            self.cbo_studyarea.setCurrentIndex(matching_index)

    def on_aoi_source_changed(self, button_id: int, toggled: bool):
        """Slot raised when the area of interest source button group has
        been toggled.
        """
        if not toggled:
            return

        if button_id == AreaOfInterestSource.LAYER.value:
            self.studyarea_stacked_widget.setCurrentIndex(0)
        elif button_id == AreaOfInterestSource.EXTENT.value:
            self.studyarea_stacked_widget.setCurrentIndex(1)
