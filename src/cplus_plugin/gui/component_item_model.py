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


ModelComponentItemType = typing.TypeVar(
    "ModelComponentItemType", bound=ModelComponentItem
)


class ComponentItemModel(QtGui.QStandardItemModel):
    """View model for ModelComponent objects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)

        self._uuid_row_idx = {}

    def add_component_item(self, component_item: ModelComponentItem) -> bool:
        """Adds a model component item to the view model.

        :param component_item: Model component item to be added to the view
        model.
        :type component_item: ModelComponentItem

        :returns: True if the component item was successfully added, else
        False if there is an existing component item with the same UUID.
        :rtype: bool
        """
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
        """Updates the item for the corresponding item in the model.

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
