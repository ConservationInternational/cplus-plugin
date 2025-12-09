# -*- coding: utf-8 -*-
"""
Activity NPV configuration widget implementing the ConstantRasterWidgetInterface.
"""

import math
import sys
import typing

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsBasicNumericFormat,
    QgsNumericFormatContext,
)
from qgis.PyQt import QtWidgets, QtCore, QtGui

from .constant_raster_widgets import (
    ConstantRasterWidgetInterface,
    ConstantRasterComponent,
    ConstantRasterMetadata,
)
from ...definitions.constants import (
    DISCOUNTED_VALUE_HEADER,
    TOTAL_PROJECTED_COSTS_HEADER,
    TOTAL_PROJECTED_REVENUES_HEADER,
    YEAR_HEADER,
    MAX_YEARS,
)
from ...definitions.defaults import FINANCIAL_NPV_NAME, NPV_METADATA_ID
from ...lib.financials import compute_discount_value
from ...models.base import LayerModelComponent, ModelComponentType
from ...models.financial import ActivityNpv, ActivityNpvCollection, NpvParameters
from ...models.helpers import (
    activity_npv_collection_to_dict,
    create_activity_npv_collection,
)
from ...utils import FileUtils, tr


DEFAULT_DECIMAL_PLACES = 2


class NpvFinancialModel(QtGui.QStandardItemModel):
    """View model for costs and revenues used in NPV computation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)

        # Headers
        self.setHorizontalHeaderLabels(
            [
                tr(YEAR_HEADER),
                tr(TOTAL_PROJECTED_REVENUES_HEADER),
                tr(TOTAL_PROJECTED_COSTS_HEADER),
                tr(DISCOUNTED_VALUE_HEADER),
            ]
        )

    def add_year_row(self) -> int:
        """Adds a new row for the year.

        The year number is automatically set.

        :returns: The newly added year number (1-based), or -1 if row not added.
        """
        if self.rowCount() >= MAX_YEARS:
            return -1

        year_number = self.rowCount() + 1
        year_item = QtGui.QStandardItem(str(year_number))
        year_item.setEditable(False)
        year_item.setTextAlignment(QtCore.Qt.AlignCenter)
        # style background
        year_item.setData(QtGui.QBrush(QtCore.Qt.lightGray), QtCore.Qt.BackgroundRole)

        revenue_item = QtGui.QStandardItem()
        revenue_item.setEditable(True)
        revenue_item.setTextAlignment(QtCore.Qt.AlignCenter)

        cost_item = QtGui.QStandardItem()
        cost_item.setEditable(True)
        cost_item.setTextAlignment(QtCore.Qt.AlignCenter)

        discount_item = QtGui.QStandardItem()
        discount_item.setEditable(False)
        discount_item.setTextAlignment(QtCore.Qt.AlignCenter)
        discount_item.setData(
            QtGui.QBrush(QtCore.Qt.lightGray), QtCore.Qt.BackgroundRole
        )

        self.appendRow([year_item, revenue_item, cost_item, discount_item])

        return year_number

    def append_years(self, number_years: int):
        """Appends new rows based on the number of years specified."""
        for _ in range(number_years):
            row_number = self.add_year_row()
            if row_number == -1:
                break

    def set_number_of_years(self, number_years: int):
        """Sets the number of years by adding or removing rows to match number_years."""
        if number_years < 0:
            return
        if self.rowCount() < number_years:
            additional_years = number_years - self.rowCount()
            self.append_years(additional_years)
        elif self.rowCount() > number_years:
            remove_years = self.rowCount() - number_years
            self.removeRows(self.rowCount() - remove_years, remove_years)


class DisplayValueFormatterItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Delegate for formatting numeric values using thousand comma separator,
    number of decimal places etc.
    """

    def displayText(self, value: float, locale: QtCore.QLocale) -> str:
        """Format the value to incorporate thousand comma separator.

        :param value: Value of the display role provided by the model.
        :type value: float

        :param locale: Locale for the value in the display role.
        :type locale: QtCore.QLocale

        :returns: Formatted value of the display role data.
        :rtype: str
        """
        if value is None:
            return ""

        formatter = QgsBasicNumericFormat()
        formatter.setShowThousandsSeparator(True)
        formatter.setNumberDecimalPlaces(DEFAULT_DECIMAL_PLACES)

        return formatter.formatDouble(float(value), QgsNumericFormatContext())


