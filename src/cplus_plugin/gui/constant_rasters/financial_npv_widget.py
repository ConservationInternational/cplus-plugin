# -*- coding: utf-8 -*-
"""
Activity NPV configuration widget implementing the ConstantRasterWidgetInterface.
"""

from __future__ import annotations

import math
from qgis.PyQt import QtWidgets, QtCore, QtGui
import typing

from .constant_raster_widgets import (
    ConstantRasterWidgetInterface,
    ConstantRasterComponent,
    ConstantRasterMetadata,
    InputRange,
)
from ...definitions.constants import (
    DISCOUNTED_VALUE_HEADER,
    TOTAL_PROJECTED_COSTS_HEADER,
    TOTAL_PROJECTED_REVENUES_HEADER,
    YEAR_HEADER,
    MAX_YEARS,
)
from ...models.base import LayerModelComponent, ModelComponentType
from ...models.financial import ActivityNpv, NpvParameters
from ...utils import tr


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
        self._connect_signals()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Header
        self.lbl_title = QtWidgets.QLabel(self.tr("Activity NPV"))
        f = self.lbl_title.font()
        f.setBold(True)
        self.lbl_title.setFont(f)
        layout.addWidget(self.lbl_title)

        form = QtWidgets.QFormLayout()
        self.lbl_activity_name = QtWidgets.QLabel(self.tr("<No activity selected>"))
        form.addRow(self.tr("Activity:"), self.lbl_activity_name)

        # Absolute NPV value
        self.sb_absolute = QtWidgets.QDoubleSpinBox()
        self.sb_absolute.setRange(-1e12, 1e12)
        self.sb_absolute.setDecimals(2)
        self.sb_absolute.setSingleStep(100.0)
        self.sb_absolute.setToolTip(
            self.tr("Absolute Net Present Value for the activity")
        )
        form.addRow(self.tr("Absolute NPV:"), self.sb_absolute)

        # Normalized preview (read-only)
        self.lbl_normalized = QtWidgets.QLabel("-")
        form.addRow(self.tr("Normalized (preview):"), self.lbl_normalized)

        # Years & global discount
        self.spn_years = QtWidgets.QSpinBox()
        self.spn_years.setRange(0, MAX_YEARS)
        self.spn_years.setValue(0)
        form.addRow(self.tr("Years:"), self.spn_years)

        self.sb_discount = QtWidgets.QDoubleSpinBox()
        self.sb_discount.setRange(0.0, 1.0)
        self.sb_discount.setDecimals(4)
        self.sb_discount.setSingleStep(0.01)
        self.sb_discount.setToolTip(self.tr("Default discount rate (0-1)"))
        form.addRow(self.tr("Discount rate:"), self.sb_discount)

        layout.addLayout(form)

        # Main table
        self.table_view = QtWidgets.QTableView()
        self.fin_model = NpvFinancialModel(self)
        self.table_view.setModel(self.fin_model)
        # Some appearance tweaks
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        layout.addWidget(QtWidgets.QLabel(self.tr("Yearly rates (revenue / cost)")))
        layout.addWidget(self.table_view, 1)

        # Skip raster checkbox
        self.chk_skip_raster = QtWidgets.QCheckBox(
            self.tr("Skip raster creation for this activity")
        )
        layout.addWidget(self.chk_skip_raster)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.btn_reset = QtWidgets.QPushButton(self.tr("Reset"))
        self.btn_apply = QtWidgets.QPushButton(self.tr("Apply"))
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

    def _connect_signals(self):
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        self.btn_reset.clicked.connect(self._on_reset_clicked)
        self.spn_years.valueChanged.connect(self._on_years_changed)
        # Recompute discounted column when the global discount changes
        self.sb_discount.valueChanged.connect(self._recompute_discounted_column)
        # Recompute preview when absolute value changes
        self.sb_absolute.valueChanged.connect(self._update_normalized_preview)

    # Interface methods

    def reset(self):
        self._constant_raster_component = None
        self.lbl_activity_name.setText(self.tr("<No activity selected>"))
        self.sb_absolute.setValue(0.0)
        self.lbl_normalized.setText("-")
        self.spn_years.setValue(0)
        self.sb_discount.setValue(0.0)
        self.fin_model.removeRows(0, self.fin_model.rowCount())
        self.chk_skip_raster.setChecked(False)

    def load(self, raster_component: ConstantRasterComponent):
        """Load a component (ideally ActivityNpv) into the widget and populate controls."""
        # Set internal reference
        self.raster_component = raster_component

        # Ensure NpvParameters exists
        if not isinstance(self.raster_component.value_info, NpvParameters):
            self.raster_component.value_info = NpvParameters()

        params: NpvParameters = self.raster_component.value_info

        # Update header/activity name
        activity_name = (
            getattr(self.raster_component.component, "name", "")
            or self.raster_component.component_id
        )
        self.lbl_activity_name.setText(activity_name)

        # Absolute
        self.sb_absolute.blockSignals(True)
        self.sb_absolute.setValue(float(params.absolute or 0.0))
        self.sb_absolute.blockSignals(False)

        # Years & discount
        self.spn_years.blockSignals(True)
        years = int(params.years or 0)
        self.spn_years.setValue(years)
        self.spn_years.blockSignals(False)

        self.sb_discount.blockSignals(True)
        self.sb_discount.setValue(float(params.discount or 0.0))
        self.sb_discount.blockSignals(False)

        # Skip raster
        self.chk_skip_raster.blockSignals(True)
        self.chk_skip_raster.setChecked(bool(self.raster_component.skip_raster))
        self.chk_skip_raster.blockSignals(False)

        # Populate the financial model table
        self.fin_model.set_number_of_years(years)

        rates = params.yearly_rates or []
        # Fill rows
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
                # Preserve per-row discount rate in UserRole for later computation/persistence
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
        component.component = model_component
        component.prefix = ""
        component.suffix = "NPV"
        component.skip_raster = False
        component.enabled = True

        return component

    @classmethod
    def create_metadata(
        cls, metadata_id: str, component_type: "ModelComponentType"
    ) -> ConstantRasterMetadata:
        """Base method override."""
        display_name = tr("Net Present Value")

        return ConstantRasterMetadata(
            id=metadata_id,
            display_name=display_name,
            raster_collection=None,
            serializer=None,
            deserializer=None,
            component_type=component_type,
            input_range=InputRange(min=0.0, max=1e9),
        )

    def _on_apply_clicked(self):
        """Apply changes from the UI into the raster_component and emit update_requested."""
        if self.raster_component is None:
            return

        if not isinstance(self.raster_component.value_info, NpvParameters):
            self.raster_component.value_info = NpvParameters()

        params: NpvParameters = self.raster_component.value_info

        params.absolute = float(self.sb_absolute.value())
        params.years = int(self.spn_years.value())
        params.discount = float(self.sb_discount.value())

        # Read model rows into params.yearly_rates
        rates: typing.List[tuple] = []
        for row in range(self.fin_model.rowCount()):
            rev_item = self.fin_model.item(row, 1)
            cost_item = self.fin_model.item(row, 2)
            discount_item = self.fin_model.item(row, 3)

            def parse_number(item: QtGui.QStandardItem):
                if item is None:
                    return None
                txt = item.text().strip()
                if txt == "":
                    return None
                try:
                    return float(txt)
                except Exception:
                    return None

            rev = parse_number(rev_item)
            cost = parse_number(cost_item)
            per_row_disc = discount_item.data(QtCore.Qt.UserRole)
            # Keep per-row discount if present; otherwise None (global discount used)
            rates.append(
                (rev, cost, float(per_row_disc) if per_row_disc is not None else None)
            )

        params.yearly_rates = rates

        # Update skip_raster flag
        self.raster_component.skip_raster = bool(self.chk_skip_raster.isChecked())

        # Notify manager that an update is requested
        self.notify_update()

    def _on_reset_clicked(self):
        if self.raster_component is None:
            self.reset()
        else:
            self.load(self.raster_component)

    def _on_years_changed(self, new_years: int):
        """Adjust the number of rows in the model to match years."""
        if new_years < 0:
            return
        self.fin_model.set_number_of_years(new_years)
        # Recompute discounted values for any new rows
        self._recompute_discounted_column()

    def _recompute_discounted_column(self):
        """Recompute discounted value column using per-row discount if provided, else global discount."""
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
            self.lbl_normalized.setText("-")
            return

        absolute = float(
            getattr(self.raster_component.value_info, "absolute", 0.0) or 0.0
        )

        collection = getattr(self.raster_component, "_parent_collection", None)
        if collection is None:
            self.lbl_normalized.setText(self.tr("N/A"))
            return

        try:
            minv = float(collection.min_value)
            maxv = float(collection.max_value)
            if maxv == minv:
                normalized = 1.0
            else:
                normalized = (absolute - minv) / float(maxv - minv)
                normalized = max(0.0, min(1.0, normalized))
            self.lbl_normalized.setText(f"{normalized:.3f}")
        except Exception:
            self.lbl_normalized.setText(self.tr("N/A"))
