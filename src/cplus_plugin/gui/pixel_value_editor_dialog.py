# -*- coding: utf-8 -*-
"""
Dialog for setting the pixel value for styling IMs.
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


class PixelValueItemModel(QtGui.QStandardItemModel):
    """Custom model that prevent dropping items in the first row since
    it is fixed for the constant value raster.
    """

    def dropMimeData(
        self,
        data: QtCore.QMimeData,
        action: QtCore.Qt.DropAction,
        row: int,
        column: int,
        parent: QtCore.QModelIndex,
    ) -> bool:
        """Implements behaviour for handling data supplied by drag
        and drop operation.

        :param data: Object containing data from the drag operation.
        :type data: QtCore.QMimeData

        :param action: Type of the drag and drop operation.
        :type action: QtCore.Qt.DropAction

        :param row: Row location of dropped data.
        :type row: int

        :param column: Column location of dropped data.
        :type column: int

        :param parent: Index location for target item where the
        operation ended.
        :type parent: QtCore.QModelIndex

        :returns: True if the data and action can be handled by the
        model, else False.
        :rtype: bool
        """
        if row == 0:
            return False

        return super().dropMimeData(data, action, row, column, parent)


class PixelValueEditorDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for setting the pixel value for styling IMs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        help_icon = FileUtils.get_icon("mActionHelpContents.svg")
        self.btn_help.setIcon(help_icon)
        self.btn_help.clicked.connect(self.open_help)

        self._item_model = PixelValueItemModel(self)
        self._item_model.setColumnCount(1)
        self.tv_implementation_model.setModel(self._item_model)

        self.tv_implementation_model.setDragEnabled(True)
        self.tv_implementation_model.setAcceptDrops(True)
        self.tv_implementation_model.setShowGrid(False)
        self.tv_implementation_model.setDragDropOverwriteMode(False)
        self.tv_implementation_model.setDragDropMode(
            QtWidgets.QAbstractItemView.InternalMove
        )
        self.tv_implementation_model.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )

        self._load_items()

    def _load_items(self):
        """Load implementation models to the table widget."""
        # Add default fixed pixel-value layer.
        fixed_value_item = QtGui.QStandardItem(
            self.tr("Constant-value analysis layer (fixed)")
        )
        fixed_value_item.setEnabled(False)
        fixed_value_item.setEditable(False)
        fixed_value_item.setDragEnabled(False)
        fixed_value_item.setDropEnabled(False)
        self._item_model.appendRow(fixed_value_item)

        sorted_models = sorted(
            settings_manager.get_all_implementation_models(),
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
        """Returns a mapping of the implementation model position in
        the table and its corresponding unique identifier.

        We are using an OrderedDict to ensure consistency across
        different Python versions in the different platforms that QGIS
        runs on.

        :returns: The mapping of the implementation model position in
        the table and its corresponding unique identifier.
        :rtype: OrderedDict
        """
        im_position = OrderedDict()

        for i in range(1, self._item_model.rowCount()):
            item = self._item_model.item(i, 0)
            im_id = item.data(QtCore.Qt.UserRole)
            im_position[i + 1] = im_id

        return im_position
