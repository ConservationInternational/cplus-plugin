# -*- coding: utf-8 -*-
"""
Contains item models for view widgets such as NCS pathway or IM views.
"""
from abc import abstractmethod
import typing

from qgis.PyQt import QtCore, QtGui, QtWidgets

from ..models.base import (
    BaseModelComponent,
    BaseModelComponentType,
    ImplementationModel,
    LayerType,
    NcsPathway,
)


NCS_PATHWAY_TYPE = QtGui.QStandardItem.UserType + 2
IMPLEMENTATION_MODEL_TYPE = QtGui.QStandardItem.UserType + 3


class ModelComponentItem(QtGui.QStandardItem):
    """Base standard item for a BaseModelComponent object."""

    def __init__(self, model_component: BaseModelComponent):
        super().__init__(model_component.name)
        self.setToolTip(model_component.name)

        self._model_component = model_component
        if self._model_component is not None:
            self.update(self._model_component)

    def update(self, model_component: BaseModelComponent):
        """Update the component-related properties of the item."""
        if model_component is None:
            return

        self._model_component = model_component
        self.setText(model_component.name)
        self.setToolTip(model_component.name)

    @property
    def model_component(self) -> BaseModelComponent:
        """Returns an instance of the underlying model component object.

        :returns: Instance of underlying model component object.
        :rtype: BaseModelComponent
        """
        return self._model_component

    @property
    def uuid(self) -> str:
        """Returns the UUID of the item.

        :returns: UUID of the item.
        :rtype: str
        """
        if self._model_component is None:
            return ""

        return str(self._model_component.uuid)

    @property
    def description(self) -> str:
        """Returns the description of the item.

        :returns: Description of the item.
        :rtype: str
        """
        if self._model_component is None:
            return ""

        return str(self._model_component.description)

    @staticmethod
    @abstractmethod
    def create(model_component: BaseModelComponent) -> "ModelComponentItem":
        """Factory method for creating an instance of a model item.

        This is an abstract method that needs to be implemented by
        subclasses.

        :param model_component: Source model component for creating the
        corresponding item.
        :type model_component: BaseModelComponent

        :returns: Model component item for use in a standard item model.
        :rtype: ModelComponentItem
        """
        pass

    @abstractmethod
    def clone(self) -> "ModelComponentItemType":
        """Creates a deep copied version of the model item.

        :returns: Cloned version of the model item containing all
        the properties as the source.
        :rtype: ModelComponentItem
        """
        pass


ModelComponentItemType = typing.TypeVar(
    "ModelComponentItemType", bound=ModelComponentItem
)


class NcsPathwayItem(ModelComponentItem):
    """Standard item for an NCS pathway object."""

    def __init__(self, ncs: NcsPathway):
        super().__init__(ncs)
        self._ncs_pathway = ncs

    def is_valid(self) -> bool:
        """Checks whether the map layer of the underlying NcsPathway object is valid.

        :returns: True if the map layer is valid, else False if map layer is
        invalid or of None type.
        :rtype: bool
        """
        if self._ncs_pathway is None:
            return False

        return self._ncs_pathway.is_valid()

    @property
    def ncs_pathway(self) -> NcsPathway:
        """Returns an instance of the underlying NcsPathway object.

        :returns: The underlying NcsPathway model object.
        :rtype: NcsPathway
        """
        return self._ncs_pathway

    def type(self) -> int:
        """Returns the type of the standard item.

        :returns: Type identifier of the standard item.
        :rtype: int
        """
        return NCS_PATHWAY_TYPE

    @staticmethod
    def create(ncs: NcsPathway) -> "NcsPathwayItem":
        """Creates an instance of the NcsPathwayItem from the model object.

        :returns: An instance of the NcsPathway item to be used in a standard
        model.
        :rtype: NcsPathwayItem
        """
        return NcsPathwayItem(ncs)

    def clone(self) -> "NcsPathwayItem":
        """Creates a cloned version of this item."""
        return NcsPathwayItem(self.ncs_pathway)


