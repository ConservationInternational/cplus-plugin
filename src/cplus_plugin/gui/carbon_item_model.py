# -*- coding: utf-8 -*-
"""
MVC model for carbon layer paths.
"""
import os
import typing
from pathlib import Path

from qgis.core import QgsRasterLayer

from qgis.PyQt import QtCore, QtGui

from ..utils import FileUtils, tr


class CarbonLayerItem(QtGui.QStandardItem):
    """Represents a single carbon layer path."""

    def __init__(self, layer_path: str):
        super().__init__()

        self._layer_path = layer_path
        self._is_valid = True
        self.update(self._layer_path)

    @property
    def is_valid(self) -> bool:
        """Returns the validity status of the carbon layer path.

        The path could be invalid if it does not exist or if the
        corresponding map layer is invalid.

        :returns: True if valid, else False.
        :rtype: bool
        """
        return self._is_valid

    @property
    def layer_path(self) -> str:
        """Returns the path to the carbon layer.

        :returns: Path to the carbon layer.
        :rtype: str
        """
        return self._layer_path

    def update(self, layer_path: str):
        """Update the UI properties."""
        if self._layer_path.startswith("cplus://"):
            paths = self._layer_path.split("/")
            self.setText(f"Online Default: {paths[-1]}")
            self.setToolTip(f"Online Default: {paths[-1]}")
            self._is_valid = True
            self.setIcon(QtGui.QIcon())
            return
        self._layer_path = str(os.path.normpath(layer_path))
        p = Path(self._layer_path)
        self.setText(p.name)
        self.setToolTip(self._layer_path)

        # Check validity
        if p.exists():
            layer = QgsRasterLayer(layer_path)
            if layer.isValid():
                self._is_valid = True
                self.setIcon(QtGui.QIcon())
            else:
                self._is_valid = False
                error_icon = FileUtils.get_icon("mIndicatorLayerError.svg")
                self.setIcon(error_icon)
                self.setToolTip(tr("Carbon layer is not invalid."))
        else:
            self._is_valid = False
            error_icon = FileUtils.get_icon("mIndicatorLayerError.svg")
            self.setIcon(error_icon)
            self.setToolTip(tr("File path is invalid."))

    def type(self) -> int:
        """Returns the type of the standard item.

        :returns: Type identifier of the carbob item.
        :rtype: int
        """
        return QtGui.QStandardItem.UserType + 5


class CarbonLayerModel(QtGui.QStandardItemModel):
    """View model for carbon layers."""

    def __init__(
        self, parent=None, carbon_paths: typing.Union[typing.List[str], None] = None
    ):
        super().__init__(parent)
        self.setColumnCount(1)

        if carbon_paths is not None:
            for cp in carbon_paths:
                self.add_carbon_layer(cp)

    def add_carbon_layer(self, layer_path: str) -> bool:
        """Adds a carbon layer to the model.

        :param layer_path: Carbon layer path.
        :type layer_path: str

        :returns: True if the carbon layer was successfully added,
        else False if there is an existing item with the same path.
        """
        if self.contains_layer_path(layer_path):
            return False

        carbon_item = CarbonLayerItem(layer_path)
        self.appendRow(carbon_item)

        return True

    def carbon_layer_index(self, layer_path: str) -> QtCore.QModelIndex:
        """Get the model index for the given layer path.

        :param layer_path: Carbon layer path.
        :type layer_path: str

        :returns: The index corresponding to the given layer path else
        an invalid index if not found.
        :rtype: QtCore.QModelIndex
        """
        if not layer_path.startswith("cplus://"):
            norm_path = str(os.path.normpath(layer_path))
        else:
            norm_path = layer_path
        matching_index = None
        for r in range(self.rowCount()):
            index = self.index(r, 0)
            if not index.isValid():
                continue
            item = self.itemFromIndex(index)
            if item.layer_path == norm_path:
                matching_index = index
                break

        if matching_index is None:
            return QtCore.QModelIndex()

        return matching_index

    def contains_layer_path(self, layer_path: str) -> bool:
        """Checks if the specified layer path exists in the model.

        :param layer_path: Carbon layer path.
        :type layer_path: str

        :returns: True if the path exists, else False.
        :rtype: bool
        """
        carbon_idx = self.carbon_layer_index(layer_path)
        if carbon_idx.isValid():
            return True

        return False

    def carbon_paths(self, valid_only: bool = False) -> list:
        """Gets all the carbon paths in the model.

        :param valid_only: Only return the carbon paths that are valid.
        :type valid_only: bool

        :returns: A collection of carbon paths in the model.
        :rtype: list
        """
        carbon_paths = []
        for r in range(self.rowCount()):
            index = self.index(r, 0)
            item = self.itemFromIndex(index)
            if valid_only:
                if item.is_valid:
                    carbon_paths.append(item.layer_path)
            else:
                carbon_paths.append(item.layer_path)

        return carbon_paths

    def update_carbon_path(self, index: QtCore.QModelIndex, layer_path: str) -> bool:
        """Update the carbon path at the given position specified by the index.

        :param index: Location to modify the carbon path.
        :type index: QtCore.QModelIndex

        :param layer_path: Carbon layer path.
        :type layer_path: str

        :returns: True if the path was successfully updated else False
        if there is no carbon item at the given location.
        :rtype: bool
        """
        if not index.isValid():
            return False

        item = self.itemFromIndex(index)
        if item is None:
            return False

        item.update(layer_path)

        return True
