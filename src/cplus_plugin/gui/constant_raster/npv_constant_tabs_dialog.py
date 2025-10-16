# -*- coding: utf-8 -*-
from qgis.PyQt import QtWidgets, QtCore
from .constant_pwl_manager_dialog import ConstantPwlManagerDialog


class NpvConstantTabsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NPV & Constant Raster PWL Manager")
        root = QtWidgets.QVBoxLayout(self)
        tabs = QtWidgets.QTabWidget(self)
        root.addWidget(tabs)

        # Tab 1: NPV (your existing dialog embedded)
        try:
            from ..financials.npv_manager_dialog import NpvPwlManagerDialog
            npv_dlg = NpvPwlManagerDialog(self)
            tabs.addTab(npv_dlg, "NPV")
        except Exception:
            placeholder = QtWidgets.QLabel("NPV UI not available.")
            placeholder.setAlignment(QtCore.Qt.AlignCenter)
            tabs.addTab(placeholder, "NPV")

        # Tab 2: Constant PWLs
        const_dlg = ConstantPwlManagerDialog(self)
        tabs.addTab(const_dlg, "Constant PWLs")
