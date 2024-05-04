# -*- coding: utf-8 -*-
"""
Dialog for creating a new financial PWL.
"""

import os
import typing
import uuid

from qgis.core import (
    Qgis,
    QgsColorRamp,
    QgsFillSymbol,
    QgsFillSymbolLayer,
    QgsMapLayerProxyModel,
    QgsRasterLayer,
)
from qgis.gui import QgsGui, QgsMessageBar

from qgis.PyQt import QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from ..definitions.constants import (
    COLOR_RAMP_PROPERTIES_ATTRIBUTE,
    COLOR_RAMP_TYPE_ATTRIBUTE,
    ACTIVITY_LAYER_STYLE_ATTRIBUTE,
    ACTIVITY_SCENARIO_STYLE_ATTRIBUTE,
)
from ..definitions.defaults import ICON_PATH, USER_DOCUMENTATION_SITE
from .financial_npv_model import FinancialNpvModel
from ..models.base import Activity
from ..utils import FileUtils, open_documentation, tr

WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/financial_pwl_dialog.ui")
)


class FinancialPwlDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for creating a new financial PWL."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        # Initialize UI
        help_icon = FileUtils.get_icon("mActionHelpContents_green.svg")
        self.btn_help.setIcon(help_icon)

        # copy_icon = FileUtils.get_icon("mActionHelpContents_green.svg")
        # self.btn_help.setIcon(help_icon)

        ok_button = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        ok_button.setText(tr("Create"))

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)
        self.btn_help.clicked.connect(self.open_help)

        # Set view model
        self._npv_model = FinancialNpvModel()
        self.tv_revenue_costs.setModel(self._npv_model)

        self.sb_num_years.valueChanged.connect(self.on_number_years_changed)

        # Set default values
        self.sb_num_years.setValue(5)

    def open_help(self, activated: bool):
        """Opens the user documentation for the plugin in a browser."""
        open_documentation(USER_DOCUMENTATION_SITE)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        """Use this event to trigger the resizing of the table columns.

        :param event: Contains the geometry information of the dialog.
        :type event: QtGui.QResizeEvent
        """
        table_width = self.tv_revenue_costs.width()
        self.tv_revenue_costs.setColumnWidth(0, table_width * 0.1)
        self.tv_revenue_costs.setColumnWidth(1, table_width * 0.35)
        self.tv_revenue_costs.setColumnWidth(2, table_width * 0.35)
        self.tv_revenue_costs.setColumnWidth(3, table_width * 0.2)

    def on_number_years_changed(self, years: int):
        """Slot raised when the number of years change.

        :param years: The number of years.
        :type years: int
        """
        self._npv_model.set_number_of_years(years)
