# -*- coding: utf-8 -*-
"""
Activity NPV configuration widget implementing the ConstantRasterWidgetInterface.
"""

import math
import sys

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsBasicNumericFormat,
    QgsNumericFormatContext,
)
from qgis.PyQt import QtWidgets, QtCore, QtGui

from .constant_raster_widgets import (
    ConstantRasterWidgetInterface,
    ConstantRasterCollection,
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
from ...models.base import LayerModelComponent, ModelComponentType
from ...models.financial import ActivityNpv, NpvParameters
from ...utils import FileUtils, tr


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


class ActivityNpvWidget(QtWidgets.QWidget, ConstantRasterWidgetInterface):
    """Widget for configuring an Activity's NPV values using NpvFinancialModel."""

    update_requested = QtCore.pyqtSignal(object)

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
        self.sb_discount.setDecimals(2)
        self.sb_discount.setSingleStep(1.0)
        self.sb_discount.setToolTip(self.tr("Discount rate (0-100)"))
        form.addRow(self.tr("Discount rate (%)"), self.sb_discount)

        layout.addLayout(form)

        # Main table
        self.tv_revenue_costs = QtWidgets.QTableView()
        self.fin_model = NpvFinancialModel(self)
        self.tv_revenue_costs.setModel(self.fin_model)
        self.tv_revenue_costs.horizontalHeader().setStretchLastSection(True)
        self.tv_revenue_costs.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectItems
        )
        self.tv_revenue_costs.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection
        )
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
        self.sb_npv.setDecimals(2)
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

    def reset(self):
        self._constant_raster_component = None
        self.spn_years.setValue(0)
        self.sb_discount.setValue(0.0)
        self.fin_model.removeRows(0, self.fin_model.rowCount())

    def load(self, raster_component: ConstantRasterComponent):
        """Load a component (ideally ActivityNpv) into the widget and populate controls."""
        # Set internal reference
        self.raster_component = raster_component

        # Ensure NpvParameters exists
        if not isinstance(self.raster_component.value_info, NpvParameters):
            self.raster_component.value_info = NpvParameters()

        params: NpvParameters = self.raster_component.value_info

        self.spn_years.blockSignals(True)
        years = int(params.years or 0)
        self.spn_years.setValue(years)
        self.spn_years.blockSignals(False)

        self.sb_discount.blockSignals(True)
        self.sb_discount.setValue(float(params.discount or 0.0))
        self.sb_discount.blockSignals(False)

        self.fin_model.set_number_of_years(years)

        rates = params.yearly_rates or []
        for row in range(self.fin_model.rowCount()):
            # Revenue item
            revenue_item = self.fin_model.item(row, 1)
            cost_item = self.fin_model.item(row, 2)
            discount_item = self.fin_model.item(row, 3)

            revenue_item.setText("")
            cost_item.setText("")
            discount_item.setText("")
            discount_item.setData(
                None, QtCore.Qt.UserRole
            )  # store per-row discount rate here

            if row < len(rates):
                rev, cost, per_row_disc = (
                    rates[row] if rates[row] is not None else (None, None, None)
                )
                if rev is not None:
                    revenue_item.setText(str(rev))
                if cost is not None:
                    cost_item.setText(str(cost))
                if per_row_disc is not None:
                    discount_item.setData(float(per_row_disc), QtCore.Qt.UserRole)
                else:
                    discount_item.setData(None, QtCore.Qt.UserRole)

        # Compute discounted column values based on either per-row discount or global discount
        self._recompute_discounted_column()

        # Update normalized preview
        self._update_normalized_preview()

    @classmethod
    def create_raster_component(
        cls, model_component: LayerModelComponent
    ) -> ActivityNpv:
        """Base method override."""
        params = NpvParameters()
        component = ActivityNpv()
        component.value_info = params
        component.activity = model_component
        component.skip_raster = False
        component.enabled = True

        return component

    @classmethod
    def create_metadata(cls) -> ConstantRasterMetadata:
        """Base method override."""
        collection = ConstantRasterCollection(
            min_value=0.0,
            max_value=0.0,
            component_type=ModelComponentType.ACTIVITY,
            components=[],
            allowable_max=sys.float_info.max,
            allowable_min=0.0,
        )

        return ConstantRasterMetadata(
            id=NPV_METADATA_ID,
            display_name=FINANCIAL_NPV_NAME,
            raster_collection=collection,
            serializer=None,
            deserializer=None,
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

    def _recompute_discounted_column(self):
        """Recompute discounted value column using per-row discount
        if provided, else global discount.
        """
        global_discount = float(self.sb_discount.value() or 0.0)
        for row in range(self.fin_model.rowCount()):
            rev_item = self.fin_model.item(row, 1)
            cost_item = self.fin_model.item(row, 2)
            discount_item = self.fin_model.item(row, 3)

            # Get numeric values
            try:
                rev = (
                    float(rev_item.text())
                    if rev_item and rev_item.text().strip() != ""
                    else 0.0
                )
            except Exception:
                rev = 0.0
            try:
                cost = (
                    float(cost_item.text())
                    if cost_item and cost_item.text().strip() != ""
                    else 0.0
                )
            except Exception:
                cost = 0.0

            # Year index (1-based)
            year_index = row + 1

            # Per-row discount rate saved in UserRole if available
            per_row_discount = discount_item.data(QtCore.Qt.UserRole)
            used_discount = (
                float(per_row_discount)
                if per_row_discount is not None
                else global_discount
            )

            # Avoid negative or crazy discount rates; clamp to [0, 10]
            if used_discount is None:
                used_discount = 0.0
            try:
                used_discount = max(0.0, min(10.0, float(used_discount)))
            except Exception:
                used_discount = 0.0

            # Compute discounted net = (rev - cost) / (1 + r)^t
            try:
                denom = math.pow(1.0 + used_discount, year_index)
                discounted = (rev - cost) / denom if denom != 0 else (rev - cost)
            except Exception:
                discounted = 0.0

            discount_item.setText(f"{discounted:.2f}")

        # Keep normalized preview in sync after recompute
        self._update_normalized_preview()

    def _update_normalized_preview(self):
        """Update normalized label based on the current collection if available."""
        if self.raster_component is None or not self.raster_component.value_info:
            return

        absolute = float(
            getattr(self.raster_component.value_info, "absolute", 0.0) or 0.0
        )

        collection = getattr(self.raster_component, "_parent_collection", None)
        if collection is None:
            return

        minv = float(collection.min_value)
        maxv = float(collection.max_value)
        if maxv == minv:
            normalized = 1.0
        else:
            normalized = (absolute - minv) / float(maxv - minv)
            normalized = max(0.0, min(1.0, normalized))
