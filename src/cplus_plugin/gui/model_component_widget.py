# -*- coding: utf-8 -*-
"""
Composite list view-based widgets for displaying implementation model
and NCS pathway items.
"""
import os
import typing

from qgis.PyQt import QtCore, QtWidgets
from qgis.PyQt.uic import loadUiType

from qgis.core import QgsApplication

from .component_item_model import (
    ComponentItemModel,
    ComponentItemModelType,
    IMItemModel,
    ImplementationModelItem,
    IMPLEMENTATION_MODEL_TYPE,
    ModelComponentItemType,
    NcsPathwayItem,
    NcsPathwayItemModel,
    NCS_PATHWAY_TYPE,
)
from .implementation_model_editor_dialog import ImplementationModelEditorDialog
from .ncs_pathway_editor_dialog import NcsPathwayEditorDialog
from ..models.base import ImplementationModel, LayerType, NcsPathway


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/model_component_widget.ui")
)


class ModelComponentWidget(QtWidgets.QWidget, WidgetUi):
    """Widget for displaying and managing model items in a list view."""

    def __init__(self, parent=None, item_model=None):
        super().__init__(parent)
        self.setupUi(self)

        self._item_model = item_model
        if self._item_model is not None:
            self.item_model = self._item_model

        add_icon = QgsApplication.instance().getThemeIcon("symbologyAdd.svg")
        self.btn_add.setIcon(add_icon)
        self.btn_add.clicked.connect(self._on_add_item)

        remove_icon = QgsApplication.instance().getThemeIcon("symbologyRemove.svg")
        self.btn_remove.setIcon(remove_icon)
        self.btn_remove.setEnabled(False)
        self.btn_remove.clicked.connect(self._on_remove_item)

        edit_icon = QgsApplication.instance().getThemeIcon("mActionToggleEditing.svg")
        self.btn_edit.setIcon(edit_icon)
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_item)

    @property
    def item_model(self) -> ComponentItemModelType:
        """Returns the component item model for managing items the list view.

        :returns: Component item model for managing items the list view.
        :rtype: ComponentItemModel
        """
        return self._item_model

    @item_model.setter
    def item_model(self, model: ComponentItemModelType):
        """Sets the component item model for managing items in the list view.

        :param model: The component item model for managing items.
        :type model: ComponentItemModel
        """
        if self._item_model is None:
            self._item_model = model
            self.lst_model_items.setModel(self._item_model)
            self.lst_model_items.selectionModel().selectionChanged.connect(
                self._on_selection_changed
            )

    @property
    def title(self) -> str:
        """Returns the title of the view.

        :returns: Title of the view.
        :rtype: str
        """
        return self.lbl_title.text()

    @title.setter
    def title(self, text: str):
        """Sets the text tobe displayed in the title label of the view.

        :param text: Title of the view.
        :type text: str
        """
        self.lbl_title.setText(text)

    def _on_add_item(self):
        """Slot raised when add item button has been clicked.

        Default implementation does nothing. To be implemented by
        subclasses.
        """
        pass

    def _on_edit_item(self):
        """Slot raised when edit item button has been clicked.

        Default implementation does nothing. To be implemented by
        subclasses.
        """
        pass

    def _on_remove_item(self):
        """Slot raised when remove item button has been clicked.

        Default implementation does nothing. To be implemented by
        subclasses.
        """
        pass

    def set_description(self, description: str):
        """Updates the text for the selected item.

        :param description: Description for the selected item.
        :type description: str
        """
        self.txt_item_description.setText(description)
        self.txt_item_description.setToolTip(description)

    def clear_description(self):
        """Clears the content in the description text box."""
        self.txt_item_description.clear()
        self.txt_item_description.setToolTip("")

    def _on_selection_changed(
        self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection
    ):
        """Slot raised when selection in the list view has changed.

        :param selected: Current item selection.
        :type selected: QtCore.QItemSelection

        :param deselected: Previously selected items that have been
        deselected.
        :type deselected: QtCore.QItemSelection
        """
        self._update_ui_on_selection_changed()

    def _update_ui_on_selection_changed(self):
        """Update UI properties on selection changed."""
        self.btn_remove.setEnabled(True)
        self.btn_edit.setEnabled(True)

        # Remove description and disable edit and remove buttons if
        # more than one item has been selected.
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            self.clear_description()
            self.btn_remove.setEnabled(False)
            self.btn_edit.setEnabled(False)
            return

        self.set_description(selected_items[0].description)

    def selected_items(self) -> typing.List[ModelComponentItemType]:
        """Returns the selected items in the list view.

        :returns: A collection of the selected model component items. Returns
        an empty list if the item model has not been set.
        :rtype: list
        """
        if self._item_model is None:
            return []

        selection_model = self.lst_model_items.selectionModel()
        idxs = selection_model.selectedRows()

        return [self._item_model.item(idx.row()) for idx in idxs]