class ImplementationModelItem(ModelComponentItem):
    """Standard item for an implementation model object."""

    def __init__(self, implementation_model: ImplementationModel):
        super().__init__(implementation_model)
        self._implementation_model = implementation_model

        font = self.font()
        font.setBold(True)
        self.setFont(font)

        self._ncs_items = []

    @property
    def implementation_model(self) -> ImplementationModel:
        """Returns an instance of the underlying ImplementationModel object.

        :returns: The underlying ImplementationModel object.
        :rtype: ImplementationModel
        """
        return self._implementation_model

    @property
    def ncs_items(self) -> typing.List[NcsPathwayItem]:
        """Returns a collection of NcsPathwayItem in this implementation
        model.

        :returns: Collection of NcsPathwayItem objects in this
        implementation model.
        :rtype: list
        """
        return self._ncs_items

    def ncs_item_by_uuid(self, uuid: str) -> typing.Union[NcsPathwayItem, None]:
        """Returns an NcsPathway item matching the given UUID.

        :param uuid: UUID of the NcsPathway item to retrieve.
        :type uuid: str

        :returns: NcsPathwayItem matching the given UUID, else None
        if not found.
        :rtype: NcsPathwayItem
        """
        ncs_items = [n for n in self._ncs_items if n.uuid == uuid]

        if len(ncs_items) == 0:
            return None

        return ncs_items[0]

    def contains_ncs_item(self, uuid: str) -> bool:
        """Checks whether this items contains an NcsPathway item with
        the given UUID.

        :param uuid: UUID of the NcsPathway item to search for.
        :type uuid: str

        :returns: True if there is an NcsPathwayItem matching the
        given UUID, else False.
        :rtype: bool
        """
        if self.ncs_item_by_uuid(uuid) is None:
            return False

        return True

    def add_ncs_pathway_item(self, ncs_item: NcsPathwayItem) -> bool:
        """Adds an NCS pathway item to this item.

        :param ncs_item: NCS pathway item to the collection.
        :type ncs_item: NcsPathwayItem

        :returns: True if the NCS pathway item was successfully added, else
        False if there underlying NCS pathway object was invalid or there
        is an existing item with the same UUID.
        """
        if self.contains_ncs_item(ncs_item.uuid):
            return False

        if not ncs_item.is_valid():
            return False

        if self._implementation_model.contains_pathway(ncs_item.uuid):
            return False

        self._implementation_model.add_ncs_pathway(ncs_item.ncs_pathway)
        self._ncs_items.append(ncs_item)

        return True

    def type(self) -> int:
        """Returns the type of the standard item.

        :returns: Type identifier of the standard item.
        :rtype: int
        """
        return IMPLEMENTATION_MODEL_TYPE

    @staticmethod
    def create(implementation_model: ImplementationModel) -> "ImplementationModelItem":
        """Creates an instance of the ImplementationModelItem from
        the model object.

        :returns: An instance of the ImplementationModelItem item to
        be used in a standard model.
        :rtype: ImplementationModel
        """
        return ImplementationModelItem(implementation_model)

    def clone(self) -> "ImplementationModelItem":
        """Creates a cloned version of this item."""
        return ImplementationModelItem(self.implementation_model)


