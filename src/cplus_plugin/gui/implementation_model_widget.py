# -*- coding: utf-8 -*-
"""
Container widget for configuring the implementation widget.
"""

import os
import typing

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from .model_component_widget import (
    ImplementationModelComponentWidget,
    NcsComponentWidget,
)

from ..models.base import ImplementationModel, NcsPathway

from ..utils import FileUtils


WidgetUi, _ = loadUiType(
    os.path.join(
        os.path.dirname(__file__), "../ui/implementation_model_container_widget.ui"
    )
)


class ImplementationModelContainerWidget(QtWidgets.QWidget, WidgetUi):
    """Widget for configuring the implementation model."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._items_loaded = False

        self.btn_add_one.setIcon(FileUtils.get_icon("play.svg"))
        self.btn_add_one.setToolTip(self.tr("Add selected NCS pathway"))
        self.btn_add_one.clicked.connect(self._on_add_ncs_pathway)

        self.btn_add_all.setIcon(FileUtils.get_icon("forward.svg"))
        self.btn_add_all.setToolTip(self.tr("Add all NCS pathways"))
        self.btn_add_all.clicked.connect(self._on_add_all_ncs_pathways)

        # NCS pathway view
        self.ncs_pathway_view = NcsComponentWidget()
        self.ncs_pathway_view.title = self.tr("NCS Pathways")
        self.ncs_layout.addWidget(self.ncs_pathway_view)

        # Implementation model view
        self.implementation_model_view = ImplementationModelComponentWidget()
        self.ipm_layout.addWidget(self.implementation_model_view)
        self.implementation_model_view.title = self.tr("Implementation Models")

    def load(self):
        """Load NCS pathways and implementation models to the views.

        This function is idempotent as items will only be loaded once
        on initial call.

        """
        if not self._items_loaded:
            self._load_persisted_ncs_pathways()
            self._items_loaded = True

    def _load_persisted_ncs_pathways(self):
        """Load default and user-defined NCS pathways."""
        pass

    def ncs_pathways(self) -> typing.List[NcsPathway]:
        """Gets the NCS pathway objects in the NCS Pathways view.

        :returns: NCS pathway objects, both default and user-defined.
        :rtype: list
        """
        return self.ncs_pathway_view.pathways()

    def implementation_models(self) -> typing.List[ImplementationModel]:
        """Returns the user-defined implementation models in the
        Implementation Models view.

        :returns: User-defined implementation models for the current scenario.
        :rtype: list
        """
        return self.implementation_model_view.models()

    def _on_add_ncs_pathway(self):
        """Slot raised to add NCS pathway item to an implementation model."""
        selected_ncs_items = self.ncs_pathway_view.selected_items()
        if len(selected_ncs_items) == 0:
            return

        ncs_item = selected_ncs_items[0]
        self.implementation_model_view.add_ncs_pathway_items([ncs_item])

    def _on_add_all_ncs_pathways(self):
        """Slot raised to add all NCS pathway item to an
        implementation model view.
        """
        all_ncs_items = self.ncs_pathway_view.ncs_items()
        if len(all_ncs_items) == 0:
            return

        self.implementation_model_view.add_ncs_pathway_items(all_ncs_items)
