# -*- coding: utf-8 -*-
"""
Container widget for configuring the implementation widget.
"""

import os
import typing

from qgis.core import Qgis
from qgis.gui import QgsMessageBar

from qgis.PyQt import QtCore, QtWidgets

from qgis.PyQt.uic import loadUiType

from ..conf import Settings, settings_manager
from .component_item_model import ImplementationModelItem, ModelComponentItemType
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

    ncs_reloaded = QtCore.pyqtSignal()

    def __init__(
        self, parent: QtWidgets.QWidget = None, message_bar: QgsMessageBar = None
    ):
        super().__init__(parent)
        self.setupUi(self)

        self._message_bar = message_bar

        self._items_loaded = False

        self.btn_add_one.setIcon(FileUtils.get_icon("cplus_right_arrow.svg"))
        self.btn_add_one.setToolTip(self.tr("Add selected NCS pathway"))
        self.btn_add_one.clicked.connect(self._on_add_ncs_pathway)

        self.btn_add_all.setIcon(FileUtils.get_icon("cplus_double_right_arrows.svg"))
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

        settings_manager.settings_updated[str, object].connect(self.on_settings_changed)
        self.ncs_pathway_view.ncs_pathway_updated.connect(self.on_ncs_pathway_updated)
        self.ncs_pathway_view.items_reloaded.connect(self._on_ncs_pathways_reloaded)

        self.load()

    def load(self):
        """Load NCS pathways and implementation models to the views.

        This function is idempotent as items will only be loaded once
        on initial call.
        """
        if not self._items_loaded:
            self.ncs_pathway_view.load()
            self.implementation_model_view.load()
            self._items_loaded = True

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

    def _on_ncs_pathways_reloaded(self):
        """Slot raised when NCS pathways have been reloaded."""
        self.ncs_reloaded.emit()

    def on_ncs_pathway_updated(self, ncs_pathway: NcsPathway):
        """Slot raised when an NCS pathway has been updated."""
        self.implementation_model_view.update_ncs_pathway_items(ncs_pathway)

    def enable_default_items(self, enable: bool):
        """Enable or disable default NCS pathway and implementation model items.

        :param enable: True to enable or False to disable default items.
        :type enable: bool
        """
        if not self._items_loaded:
            return

        self.ncs_pathway_view.enable_default_items(enable)
        self.implementation_model_view.enable_default_items(enable)

    def show_message(self, message, level=Qgis.Warning):
        """Shows message if message bar has been specified.

        :param message: Text to display in the message bar.
        :type message: str

        :param level: Message level type
        :type level: Qgis.MessageLevel
        """
        if self._message_bar is None:
            return

        self._message_bar.clearWidgets()
        self._message_bar.pushMessage(message, level=level)

    def on_settings_changed(self, name: str, value: typing.Any):
        """Slot raised when settings has been changed.

        :param name: Name of the setting that has changed.
        :type name: str

        :param value: New value for the given settings name.
        :type value: Any
        """
        # Update the NCS pathway and carbon layer paths when
        # BASE_DIR has been updated.
        if name == Settings.BASE_DIR.value:
            self.ncs_pathway_view.load()

    def is_valid(self) -> bool:
        """Check if the user input is valid.

        This checks if there is one implementation model defined with at
        least one NCS pathway under it.

        :returns: True if the implementation model configuration is
        valid, else False at least until there is one implementation
        model defined with at least one NCS pathway under it.
        :rtype: bool
        """
        implementation_models = self.implementation_models()
        if len(implementation_models) == 0:
            return False

        status = False
        for im in implementation_models:
            if len(im.pathways) > 0 or im.to_map_layer() is not None:
                status = True
                break

        return status

    def selected_items(self) -> typing.List[ModelComponentItemType]:
        """Returns the selected model component item types which could be
        NCS pathway or implementation model items.

        If an item is disabled then it will be excluded from the
        selection.

        These are cloned objects so as not to interfere with the
        underlying data models when used for scenario analysis. Otherwise,
        one can also use the data models from the MVC item model.

        :returns: Selected model component items.
        :rtype: list
        """
        ref_items = self.implementation_model_view.selected_items()
        cloned_items = []
        for ref_item in ref_items:
            if not ref_item.isEnabled():
                continue

            clone_item = ref_item.clone()
            cloned_items.append(clone_item)

        return cloned_items

    def selected_im_items(self) -> typing.List[ImplementationModelItem]:
        """Returns the currently selected instances of ImplementationModelItem.

        If an item is disabled then it will be excluded from the  selection.

        :returns: Currently selected instances of ImplementationModelItem or
        an empty list if there is no selection of IM items.
        :rtype: list
        """
        return [
            item
            for item in self.selected_items()
            if isinstance(item, ImplementationModelItem)
        ]
