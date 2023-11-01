# -*- coding: utf-8 -*-
"""
Dialog for setting the pixel value for styling IMs.
"""

import os
import typing
import uuid

from qgis.gui import QgsMessageBar

from qgis.PyQt import QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from ..conf import settings_manager
from ..definitions.constants import (
    COLOR_RAMP_PROPERTIES_ATTRIBUTE,
    COLOR_RAMP_TYPE_ATTRIBUTE,
    IM_LAYER_STYLE_ATTRIBUTE,
    IM_SCENARIO_STYLE_ATTRIBUTE,
)
from ..definitions.defaults import ICON_PATH, USER_DOCUMENTATION_SITE
from ..models.base import ImplementationModel
from ..utils import FileUtils, open_documentation, tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/style_pixel_dialog.ui")
)


class PixelValueEditorDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for setting the pixel value for styling IMs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        help_icon = FileUtils.get_icon("mActionHelpContents.svg")
        self.btn_help.setIcon(help_icon)

        self._item_model = QtGui.QStandardItemModel(self)
        self._item_model.setColumnCount(1)
        self.lv_implementation_model.setModel(self._item_model)

        self._load_items()

    def _load_items(self):
        """Load implementation models to the view."""
        for imp_model in settings_manager.get_all_implementation_models():
            im_item = QtGui.QStandardItem(imp_model.name)
            self._item_model.appendRow(im_item)