class NcsComponentWidget(ModelComponentWidget):
    """Widget for displaying and managing NCS pathways."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.item_model = NcsPathwayItemModel(parent)

        self.lst_model_items.setDragEnabled(True)
        self.lst_model_items.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.lst_model_items.setAcceptDrops(False)

        # Disable add, edit, remove controls for now
        self.btn_add.setEnabled(False)
        self.btn_remove.setEnabled(False)
        self.btn_edit.setEnabled(False)

    def add_ncs_pathway(self, ncs_pathway: NcsPathway):
        """Adds an NCS pathway object to the view.

        :param ncs_pathway: NCS pathway object to be added to the view.
        :type ncs_pathway: NcsPathway
        """
        self.item_model.add_ncs_pathway(ncs_pathway)

    def _update_ui_on_selection_changed(self):
        """Temporarily disable edit, remove buttons."""
        super()._update_ui_on_selection_changed()
        self.btn_remove.setEnabled(False)
        self.btn_edit.setEnabled(False)

    def pathways(self, valid_only=False) -> typing.List[NcsPathway]:
        """Returns a collection of NcsPathway objects in the list view.

        :param valid_only: True to only return those NcsPathway objects that
        are valid, default is False.
        :type valid_only: bool

        :returns: Collection of NcsPathway objects in the list view.
        :rtype: list
        """
        return self.item_model.pathways(valid_only)

    def ncs_items(self) -> typing.List[NcsPathwayItem]:
        """Returns a collection of all NcsPathwayItem objects in the
        list view.

        :returns: Collection of NcsPathwayItem objects in the list view.
        :rtype: list
        """
        return self.item_model.model_component_items()

    def _on_add_item(self):
        """Show NCS pathway editor."""
        ncs_editor = NcsPathwayEditorDialog(self)
        if ncs_editor.exec_() == QtWidgets.QDialog.Accepted:
            ncs_pathway = ncs_editor.ncs_pathway
            self.item_model.add_ncs_pathway(ncs_pathway)

    def _on_edit_item(self):
        """Edit selected NCS pathway object."""
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            return

        item = selected_items[0]
        ncs_editor = NcsPathwayEditorDialog(self, item.ncs_pathway)
        if ncs_editor.exec_() == QtWidgets.QDialog.Accepted:
            ncs_pathway = ncs_editor.ncs_pathway
            self.item_model.update_ncs_pathway(ncs_pathway)
            self._update_ui_on_selection_changed()

    def _on_remove_item(self):
        """Delete NcsPathway object."""
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            return

        ncs = selected_items[0].ncs_pathway

        msg = self.tr(
            f"Do you want to remove '{ncs.name}'?\nClick Yes to "
            f"proceed or No to cancel."
        )

        if (
            QtWidgets.QMessageBox.question(
                self,
                self.tr("Remove NCS Pathway"),
                msg,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            == QtWidgets.QMessageBox.Yes
        ):
            self.item_model.remove_ncs_pathway(str(ncs.uuid))
            self.clear_description()


class ImplementationModelComponentWidget(ModelComponentWidget):
    """Widget for displaying and managing implementation models."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.item_model = IMItemModel(parent)

        self.lst_model_items.setAcceptDrops(True)
        self.lst_model_items.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.lst_model_items.setDropIndicatorShown(True)

    def models(self) -> typing.List[ImplementationModel]:
        """Returns a collection of ImplementationModel objects in the
        list view.

        :returns: Collection of ImplementationModel objects in the
        list view.
        :rtype: list
        """
        return self.item_model.models()

    def model_items(self) -> typing.List[ImplementationModelItem]:
        """Returns a collection of all ImplementationModelItem objects
        in the list view.

        :returns: Collection of ImplementationModelItem objects in
        the list view.
        :rtype: list
        """
        return self.item_model.model_items()

    def _on_add_item(self):
        """Show implementation model editor."""
        editor = ImplementationModelEditorDialog(self)
        if editor.exec_() == QtWidgets.QDialog.Accepted:
            model = editor.implementation_model
            self.item_model.add_implementation_model(model)

    def _on_edit_item(self):
        """Edit selected implementation model object."""
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            return

        item = selected_items[0]
        editor = ImplementationModelEditorDialog(self, item.implementation_model)
        if editor.exec_() == QtWidgets.QDialog.Accepted:
            model = editor.implementation_model
            self.item_model.update_implementation_model(model)
            self._update_ui_on_selection_changed()

    def _on_remove_item(self):
        """Delete implementation model object."""
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            return

        item = selected_items[0]
        model_component = item.model_component

        additional_note = ""
        if item.type() == IMPLEMENTATION_MODEL_TYPE:
            additional_note = self.tr("and the children pathways")

        msg = self.tr(
            f"Do you want to remove '{model_component.name}' {additional_note}?"
            f"\nClick Yes to proceed or No to cancel."
        )

        if (
            QtWidgets.QMessageBox.question(
                self,
                self.tr("Remove Implementation Model Item"),
                msg,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            == QtWidgets.QMessageBox.Yes
        ):
            # NCS pathway item
            if item.type() == NCS_PATHWAY_TYPE:
                parent = item.parent
                self.item_model.remove_ncs_pathway_item(item.uuid, parent)
            else:
                # Implementation model item
                self.item_model.remove_implementation_model(str(model_component.uuid))

            self.clear_description()

    def add_ncs_pathway_items(self, ncs_items: typing.List[NcsPathwayItem]) -> bool:
        """Adds an NCS pathway item to the collection.

        One, and only one, target implementation model item needs
        to have been selected.

        :param ncs_items: NCS pathway items to be added to the
        implementation model.
        :type ncs_items: list

        :returns: True if the item was successfully added, else False.
        :rtype: bool
        """
        selected_models = self.selected_items()
        if len(selected_models) == 0 or len(selected_models) > 1:
            return False

        sel_model = selected_models[0]

        # Use the parent to add the NCS item
        if sel_model.type() == NCS_PATHWAY_TYPE:
            if sel_model.parent is None:
                return False

            sel_model = sel_model.parent

        status = True
        for ncs_item in ncs_items:
            status = self.item_model.add_ncs_pathway(ncs_item, sel_model)

        return status

    def add_implementation_model(self, implementation_model: ImplementationModel):
        """Adds an implementation model object to the view.

        :param implementation_model: Implementation model object
        to be added to the view.
        :type implementation_model: ImplementationModel
        """
        self.item_model.add_implementation_model(implementation_model)

    def _update_ui_on_selection_changed(self):
        """Check type of item selected and update UI
        controls accordingly.
        """
        super()._update_ui_on_selection_changed()

        selected_items = self.selected_items()
        if len(selected_items) == 0:
            return

        if selected_items[0].type() == NCS_PATHWAY_TYPE:
            self.btn_edit.setEnabled(False)
