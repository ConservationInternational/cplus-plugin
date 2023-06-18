# -*- coding: utf-8 -*-
"""
Composite list view-based widgets for displaying implementation model
and NCS pathway items.
"""

import os

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets
)

from qgis.PyQt.uic import loadUiType

from qgis.core import QgsApplication


WidgetUi, _ = loadUiType(
    os.path.join(
        os.path.dirname(__file__),
        "../ui/model_component_widget.ui"
    )
)


class ModelComponentWidget(QtWidgets.QWidget, WidgetUi):
    """Widget for displaying and managing model items in a list view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        add_icon = QgsApplication.instance().getThemeIcon("symbologyAdd.svg")
        self.btn_add.setIcon(add_icon)

        remove_icon = QgsApplication.instance().getThemeIcon(
            "symbologyRemove.svg"
        )
        self.btn_remove.setIcon(remove_icon)

        edit_icon = QgsApplication.instance().getThemeIcon(
            "mActionToggleEditing.svg"
        )
        self.btn_edit.setIcon(edit_icon)

    @property
    def title(self) -> str:
        """Returns the title of the view.

        :returns: Title of the view.
        :rtype: str
        """
        return self.lbl_title.text()

    @title.setter
    def title(self, text: str):
        """Sets the text tobe displayed in the title label of the view.

        :param text: Title of the view.
        :type text: str
        """
        self.lbl_title.setText(text)