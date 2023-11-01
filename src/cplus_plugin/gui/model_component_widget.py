# -*- coding: utf-8 -*-
"""
Composite list view-based widgets for displaying implementation model
and NCS pathway items.
"""
import os
import typing

from qgis.PyQt import QtCore, QtWidgets
from qgis.PyQt.uic import loadUiType

from qgis.core import QgsApplication, QgsMapLayer

from .component_item_model import (
    ComponentItemModel,
    ComponentItemModelType,
    IMItemModel,
    ImplementationModelItem,
    IMPLEMENTATION_MODEL_TYPE,
    LAYER_ITEM_TYPE,
    ModelComponentItem,
    ModelComponentItemType,
    NcsPathwayItem,
    NcsPathwayItemModel,
    NCS_PATHWAY_TYPE,
)
from ..conf import settings_manager
from .implementation_model_editor_dialog import ImplementationModelEditorDialog
from .model_description_editor import ModelDescriptionEditorDialog
from .ncs_pathway_editor_dialog import NcsPathwayEditorDialog
from .pixel_value_editor_dialog import PixelValueEditorDialog
from ..models.base import ImplementationModel, NcsPathway
from ..utils import FileUtils, log


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

        add_icon = FileUtils.get_icon("symbologyAdd.svg")
        self.btn_add.setIcon(add_icon)
        self.btn_add.clicked.connect(self._on_add_item)

        remove_icon = FileUtils.get_icon("symbologyRemove.svg")
        self.btn_remove.setIcon(remove_icon)
        self.btn_remove.setEnabled(False)
        self.btn_remove.clicked.connect(self._on_remove_item)

        edit_icon = FileUtils.get_icon("mActionToggleEditing.svg")
        self.btn_edit.setIcon(edit_icon)
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_item)

        reload_icon = FileUtils.get_icon("mActionReload.svg")
        self.btn_reload.setIcon(reload_icon)
        self.btn_reload.setToolTip(self.tr("Refresh view"))
        self.btn_reload.clicked.connect(self._on_reload)

        self.btn_edit_description.setIcon(edit_icon)
        self.btn_edit_description.setToolTip(self.tr("Edit description"))
        self.btn_edit_description.setEnabled(False)
        self.btn_edit_description.clicked.connect(self._on_update_description)

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
    def selection_model(self) -> QtCore.QItemSelectionModel:
        """Gets the item's view selection model.

        :returns: The item's view selection model.
        :rtype: QtCore.QItemSelectionModel
        """
        return self.lst_model_items.selectionModel()

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
        self.lbl_title.setText(f"<b>{text}</b>")

    def load(self):
        """Subclass to determine how to initialize the items."""
        pass

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

    def _on_update_description(self):
        """Slot raised to edit the currently selected item."""
        sel_items = self.selected_items()
        if len(sel_items) == 0:
            return

        reference_item = sel_items[0]
        description_editor = ModelDescriptionEditorDialog(
            self, reference_item.description
        )
        title_tr = self.tr("Description Editor")
        description_editor.setWindowTitle(
            f"{reference_item.model_component.name} {title_tr}"
        )
        if description_editor.exec_() == QtWidgets.QDialog.Accepted:
            updated_description = description_editor.description
            reference_item.model_component.description = updated_description
            self.txt_item_description.setText(updated_description)
            self._save_item(reference_item)

    def _save_item(self, item: ComponentItemModelType):
        """Persist the changes in the underlying model for the given item.

        To be implemented by child classes as default implementation does
        nothing.
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
        self.btn_edit_description.setEnabled(True)

        # Remove description and disable edit and remove buttons if
        # more than one item has been selected.
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            self.clear_description()
            self.btn_remove.setEnabled(False)
            self.btn_edit.setEnabled(False)
            self.btn_edit_description.setEnabled(False)
            return

        if not isinstance(selected_items[0], ModelComponentItem):
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

    def clear(self):
        """Remove all items in the view. To be implemented
        by subclasses."""
        pass

    def _on_reload(self):
        """Slot raised when the reload button has been clicked.
        Default implementation is to call the load the items
        afresh.
        """
        self.load()

    def model_names(self) -> typing.List[str]:
        """Gets the names of the components in the item model.

        :returns: Returns the model names in lower case or an empty
        list if the item model has not been set.
        :rtype: list
        """
        if self._item_model is None:
            return []

        model_components = self._item_model.model_components()

        return [mc.name.lower() for mc in model_components]

    def add_action_widget(self, widget: QtWidgets.QWidget):
        """Adds an auxiliary widget below the list view from the left-hand side.

        :param widget: Widget to be added to the collection of controls
        below the list view.
        :type widget: QtWidgets.QWidget
        """
        self.widget_container.addWidget(widget)


class NcsComponentWidget(ModelComponentWidget):
    """Widget for displaying and managing NCS pathways."""

    ncs_pathway_updated = QtCore.pyqtSignal(NcsPathway)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.item_model = NcsPathwayItemModel(parent)

        self.lst_model_items.setDragEnabled(True)
        self.lst_model_items.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.lst_model_items.setAcceptDrops(False)

    def add_ncs_pathway(self, ncs_pathway: NcsPathway) -> bool:
        """Adds an NCS pathway object to the view.

        :param ncs_pathway: NCS pathway object to be added to the view.
        :type ncs_pathway: NcsPathway

        :returns: Returns True if the NcsPathway was successfully added,
        else False.
        :rtype: bool
        """
        return self.item_model.add_ncs_pathway(ncs_pathway)

    def clear(self):
        """Removes all NCS pathway items in the view."""
        items = self.ncs_items()
        for item in items:
            self.item_model.remove_ncs_pathway(item.uuid)

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
        ncs_editor = NcsPathwayEditorDialog(self, excluded_names=self.model_names())
        if ncs_editor.exec_() == QtWidgets.QDialog.Accepted:
            ncs_pathway = ncs_editor.ncs_pathway
            result = self.item_model.add_ncs_pathway(ncs_pathway)
            if result:
                settings_manager.save_ncs_pathway(ncs_pathway)

    def _on_edit_item(self):
        """Edit selected NCS pathway object."""
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            return

        item = selected_items[0]

        # If editing, remove the current name of the model component
        excluded_names = self.model_names()
        excluded_names.remove(item.model_component.name.lower())

        ncs_editor = NcsPathwayEditorDialog(
            self, item.ncs_pathway, excluded_names=excluded_names
        )
        if ncs_editor.exec_() == QtWidgets.QDialog.Accepted:
            ncs_pathway = ncs_editor.ncs_pathway
            result = self.item_model.update_ncs_pathway(ncs_pathway)
            if result:
                self._save_item(item)
                self.ncs_pathway_updated.emit(ncs_pathway)
            self._update_ui_on_selection_changed()

    def _save_item(self, item: NcsPathwayItem):
        """Update the NCS pathway in settings."""
        cloned_ncs_item = item.clone()
        cloned_ncs = cloned_ncs_item.ncs_pathway
        settings_manager.update_ncs_pathway(cloned_ncs)

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
            settings_manager.remove_ncs_pathway(str(ncs.uuid))
            self.clear_description()

    def load(self):
        """Load items from settings."""
        self.clear()

        settings_manager.update_ncs_pathways()
        ncs_pathways = settings_manager.get_all_ncs_pathways()

        progress_dialog = QtWidgets.QProgressDialog(self)
        progress_dialog.setWindowTitle(self.tr("Load NCS Pathways"))
        progress_dialog.setMinimum(0)
        progress_dialog.setMaximum(len(ncs_pathways))
        progress_dialog.setLabelText(self.tr("Updating NCS pathways..."))
        for i, ncs in enumerate(ncs_pathways, start=1):
            progress_dialog.setValue(i)
            if progress_dialog.wasCanceled():
                break
            self.add_ncs_pathway(ncs)


class ImplementationModelComponentWidget(ModelComponentWidget):
    """Widget for displaying and managing implementation models."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.item_model = IMItemModel(parent)
        self.item_model.im_pathways_updated.connect(self.on_pathways_updated)

        self.lst_model_items.setAcceptDrops(True)
        self.lst_model_items.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.lst_model_items.setDropIndicatorShown(True)

        self.btn_reload.setVisible(False)

        self.btn_pixel_editor = None

        self.add_auxiliary_widgets()

    def models(self) -> typing.List[ImplementationModel]:
        """Returns a collection of ImplementationModel objects in the
        list view.

        :returns: Collection of ImplementationModel objects in the
        list view.
        :rtype: list
        """
        return self.item_model.models()

    def add_auxiliary_widgets(self):
        """Adds additional action widgets for managing implementation models."""
        self.btn_pixel_editor = QtWidgets.QToolButton(self)
        style_icon = FileUtils.get_icon("rendererCategorizedSymbol.svg")
        self.btn_pixel_editor.setIcon(style_icon)
        self.btn_pixel_editor.setToolTip(
            self.tr("Show dialog for ordering pixel values for styling.")
        )
        self.btn_pixel_editor.clicked.connect(self.on_show_pixel_value_editor)
        self.add_action_widget(self.btn_pixel_editor)

    def on_show_pixel_value_editor(self):
        """Slot raised to show editor dialog for managing IM pixel values for styling."""
        pixel_dialog = PixelValueEditorDialog(self)
        if pixel_dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Update pixel values
            pixel_values = pixel_dialog.item_mapping
            for val, im_id in pixel_values.items():
                imp_model = settings_manager.get_implementation_model(im_id)
                if not imp_model:
                    continue
                imp_model.style_pixel_value = val
                settings_manager.update_implementation_model(imp_model)

    def model_names(self) -> typing.List[str]:
        """Gets the names of the implementation models in the item model.

        :returns: Returns the names of implementation models in lower
        case or an empty list if the item model has not been set.
        :rtype: list
        """
        if self._item_model is None:
            return []

        model_components = self._item_model.models()

        return [mc.name.lower() for mc in model_components]

    def on_pathways_updated(self, im_item: ImplementationModelItem):
        """Slot raised when the pathways of an ImplementationModelItem
        have been added or removed. Persist this information in settings.
        """
        self._save_item(im_item)

    def model_items(self) -> typing.List[ImplementationModelItem]:
        """Returns a collection of all ImplementationModelItem objects
        in the list view.

        :returns: Collection of ImplementationModelItem objects in
        the list view.
        :rtype: list
        """
        return self.item_model.model_items()

    def clear(self):
        """Removes all implementation model items in the view."""
        items = self.model_items()
        for item in items:
            self.item_model.remove_implementation_model(item.uuid)

    def load(self):
        """Load implementation models from settings."""
        self.clear()

        for imp_model in settings_manager.get_all_implementation_models():
            self.add_implementation_model(imp_model)

    def _on_add_item(self):
        """Show implementation model editor."""
        editor = ImplementationModelEditorDialog(
            self, excluded_names=self.model_names()
        )
        if editor.exec_() == QtWidgets.QDialog.Accepted:
            model = editor.implementation_model
            layer = editor.layer
            num_models = len(settings_manager.get_all_implementation_models())
            model.style_pixel_value = num_models + 1
            result = self.item_model.add_implementation_model(model, layer)
            if result:
                settings_manager.save_implementation_model(model)

    def _on_edit_item(self):
        """Edit selected implementation model object."""
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            return

        item = selected_items[0]

        # If editing, remove the current name of the model component
        excluded_names = self.model_names()
        excluded_names.remove(item.model_component.name.lower())

        editor = ImplementationModelEditorDialog(
            self, item.implementation_model, excluded_names=excluded_names
        )
        if editor.exec_() == QtWidgets.QDialog.Accepted:
            model = editor.implementation_model
            layer = editor.layer
            result = self.item_model.update_implementation_model(model, layer)
            if result:
                self._save_item(item)
            self._update_ui_on_selection_changed()

    def _save_item(self, item: ImplementationModelItem):
        """Update the underlying IM in the item in settings."""
        cloned_im_item = item.clone()
        cloned_im = cloned_im_item.implementation_model
        settings_manager.update_implementation_model(cloned_im)

    def _on_remove_item(self):
        """Delete implementation model object."""
        selected_items = self.selected_items()
        if len(selected_items) == 0 or len(selected_items) > 1:
            return

        item = selected_items[0]
        model_component = None
        if isinstance(item, ModelComponentItem):
            is_model_component_item = True
            model_component = item.model_component
        else:
            is_model_component_item = False

        additional_note = ""

        if is_model_component_item:
            if item.type() == IMPLEMENTATION_MODEL_TYPE:
                additional_note = self.tr("and its children")

            msg = self.tr(
                f"Do you want to remove '{model_component.name}' {additional_note}?"
                f"\nClick Yes to proceed or No to cancel."
            )
        else:
            msg = self.tr(
                "Do you want to remove the layer for the implementation model?"
                "\nClick Yes to proceed or No to cancel"
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
            if is_model_component_item:
                # NCS pathway item
                if item.type() == NCS_PATHWAY_TYPE:
                    parent = item.parent
                    self.item_model.remove_ncs_pathway_item(item.uuid, parent)
                else:
                    # Implementation model item
                    implementation_model_uuid = str(model_component.uuid)
                    result = self.item_model.remove_implementation_model(
                        implementation_model_uuid
                    )
                    if result:
                        ref_pixel_value = model_component.style_pixel_value
                        settings_manager.remove_implementation_model(
                            implementation_model_uuid
                        )

                        # Reassign pixel values accordingly
                        self.reassign_pixel_values(ref_pixel_value)
            else:
                implementation_model_item = item.data()
                if implementation_model_item:
                    self.item_model.remove_layer(implementation_model_item)
                    self._save_item(implementation_model_item)

            self.clear_description()

    @classmethod
    def reassign_pixel_values(cls, start_position: int):
        """Reassign the styling pixel values for implementation models
        from the given start position.

        It is important to call this function when the maximum pixel
        value does not match the number of implementation models such
        as when one or more implementation models have been deleted.

        :param start_position: Position to start reassigning the pixel
        values.
        :type start_position: int
        """
        sorted_models = sorted(
            settings_manager.get_all_implementation_models(),
            key=lambda model: model.style_pixel_value,
        )
        remap_models = sorted_models[start_position:]
        for val, imp_model in enumerate(remap_models, start=start_position):
            imp_model.style_pixel_value = val
            settings_manager.update_implementation_model(imp_model)
            print(f"{imp_model.name} - {val!s}")

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
        item_type = sel_model.type()

        # Use the parent to add the NCS item
        if item_type == NCS_PATHWAY_TYPE:
            if sel_model.parent is None:
                return False

            sel_model = sel_model.parent

        elif item_type == LAYER_ITEM_TYPE:
            return False

        status = True
        for ncs_item in ncs_items:
            status = self.item_model.add_ncs_pathway(ncs_item, sel_model)

        return status

    def add_implementation_model(
        self, implementation_model: ImplementationModel, layer: QgsMapLayer = None
    ):
        """Adds an implementation model object to the view with the option of
        specifying the layer.

        :param implementation_model: Implementation model object
        to be added to the view.
        :type implementation_model: ImplementationModel

        :param layer: Optional map layer to be added to the model.
        :type layer: QgsMapLayer

        :returns: True if the implementation model was successfully added, else
        False.
        :rtype: bool
        """
        return self.item_model.add_implementation_model(implementation_model, layer)

    def _update_ui_on_selection_changed(self):
        """Check type of item selected and update UI
        controls accordingly.
        """
        super()._update_ui_on_selection_changed()

        selected_items = self.selected_items()
        if len(selected_items) == 0:
            return

        item = selected_items[0]
        self.btn_edit.setEnabled(False)
        self.btn_edit_description.setEnabled(False)
        if item.type() == IMPLEMENTATION_MODEL_TYPE:
            self.btn_edit.setEnabled(True)
            self.btn_edit_description.setEnabled(True)

    def update_ncs_pathway_items(self, ncs_pathway: NcsPathway) -> bool:
        """Update NCS pathway items used for IMs that are linked to the
        given NCS pathway.

        :param ncs_pathway: NCS pathway whose attribute values will be updated
        for the related pathways used in the IMs.
        :type ncs_pathway: NcsPathway

        :returns: True if NCS pathway items were updated, else False.
        :rtype: bool
        """
        return self.item_model.update_ncs_pathway_items(ncs_pathway)