class FinancialValueItemDelegate(DisplayValueFormatterItemDelegate):
    """
    Delegate for ensuring only numbers are specified in financial value
    fields.
    """

    def createEditor(
        self,
        parent: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        idx: QtCore.QModelIndex,
    ) -> QtWidgets.QLineEdit:
        """Creates a line edit control whose input value is limited to numbers only.

        :param parent: Parent widget.
        :type parent: QtWidgets.QWidget

        :param option: Options for drawing the widget in the view.
        :type option: QtWidgets.QStyleOptionViewItem

        :param idx: Location of the request in the data model.
        :type idx: QtCore.QModelIndex

        :returns: The editor widget.
        :rtype: QtWidgets.QLineEdit
        """
        line_edit = QtWidgets.QLineEdit(parent)
        line_edit.setFrame(False)
        line_edit.setMaxLength(50)
        validator = QtGui.QDoubleValidator()
        validator.setDecimals(DEFAULT_DECIMAL_PLACES)
        line_edit.setValidator(validator)

        return line_edit

    def setEditorData(self, widget: QtWidgets.QWidget, idx: QtCore.QModelIndex):
        """Sets the data to be displayed and edited by the editor.

        :param widget: Editor widget.
        :type widget: QtWidgets.QWidget

        :param idx: Location in the data model.
        :type idx: QtCore.QModelIndex
        """
        value = idx.model().data(idx, QtCore.Qt.EditRole)
        if value is None:
            widget.setText("")
        else:
            widget.setText(str(value))

    def setModelData(
        self,
        widget: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        idx: QtCore.QModelIndex,
    ):
        """Gets data from the editor widget and stores it in the specified
        model at the item index.

        :param widget: Editor widget.
        :type widget: QtWidgets.QWidget

        :param model: Model to store the editor data in.
        :type model: QtCore.QAbstractItemModel

        :param idx: Location in the data model.
        :type idx: QtCore.QModelIndex
        """
        if not widget.text():
            value = None
        else:
            value = float(widget.text())

        model.setData(idx, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(
        self,
        widget: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        idx: QtCore.QModelIndex,
    ):
        """Updates the geometry of the editor for the item with the given index,
        according to the rectangle specified in the option.

        :param widget: Widget whose geometry will be updated.
        :type widget: QtWidgets.QWidget

        :param option: Option containing the rectangle for
        updating the widget.
        :type option: QtWidgets.QStyleOptionViewItem

        :param idx: Location of the widget in the data model.
        :type idx: QtCore.QModelIndex
        """
        widget.setGeometry(option.rect)


class ActivityNpvWidget(QtWidgets.QWidget, ConstantRasterWidgetInterface):
    """Widget for configuring an Activity's NPV values using NpvFinancialModel."""

    update_requested = QtCore.pyqtSignal(ConstantRasterComponent)

    def __init__(self, parent=None):
        super().__init__(parent)
        ConstantRasterWidgetInterface.__init__(self)

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        form = QtWidgets.QFormLayout()

        # Years & discount
        self.spn_years = QtWidgets.QSpinBox()
        self.spn_years.setRange(0, MAX_YEARS)
        self.spn_years.setValue(0)
        form.addRow(self.tr("Number of Years"), self.spn_years)

        self.sb_discount = QtWidgets.QDoubleSpinBox()
        self.sb_discount.setRange(0.0, 100.0)
        self.sb_discount.setDecimals(DEFAULT_DECIMAL_PLACES)
        self.sb_discount.setSingleStep(1.0)
        self.sb_discount.setToolTip(self.tr("Discount rate (0-100)"))
        form.addRow(self.tr("Discount rate (%)"), self.sb_discount)

        layout.addLayout(form)

        # Main table
        self.tv_revenue_costs = QtWidgets.QTableView()
        self.fin_model = NpvFinancialModel(self)
        self.tv_revenue_costs.setModel(self.fin_model)
        self._revenue_delegate = FinancialValueItemDelegate()
        self._costs_delegate = FinancialValueItemDelegate()
        self._discounted_value_delegate = DisplayValueFormatterItemDelegate()
        self.tv_revenue_costs.setItemDelegateForColumn(1, self._revenue_delegate)
        self.tv_revenue_costs.setItemDelegateForColumn(2, self._costs_delegate)
        self.tv_revenue_costs.setItemDelegateForColumn(
            3, self._discounted_value_delegate
        )
        self.tv_revenue_costs.horizontalHeader().setStretchLastSection(True)
        self.tv_revenue_costs.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectItems
        )
        self.tv_revenue_costs.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
        self.fin_model.itemChanged.connect(self.on_npv_computation_item_changed)
        self.fin_model.rowsRemoved.connect(self.on_years_removed)
        self.tv_revenue_costs.installEventFilter(self)
        layout.addWidget(self.tv_revenue_costs)

        # NPV value layout
        npv_layout = QtWidgets.QHBoxLayout()

        # NPV value label
        self.lbl_npv = QtWidgets.QLabel(self.tr("Net present value per ha"))
        npv_layout.addWidget(self.lbl_npv)

        # NPV spinbox
        self.sb_npv = QtWidgets.QDoubleSpinBox()
        self.sb_npv.setRange(0.0, 1e12)
        self.sb_npv.setDecimals(DEFAULT_DECIMAL_PLACES)
        self.sb_npv.setSingleStep(10.0)
        self.sb_npv.setReadOnly(True)
        npv_layout.addWidget(self.sb_npv)

        # Copy button
        copy_icon = FileUtils.get_icon("mActionEditCopy.svg")
        self.tb_copy_npv = QtWidgets.QToolButton()
        self.tb_copy_npv.setIcon(copy_icon)
        self.tb_copy_npv.setToolTip(self.tr("Copy NPV value"))
        npv_layout.addWidget(self.tb_copy_npv)

        # Auto-compute enable/disable checkbox
        self.cb_manual_npv = QtWidgets.QCheckBox(self.tr("User-defined NPV"))
        self.cb_manual_npv.setChecked(False)
        self.cb_manual_npv.setToolTip(
            self.tr("Uncheck for auto-computed NPV or check for manual input")
        )
        npv_layout.addWidget(self.cb_manual_npv)
        npv_layout.addStretch()

        layout.addLayout(npv_layout)

        # Connect signals
        self.spn_years.valueChanged.connect(self._on_years_changed)
        self.sb_discount.valueChanged.connect(self._recompute_discounted_column)
        self.tb_copy_npv.clicked.connect(self.copy_npv)
        self.cb_manual_npv.toggled.connect(self._on_manual_npv_toggled)
        self.sb_npv.valueChanged.connect(self._on_npv_value_changed)

    def reset(self):
        self._constant_raster_component = None
        self.spn_years.setValue(0)
        self.sb_discount.setValue(0.0)
        self.fin_model.removeRows(0, self.fin_model.rowCount())
        self.cb_manual_npv.setChecked(False)
        self.sb_npv.setValue(0.0)

    def load(self, raster_component: ActivityNpv):
        """Load a ActivityNpv into the widget and populate controls."""
        # Ensure NpvParameters exists and is of the correct type
        if not isinstance(self.raster_component, ActivityNpv):
            raise ValueError("ActivityNpv object expected.")

        params: NpvParameters = self.raster_component.params

        self.spn_years.blockSignals(True)
        years = int(params.years or 0)
        self.spn_years.setValue(years)
        self.spn_years.blockSignals(False)

        self.sb_discount.blockSignals(True)
        self.sb_discount.setValue(float(params.discount or 0.0))
        self.sb_discount.blockSignals(False)

        self.fin_model.set_number_of_years(years)

        rates = params.yearly_rates or []
        for i, year_info in enumerate(rates):
            if len(year_info) < 3:
                continue

            revenue_index = self.fin_model.index(i, 1)
            self.fin_model.setData(revenue_index, year_info[0], QtCore.Qt.EditRole)
            cost_index = self.fin_model.index(i, 2)
            self.fin_model.setData(cost_index, year_info[1], QtCore.Qt.EditRole)

        # Compute discounted column values
        self._recompute_discounted_column()

    @classmethod
    def create_raster_component(
        cls, model_component: LayerModelComponent
    ) -> ActivityNpv:
        """Base method override."""
        params = NpvParameters()
        component = ActivityNpv()
        component.value_info = params
        component.activity = model_component
        component.skip_raster = True
        component.enabled = True

        return component

    @classmethod
    def create_metadata(cls) -> ConstantRasterMetadata:
        """Base method override."""
        collection = ActivityNpvCollection(
            min_value=0.0,
            max_value=0.0,
            component_type=ModelComponentType.ACTIVITY,
            components=[],
            allowable_max=sys.float_info.max,
            allowable_min=0.0,
            skip_raster=True,
            use_manual=False,
        )

        return ConstantRasterMetadata(
            id=NPV_METADATA_ID,
            display_name=FINANCIAL_NPV_NAME,
            raster_collection=collection,
            serializer=activity_npv_collection_to_dict,
            deserializer=create_activity_npv_collection,
            component_type=ModelComponentType.ACTIVITY,
        )

    def eventFilter(self, observed_object: QtCore.QObject, event: QtCore.QEvent):
        """Captures events sent to specific widgets.

        :param observed_object: Object receiving the event.
        :type observed_object: QtCore.QObject

        :param event: The specific event being received by the observed object.
        :type event: QtCore.QEvent
        """
        # Resize table columns based on the size of the table view.
        if observed_object == self.tv_revenue_costs:
            if event.type() == QtCore.QEvent.Resize:
                self.resize_column_widths()

        return super().eventFilter(observed_object, event)

    def resize_column_widths(self):
        """Resize column widths of the NPV revenue and cost table based
        on its current width.
        """
        table_width = self.tv_revenue_costs.width()
        self.tv_revenue_costs.setColumnWidth(0, int(table_width * 0.09))
        self.tv_revenue_costs.setColumnWidth(1, int(table_width * 0.33))
        self.tv_revenue_costs.setColumnWidth(2, int(table_width * 0.33))
        self.tv_revenue_costs.setColumnWidth(3, int(table_width * 0.24))

    def copy_npv(self):
        """Copy NPV to the clipboard."""
        QgsApplication.instance().clipboard().setText(str(self.sb_npv.value()))

    def _on_years_changed(self, new_years: int):
        """Adjust the number of rows in the model to match years."""
        if new_years < 0:
            return
        self.fin_model.set_number_of_years(new_years)
        # Recompute discounted values for any new rows
        self._recompute_discounted_column()

    def _on_manual_npv_toggled(self, checked: bool):
        """Slot raised to enable/disable manual NPV value.

        :param checked: True if the manual NPV is enabled else False.
        :type checked: bool
        """
        if checked:
            self.sb_npv.setReadOnly(False)
            self.sb_npv.setFocus()
            self.enable_npv_parameters_widgets(False)
        else:
            self.sb_npv.setReadOnly(True)
            self.enable_npv_parameters_widgets(True)

        # Notify changes
        self._request_update()

    def enable_npv_parameters_widgets(self, enable: bool):
        """Enable or disable the UI widgets for specifying NPV parameters.

        :param enable: True to enable the widgets, else False to disable.
        :type enable: bool
        """
        self.spn_years.setEnabled(enable)
        self.sb_discount.setEnabled(enable)
        self.tv_revenue_costs.setEnabled(enable)

    def _on_npv_value_changed(self, npv: float):
        """Slot raised when NPV value has changed.

        Send alert for the updated activity NPV object to be sent.

        :param npv: NPV value to be saved.
        :type npv: float
        """
        self._request_update()

    def _recompute_discounted_column(self):
        """Updates all discounted values that had already been
        computed using the revised discount rate.
        """
        for row in range(self.fin_model.rowCount()):
            discount_value = self.fin_model.data(
                self.fin_model.index(row, 3), QtCore.Qt.EditRole
            )
            if discount_value is None:
                continue
            self.update_discounted_value(row)

    def update_discounted_value(self, row: int):
        """Updated the discounted value for the given row number.

        :param row: Row number to compute the discounted value.
        :type row: int
        """
        # For computation purposes, any None value will be
        # translated to zero.
        revenue = self.fin_model.data(self.fin_model.index(row, 1), QtCore.Qt.EditRole)

        cost = self.fin_model.data(self.fin_model.index(row, 2), QtCore.Qt.EditRole)

        # No need to compute if both revenue and cost have not been defined
        if revenue is None and cost is None:
            return

        if revenue is None:
            revenue = 0.0

        if cost is None:
            cost = 0.0

        discounted_value = compute_discount_value(
            revenue, cost, row + 1, self.sb_discount.value()
        )
        rounded_discounted_value = round(discounted_value, DEFAULT_DECIMAL_PLACES)
        discounted_value_index = self.fin_model.index(row, 3)
        self.fin_model.setData(
            discounted_value_index, rounded_discounted_value, QtCore.Qt.EditRole
        )

        if not self.cb_manual_npv.isChecked():
            self.compute_npv()

    def compute_npv(self):
        """Computes the NPV based on the total of the discounted value and
        sets it in the corresponding control.
        """
        npv = 0.0
        for row in range(self.fin_model.rowCount()):
            discount_value = self.fin_model.data(
                self.fin_model.index(row, 3), QtCore.Qt.EditRole
            )
            if discount_value is None:
                continue
            npv += discount_value

        self.sb_npv.setValue(npv)

    def on_years_removed(self, index: QtCore.QModelIndex, start: int, end: int):
        """Slot raised when the year rows have been removed.

        :param index: Reference item at the given location.
        :type index: QtCore.QModelIndex

        :param start: Start location of the items that have been removed.
        :type start: int

        :param end: End location of the items that have been removed.
        :type end: int
        """
        # Recalculate the NPV
        self.compute_npv()

    def on_npv_computation_item_changed(self, item: QtGui.QStandardItem):
        """Slot raised when the data of an item has changed.

        This is used to compute discounted value as well as the NPV.

        :param item: Item whose value has changed.
        :type item: QtGui.QStandardItem
        """
        # Update discounted value only if revenue or cost
        # have changed.
        column = item.column()
        if column == 1 or column == 2:
            self.update_discounted_value(item.row())

    def update_activity_npv(self):
        """Update changes made in the UI to the underlying activity NPV object."""
        if self._constant_raster_component is None:
            return

        self._constant_raster_component.params.manual_npv = (
            self.cb_manual_npv.isChecked()
        )

        if not self._constant_raster_component.params.manual_npv:
            self._constant_raster_component.params.years = self.spn_years.value()
            self._constant_raster_component.params.discount = self.sb_discount.value()

            yearly_rates = []
            for row in range(self.fin_model.rowCount()):
                revenue_value = self.fin_model.data(
                    self.fin_model.index(row, 1), QtCore.Qt.EditRole
                )
                cost_value = self.fin_model.data(
                    self.fin_model.index(row, 2), QtCore.Qt.EditRole
                )
                discount_value = self.fin_model.data(
                    self.fin_model.index(row, 3), QtCore.Qt.EditRole
                )
                yearly_rates.append((revenue_value, cost_value, discount_value))

            self._constant_raster_component.params.yearly_rates = yearly_rates

        self._constant_raster_component.params.absolute = self.sb_npv.value()

    def _request_update(self):
        """Send a notification to the parent widget to save the latest changes."""
        self.update_activity_npv()
        self.notify_update()
