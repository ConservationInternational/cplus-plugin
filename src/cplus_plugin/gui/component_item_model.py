# -*- coding: utf-8 -*-
"""
Contains item models for view widgets such as NCS pathway or IM views.
"""
import uuid
from abc import abstractmethod
from copy import deepcopy
import json
import typing
from uuid import uuid4

from qgis.PyQt import QtCore, QtGui

from ..models.base import (
    BaseModelComponent,
    BaseModelComponentType,
    ImplementationModel,
    LayerType,
    NcsPathway,
)


NCS_PATHWAY_TYPE = QtGui.QStandardItem.UserType + 2
IMPLEMENTATION_MODEL_TYPE = QtGui.QStandardItem.UserType + 3

NCS_MIME_TYPE = "application/x-qabstractitemmodeldatalist"


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
        self._parent = None

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

    @property
    def parent(self) -> "ImplementationModelItem":
        """Returns the parent ImplementationModelItem if specified.

        :returns: Returns the parent item if set when this item is
        mapped to an ImplementationModelItem.
        :rtype: ImplementationModelItem
        """
        return self._parent

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
        ncs = deepcopy(self.ncs_pathway)

        return NcsPathwayItem(ncs)

    def json_data(self) -> str:
        """Creates a mapping of NCS pathway property names
        and their corresponding values.

        :returns: JSON representation of property name-value
        pairs for an NCS pathway object.
        :rtype: str
        """
        ncs_attrs = {
            "uuid": str(self.ncs_pathway.uuid),
            "name": self.ncs_pathway.name,
            "description": self.ncs_pathway.description,
            "path": self.ncs_pathway.path,
            "layer_type": self.ncs_pathway.layer_type,
            "user_defined": self.ncs_pathway.user_defined,
        }

        return json.dumps(ncs_attrs)


