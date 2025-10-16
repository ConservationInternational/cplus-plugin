# -*- coding: utf-8 -*-
from __future__ import annotations
from qgis.PyQt import QtCore, QtWidgets

class PwlTabsDialog(QtWidgets.QDialog):
    """
    A simple container that embeds the existing NPV and Constant PWL dialogs
    as tabs. We instantiate your dialogs and coerce them to behave as plain
    widgets so they can live inside a QTabWidget.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Financial & Constant Raster PWL Manager")
        self.setObjectName("PwlTabsDialog")

        root = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget(self)
        root.addWidget(tabs)

        # --- Tab 1: NPV manager (existing dialog) ---
        npv_widget = self._make_embedded_dialog("NPV")
        tabs.addTab(npv_widget, "NPV")

        # --- Tab 2: Constant PWLs manager (new dialog) ---
        const_widget = self._make_embedded_dialog("CONSTANT")
        tabs.addTab(const_widget, "Constant PWLs")

        # Buttons (OK just closes; each child dialog saves on its own Save/OK)
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Close, parent=self
        )
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)  # not shown, but keeps symmetry
        root.addWidget(btns)

    def _make_embedded_dialog(self, which: str) -> QtWidgets.QWidget:
        """
        Instantiate the existing dialogs and embed them as tab content.
        We clear the Dialog window flags so the child behaves like a QWidget.
        """
        if which == "NPV":
            from .financials.npv_manager_dialog import NpvPwlManagerDialog as _Dlg
        else:
            from .constant_raster.constant_pwl_manager_dialog import ConstantPwlManagerDialog as _Dlg

        child = _Dlg(self)
        # Turn the QDialog into a widget-like child (no dialog chrome)
        child.setWindowFlags((child.windowFlags() & ~QtCore.Qt.Dialog) | QtCore.Qt.Widget)

        # Ensure it sizes nicely in the tab
        container = QtWidgets.QWidget(self)
        lay = QtWidgets.QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(child)
        return container
