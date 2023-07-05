# -*- coding: utf-8 -*-
"""
    Priority group item widget
"""

import os
import typing

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
        self.group_slider.valueChanged.connect(self.update_spin_box)
        self.group_spin_box.valueChanged.connect(self.update_slider)

    def set_group(self, group: typing.Dict):
        """Sets the priority layer group and updates the slider and
        input values
        """
        self.group = group
        if group is not None:
            self.group_slider.setValue(int(group["value"]))
            self.group_spin_box.setValue(int(group["value"]))

    def name(self):
        return self.group.get("name")

    def group_value(self):
        return self.group_slider.value()

    def update_slider(self, value):
        """Changes the current slider value"""
        self.group_slider.blockSignals(True)
        self.group_slider.setValue(value)
        self.group_slider.blockSignals(False)

    def update_spin_box(self, value):
        """Changes the input value of the spin box"""
        self.group_spin_box.blockSignals(True)
        self.group_spin_box.setValue(value)
        self.group_spin_box.blockSignals(False)
