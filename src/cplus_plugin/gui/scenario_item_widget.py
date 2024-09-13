# -*- coding: utf-8 -*-
"""
    Scenario item widget
"""

from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout


class ScenarioItemWidget(QWidget):
    """Widget to display name and type of a scenario."""

    def __init__(self, name, type, parent=None):
        super(ScenarioItemWidget, self).__init__(parent)

        # Create labels for name and type
        name_label = QLabel(name)
        type_label = QLabel(type)

        # Create a horizontal layout
        layout = QHBoxLayout()
        layout.addWidget(name_label)
        layout.addWidget(type_label)

        # Set the layout for the widget
        self.setLayout(layout)
