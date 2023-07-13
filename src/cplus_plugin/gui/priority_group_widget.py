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

    slider_value_changed = QtCore.pyqtSignal(str, int)
    input_value_changed = QtCore.pyqtSignal(str, int)

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

    def set_group(self, group):
        """Sets the priority layer group and updates the slider and
        input values

         Args:
            group (dict): Priority group
        """

        if group is not None:
            self.group = group
            self.group_slider.setValue(int(group["value"]))
            self.group_spin_box.setValue(int(group["value"]))

    def name(self):
        """
        Returns:
            name (dict): Priority group name
        """
        return self.group.get("name")

    def group_value(self):
        """
        Returns:
            name (dict): Priority group value
        """
        return self.group_slider.value()

    def update_slider(self, value):
        """Changes the current slider value.

        Args:
            value (int): Value to be set on the slider
        Note:
            Emits input_value_changed signal
        """
        if self.group is not None:
            self.input_value_changed.emit(self.group["name"], value)
            self.group_slider.blockSignals(True)
            self.group_slider.setValue(value)
            self.group_slider.blockSignals(False)

    def update_spin_box(self, value):
        """Changes the input value of the spin box

        Args:
            value (int): Value to be set on the spin box.
        Note:
            Emits slider_value_changed signal

        """
        if self.group is not None:
            self.slider_value_changed.emit(self.group["name"], value)
            self.group_spin_box.blockSignals(True)
            self.group_spin_box.setValue(value)
            self.group_spin_box.blockSignals(False)
