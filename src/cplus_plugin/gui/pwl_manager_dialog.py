# -*- coding: utf-8 -*-
"""
Unified PWL Manager Dialog with tabs for NPV and Constant Rasters.
"""

import os
import typing

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.uic import loadUiType

from .financials.npv_manager_dialog import NpvPwlManagerDialog
from .constant_raster_manager_dialog import ConstantRastersManagerDialog
from ..models.base import NcsPathway
from ..definitions.defaults import ICON_PATH


class PwlManagerDialog(QtWidgets.QDialog):
    """Unified dialog for managing Priority Weighting Layers (PWLs).

    This dialog provides a tabbed interface for managing different types of PWLs:
    - NPV (Net Present Value) PWLs
    - Constant Raster PWLs
    """

    def __init__(self, pathways: typing.List[NcsPathway] = None, parent=None):
        """Initialize the unified PWL manager dialog.

        :param pathways: List of NCS pathways for constant rasters
        :param parent: Parent widget
        """
        super().__init__(parent)

        self.pathways = pathways or []
        self.npv_collection = None
        # Note: constant collections are now managed via constant_raster_registry

        self.setWindowTitle("Manage Priority Weighting Layers")
        self.resize(950, 750)

        # Create main layout
        layout = QtWidgets.QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create NPV tab (embed existing NPV dialog)
        self.npv_dialog = NpvPwlManagerDialog(parent=self)
        self.npv_dialog.setWindowFlags(QtCore.Qt.Widget)  # Embed as widget
        self.tab_widget.addTab(self.npv_dialog, "NPV PWLs")

        # Create Constant Raster tab (embed new constant raster manager)
        self.constant_dialog = ConstantRastersManagerDialog(parent=self)
        self.tab_widget.addTab(self.constant_dialog, "Constant Raster PWLs")

        # Create button box
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _on_accept(self):
        """Handle dialog acceptance."""
        # Get results from NPV tab
        if hasattr(self.npv_dialog, 'npv_collection'):
            self.npv_collection = self.npv_dialog.npv_collection

        # Constant raster tab manages its own collections via the registry
        # No need to get a collection here as they're saved directly

        self.accept()

    def get_npv_collection(self):
        """Get the NPV collection from the NPV tab.

        :returns: NcsPathwayNpvCollection or None
        """
        return self.npv_collection

    def get_constant_collection(self):
        """Get the constant raster collection from the constant raster tab.

        Note: Constant raster collections are now managed via the registry.
        This method is kept for backwards compatibility but returns None.

        :returns: None (collections managed via constant_raster_registry)
        """
        return None

    def set_active_tab(self, tab_name: str):
        """Set the active tab by name.

        :param tab_name: Tab name ('npv' or 'constant')
        """
        if tab_name.lower() == 'npv':
            self.tab_widget.setCurrentIndex(0)
        elif tab_name.lower() == 'constant':
            self.tab_widget.setCurrentIndex(1)
