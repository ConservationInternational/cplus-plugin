# -*- coding: utf-8 -*-
"""
Dialog for setting the pixel value for styling activities.
"""

from collections import OrderedDict
import os

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from qgis.gui import QgsGui

from ..conf import settings_manager
from ..definitions.defaults import ICON_PATH, USER_DOCUMENTATION_SITE
from ..utils import FileUtils, open_documentation

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/style_pixel_dialog.ui")
)


class PixelValueEditorDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for setting the pixel value for styling activities."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        help_icon = FileUtils.get_icon("mActionHelpContents.svg")
        self.btn_help.setIcon(help_icon)
        self.btn_help.clicked.connect(self.open_help)

        self._item_model = QtGui.QStandardItemModel(self)
        self._item_model.setColumnCount(1)
        self.tv_activities.setModel(self._item_model)

        self.tv_activities.setDragEnabled(True)
        self.tv_activities.setAcceptDrops(True)
        self.tv_activities.setShowGrid(False)
        self.tv_activities.setDragDropOverwriteMode(False)
        self.tv_activities.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.tv_activities.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )

        self._load_items()

    def _load_items(self):
        """Load implementation models to the table widget."""
        sorted_models = sorted(
            settings_manager.get_all_activities(),
            key=lambda model: model.style_pixel_value,
        )
        for i, imp_model in enumerate(sorted_models):
            im_item = QtGui.QStandardItem(imp_model.name)
            im_item.setDropEnabled(False)
            im_item.setEditable(False)
            im_item.setData(str(imp_model.uuid), QtCore.Qt.UserRole)
            self._item_model.appendRow(im_item)

    def open_help(self, activated: bool):
        """Opens the user documentation for the plugin in a browser."""
        open_documentation(USER_DOCUMENTATION_SITE)

    @property
    def item_mapping(self) -> OrderedDict:
        """Returns a mapping of the activity position in
        the table and its corresponding unique identifier.

        We are using an OrderedDict to ensure consistency across
        different Python versions in the different platforms that QGIS
        runs on.

        :returns: The mapping of the activities' positions in
        the table and its corresponding unique identifier.
        :rtype: OrderedDict
        """
        activity_position = OrderedDict()

        for i in range(self._item_model.rowCount()):
            item = self._item_model.item(i, 0)
            activity_id = item.data(QtCore.Qt.UserRole)
            activity_position[i + 1] = activity_id

        return activity_position
