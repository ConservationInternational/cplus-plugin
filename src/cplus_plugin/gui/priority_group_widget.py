# -*- coding: utf-8 -*-
"""
    Priority group item widget
"""

import os

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from qgis.PyQt.uic import loadUiType


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/priority_group.ui")
)


class PriorityGroupWidget(QtWidgets.QWidget, WidgetUi):
    """Widget that provide UI for priority group details."""

    slider_value_changed = QtCore.pyqtSignal()
    input_value_changed = QtCore.pyqtSignal()

    def __init__(
        self,
        group,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.group = group

        self.initialize_ui()

    def initialize_ui(self):
        """Populate UI inputs when loading the widget"""

        self.group_la.setText(self.group["name"])