class ComponentItemModel(QtGui.QStandardItemModel):
    """View model for ModelComponent objects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)

        self._uuid_row_idx = {}

    def add_component_item(
        self, component_item: ModelComponentItem, position=-1
    ) -> bool:
        """Adds a model component item to the view model.

        :param component_item: Model component item to be added to the view
        model.
        :type component_item: ModelComponentItem

        :param position: Reference row to insert the item.
        :type position: int

        :returns: True if the component item was successfully added, else
        False if there is an existing component item with the same UUID.
        :rtype: bool
        """
        idx = position
        if position == -1:
            idx = self.rowCount()

        if self.contains_item(str(component_item.uuid)):
            return False

        self.insertRow(idx, component_item)

        self._uuid_row_idx[component_item.uuid] = idx

        return True

    def contains_item(self, uuid: str) -> bool:
        """Checks if the model contains an item with the given UUID.

        :param uuid: UUID of the model item.
        :type uuid: str

        :returns: True if there is an existing item else False.
        :rtype: bool
        """
        return True if self.component_item_by_uuid(uuid) is not None else False

    def component_item_by_uuid(
        self, uuid: str
    ) -> typing.Union[ModelComponentItemType, None]:
        """Retrieves a ModelComponentItem based on a matching UUID.

        :param uuid: UUID of the model item.
        :type uuid: str

        :returns: Component item matching the given UUID or None if not found.
        :rtype: ModelComponentItem
        """
        if uuid not in self._uuid_row_idx:
            return None

        idx = self._uuid_row_idx[uuid]

        return self.item(idx)

    def update_item(self, item: ModelComponentItemType) -> bool:
        """Update an existing ModelComponentItem if it exists in the model.

        :param item: An updated instance of the ModelComponentItem.
        :type item: ModelComponentItem

        :returns: True if the item was successfully updated, else False
        if there was no matching item found in the model.
        :rtype: bool
        """
        if not self.contains_item(item.uuid):
            return False

        item.update(item.model_component)

        return True

    def model_components(self) -> typing.List[BaseModelComponentType]:
        """Returns a collection of all model component objects in the model.

        :returns: A collection of all model component objects.
        :rtype: list
        """
        rows = self.rowCount()

        return [self.item(r).model_component for r in range(rows)]

    def _re_index_rows(self):
        """Remap UUIDs with corresponding row numbers.

        Not the most ideal but should suffice for a small number of
        rows.
        """
        rows = self.rowCount()
        self._uuid_row_idx = {self.item(r).uuid: r for r in range(rows)}

    def remove_component_item(self, uuid: str) -> bool:
        """Removes a ModelComponentItem based on a matching UUID.

        :param uuid: UUID of the model item to be removed.
        :type uuid: str

        :returns: True if the component item was successfully removed, else
        False if there was not matching UUID.
        :rtype: bool
        """
        if not self.contains_item(uuid):
            return False

        if uuid not in self._uuid_row_idx:
            return False

        self.removeRows(self._uuid_row_idx[uuid], 1)
        del self._uuid_row_idx[uuid]

        self._re_index_rows()

        return True


ComponentItemModelType = typing.TypeVar(
    "ComponentItemModelType", bound=ComponentItemModel
)


class NcsPathwayItemModel(ComponentItemModel):
    """View model for NCS pathways."""

    def add_ncs_pathway(self, ncs: NcsPathway) -> bool:
        """Add an NCS pathway object to the model.

        :param ncs: NCS pathway object to the added to the view.
        :type ncs: NcsPathway

        :returns: True if the NCS pathway object was added successfully,
        else False.
        :rtype: bool
        """
        ncs_item = NcsPathwayItem.create(ncs)
        self._update_foreground(ncs_item)

        return self.add_component_item(ncs_item)

    def update_ncs_pathway(self, ncs: NcsPathway) -> bool:
        """Updates the NCS pathway item in the model.

        :param ncs: NcsPathway whose corresponding item is to be updated.
        :type ncs: NcsPathway

        :returns: Returns True if the operation was successful else False
        if the matching item was not found in the model.
        """
        item = self.component_item_by_uuid(str(ncs.uuid))
        if item is None:
            return False

        status = self.update_item(item)
        if not status:
            return False

        self._update_foreground(item)

        return True

    def _update_foreground(self, item: NcsPathwayItem):
        """Update text colour based on whether an item is valid or invalid."""
        # Set to red color if NCS pathway object is invalid.
        ncs = item.ncs_pathway
        foreground = item.foreground()

        if ncs.is_valid():
            foreground.setColor(QtCore.Qt.black)
            item.setForeground(foreground)
        else:
            foreground.setColor(QtCore.Qt.red)
            item.setForeground(foreground)

    def pathways(self, valid_only: bool = False) -> typing.List[NcsPathway]:
        """Returns NCS pathway objects in the model.

        :param valid_only: Whether to only return NCS pathway objects
        that are valid.
        :type valid_only: bool

        :returns: All NCS pathway objects in the model (default), else only
        those NCS pathway objects that are valid if valid_only is True.
        :rtype: list
        """
        ncs_pathways = self.model_components()

        if valid_only:
            return [p for p in ncs_pathways if p.is_valid()]

        return ncs_pathways

    def remove_ncs_pathway(self, uuid: str) -> bool:
        """Remove an NCS pathway item from the model.

        param uuid: UUID of the NCS pathway item to be removed.
        :type uuid: str

        :returns: True if the NCS pathway item as successfully
        removed, else False if there was not matching UUID.
        :rtype: bool
        """
        return self.remove_component_item(uuid)


class IMItemModel(ComponentItemModel):
    """View model for implementation model."""

    def add_implementation_model(
        self, implementation_model: ImplementationModel
    ) -> bool:
        """Add an ImplementationModel object to the model.

        :param implementation_model: ImplementationModel object to be
        added to the view.
        :type implementation_model: ImplementationModel

        :returns: True if ImplementationModel object was added
        successfully, else False.
        :rtype: bool
        """
        implementation_model_item = ImplementationModelItem.create(implementation_model)

        return self.add_component_item(implementation_model_item)

    def add_ncs_pathway(
        self, ncs_item: NcsPathwayItem, target_model: ImplementationModelItem
    ) -> bool:
        """Adds an NCS pathway item to the model.

        :param ncs_item: NCS pathway item to the collection.
        :type ncs_item: NcsPathwayItem

        :param target_model: Target implementation model for the NCS item.
        :type target_model: ImplementationModelItem

        :returns: True if the NCS pathway item was successfully added, else
        False if there underlying NCS pathway object was invalid or there
        is an existing item with the same UUID.
        """
        idx = target_model.index()
        if not idx.isValid():
            return False

        clone_ncs = ncs_item.clone()

        status = target_model.add_ncs_pathway_item(clone_ncs)
        if not status:
            return False

        row = idx.row() + 1
        self.add_component_item(clone_ncs, row)

        return True

    def update_implementation_model(
        self, implementation_model: ImplementationModel
    ) -> bool:
        """Updates the implementation model item in the model.

        :param implementation_model: implementation_model object whose
        corresponding item is to be updated.
        :type implementation_model: ImplementationModel

        :returns: Returns True if the operation was successful else False
        if the matching item was not found in the model.
        """
        item = self.component_item_by_uuid(str(implementation_model.uuid))
        if item is None:
            return False

        status = self.update_item(item)
        if not status:
            return False

        return True

    def models(self) -> typing.List[ImplementationModel]:
        """Returns implementation model objects in the model.

        :returns: All implementation model objects in the model.
        :rtype: list
        """
        return self.model_components()

    def remove_implementation_model(self, uuid: str) -> bool:
        """Remove an implementation model item from the model.

        param uuid: UUID of the implementation model item to
        be removed.
        :type uuid: str

        :returns: True if the implementation model item as successfully
        removed, else False if there was not matching UUID.
        :rtype: bool
        """
        return self.remove_component_item(uuid)