class ImplementationModelItem(ModelComponentItem):
    """Standard item for an implementation model object."""

    def __init__(self, implementation_model: ImplementationModel):
        super().__init__(implementation_model)
        self._implementation_model = implementation_model

        font = self.font()
        font.setBold(True)
        self.setFont(font)

        self._ncs_items = []

        # Remap pathway uuids so that there are no duplicate
        # pathways under each implementation model.
        self._uuid_remap = {}

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

    @property
    def ncs_pathways(self) -> typing.List[NcsPathway]:
        """Returns a collection of NcsPathway objects.

        :returns: Collection of NcsPathway objects linked to the
        underlying ImplementationModel object.
        :rtype: list
        """
        return [ncs_item.ncs_pathway for ncs_item in self.ncs_items]

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
        """Checks whether this item contains an NcsPathway item with
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
        old_uuid = ncs_item.uuid
        new_uuid = uuid4()
        ncs_item.ncs_pathway.uuid = new_uuid

        if old_uuid in self._uuid_remap:
            return False

        if self.contains_ncs_item(ncs_item.uuid):
            return False

        if not ncs_item.is_valid():
            return False

        if self._implementation_model.contains_pathway(ncs_item.uuid):
            return False

        self._implementation_model.add_ncs_pathway(ncs_item.ncs_pathway)
        self._ncs_items.append(ncs_item)
        ncs_item._parent = self

        self._uuid_remap[old_uuid] = str(new_uuid)

        return True

    def remove_ncs_pathway_item(self, uuid: str) -> bool:
        """Removes the NcsPathwayItem matching the given UUID.

        :param uuid: The UUID of the NcsPathwayItem to remove.
        :type uuid: str

        :returns: True if the item was successfully removed, else
        False.
        :rtype: bool
        """
        if not self.contains_ncs_item(uuid):
            return False

        idxs = [i for i, n in enumerate(self._ncs_items) if n.uuid == uuid]
        if len(idxs) == 0:
            return False

        item = self._ncs_items.pop(idxs[0])
        item._parent = None
        del item

        self._implementation_model.remove_ncs_pathway(uuid)

        old_uuids = [k for k, v in self._uuid_remap.items() if v == uuid]
        if len(old_uuids) > 0:
            del self._uuid_remap[old_uuids[0]]

        return True

    def bottom_ncs_item_index(self) -> typing.Union[QtCore.QModelIndex, None]:
        """Returns the model index of the bottom-most NcsPathwayItem
        under this implementation model item.

        :returns: Model index of the bottom-most NcsPathwayItem.
        :rtype: QModelIndex
        """
        if len(self._ncs_items) == 0:
            return None

        bottom_ncs_item = max(self._ncs_items, key=lambda n: n.index().row())

        return bottom_ncs_item.index()

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
        """Creates a cloned version of this item.

        Please note that the UUID of the cloned item will change.
        """
        implementation_model = deepcopy(self.implementation_model)

        return ImplementationModelItem(implementation_model)


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

        self._re_index_rows()

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

    def model_component_items(self) -> typing.List[ModelComponentItem]:
        """Returns all model component items in the model.

        :returns: Model component items in the model.
        :rtype: list
        """
        rows = self.rowCount()

        return [self.item(r) for r in range(rows)]

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

    def supportedDropActions(self) -> QtCore.Qt.DropActions:
        """Configure the model to only support copying items in a
        drag-and-drop operation.

        :returns: Supported drag-and-drop action for NCS pathway
        items.
        :rtype: QtCore.Qt.DropActions
        """
        return QtCore.Qt.CopyAction

    def mimeTypes(self) -> typing.List[str]:
        """Returns supported MIME types that can be used to
        describe a list of model indexes for NCS pathway items.

        :returns: MIME type for NCS pathway items which is JSON
        string but MIME type is the default datalist type for Qt
        since it does not allow custom types.
        :rtype: list
        """
        return [NCS_MIME_TYPE]

    def mimeData(self, indexes: typing.List[QtCore.QModelIndex]) -> QtCore.QMimeData:
        """Serializes the NCS items corresponding to the specified indexes.

        :param indexes: NCS items stored in the specified indexes.
        :type indexes: list

        :returns: Mime object containing serialized NCS items.
        :rtype: QtCore.QMimeData
        """
        mime_data = QtCore.QMimeData()
        item_data = QtCore.QByteArray()
        data_stream = QtCore.QDataStream(item_data, QtCore.QIODevice.WriteOnly)

        for idx in indexes:
            if not idx.isValid():
                continue

            ncs_item = self.itemFromIndex(idx)
            if ncs_item is None:
                continue

            ncs_data = QtCore.QByteArray()
            ncs_data.append(ncs_item.json_data())
            data_stream << ncs_data

        mime_data.setData(NCS_MIME_TYPE, item_data)

        return mime_data


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

        bottom_idx = target_model.bottom_ncs_item_index()
        reference_row = max(bottom_idx.row(), idx.row())
        self.add_component_item(clone_ncs, reference_row + 1)

        return True

    def remove_ncs_pathway_item(
        self, ncs_uuid: str, parent: ImplementationModelItem
    ) -> bool:
        """Remove an NCS pathway item from the model.

        param uuid: UUID of the NCS pathway item to be removed.
        :type ncs_uuid: str

        :param parent: Reference implementation model item that
        is the parent to the NCS pathway item.
        :type parent: ImplementationModelItem

        :returns: True if the NCS pathway item has been
        successfully removed, else False if there was
        no matching UUID.
        :rtype: bool
        """
        status = parent.remove_ncs_pathway_item(ncs_uuid)
        if not status:
            return False

        return self.remove_component_item(ncs_uuid)

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
        return [model_item.implementation_model for model_item in self.model_items()]

    def model_items(self) -> typing.List[ImplementationModelItem]:
        """Returns all ImplementationModelItem objects in the model.

        :returns: All implementation model items in the model.
        :rtype: list
        """
        component_items = self.model_component_items()

        return [ci for ci in component_items if ci.type() == IMPLEMENTATION_MODEL_TYPE]

    def remove_implementation_model(self, uuid: str) -> bool:
        """Remove an implementation model item from the model.

        param uuid: UUID of the implementation model item to
        be removed.
        :type uuid: str

        :returns: True if the implementation model item as successfully
        removed, else False if there was not matching UUID.
        :rtype: bool
        """
        implementation_model = self.component_item_by_uuid(uuid)
        if implementation_model is None:
            return False

        ncs_items = implementation_model.ncs_items
        for item in ncs_items:
            self.remove_component_item(item.uuid)

        return self.remove_component_item(uuid)

    def flags(self, index):
        flags = super().flags(index)

        return QtCore.Qt.ItemIsDropEnabled | flags

    def dropMimeData(
        self,
        data: QtCore.QMimeData,
        action: QtCore.Qt.DropAction,
        row: int,
        column: int,
        parent: QtCore.QModelIndex,
    ) -> bool:
        """Implements behaviour for handling data supplied by drag
        and drop operation.

        :param data: Object containing data from the drag operation.
        :type data: QtCore.QMimeData

        :param action: Type of the drag and drop operation.
        :type action: QtCore.Qt.DropAction

        :param row: Row location of dropped data.
        :type row: int

        :param column: Column location of dropped data.
        :type column: int

        :param parent: Index location for target item where the
        operation ended.
        :type parent: QtCore.QModelIndex

        :returns: True if the data and action can be handled by the
        model, else False.
        :rtype: bool
        """
        if action == QtCore.Qt.IgnoreAction:
            return True

        if not data.hasFormat(NCS_MIME_TYPE):
            return False

        encoded_data = data.data(NCS_MIME_TYPE)
        data_stream = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)

        ncs_items = []

        while not data_stream.atEnd():
            byte_data = QtCore.QByteArray()
            data_stream >> byte_data

            item_data = json.loads(byte_data.data())
            ncs_pathway = NcsPathway(
                uuid.UUID(item_data["uuid"]),
                item_data["name"],
                item_data["description"],
                item_data["path"],
                LayerType(int(item_data["layer_type"])),
                bool(item_data["user_defined"]),
            )

            ncs_item = NcsPathwayItem(ncs_pathway)
            ncs_items.append(ncs_item)

        # Get reference ImplementationModel item
        if parent.isValid():
            model_component = self.itemFromIndex(parent)
        else:
            row_count = self.rowCount()
            model_component = self.item(row_count - 1)

        if model_component is None:
            return False

        if model_component.type() == NCS_PATHWAY_TYPE:
            target_im_item = model_component.parent
        else:
            target_im_item = model_component

        # Add NCS items to model.
        status = True
        for item in ncs_items:
            status = self.add_ncs_pathway(item, target_im_item)

        return status
