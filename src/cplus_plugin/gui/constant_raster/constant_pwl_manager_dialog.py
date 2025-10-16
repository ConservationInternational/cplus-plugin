# -*- coding: utf-8 -*-
"""
Dialog for creating/updating Constant Raster PWLs.
"""
from __future__ import annotations

import os
from typing import Optional

from qgis.core import Qgis
from qgis.gui import QgsGui, QgsMessageBar
from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.uic import loadUiType

from ..component_item_model import NcsPathwayItemModel
from ...conf import settings_manager
from ...definitions.defaults import ICON_PATH, USER_DOCUMENTATION_SITE
from ...models.base import NcsPathway
from ...models.constant_pwl import (
    ConstantPwlItem,
    ConstantPwlCollection,
    InputMode,
    ScaleMode,
    Inversion,
    make_default_collection_for_pathways,
)
from ...utils import FileUtils, open_documentation, tr

HeaderUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/financial_pwl_dialog.ui")
)


class ConstantPwlManagerDialog(QtWidgets.QDialog):
    """Dialog for managing Constant Raster PWLs for NCS pathways."""

    NUM_DECIMAL_PLACES = 6
    MIN_VAL = -1e12
    MAX_VAL = 1e12

    def __init__(self, parent=None):
        super().__init__(parent)
        QgsGui.enableAutoGeometryRestore(self)
        self.setWindowTitle(tr("Constant Raster PWL Manager"))

        # ---------- state ----------
        self._message_bar = QgsMessageBar()
        self._collection: ConstantPwlCollection = None
        self._current_pathway_identifier: Optional[str] = None

        # ---------- top icon + help ----------
        fr_info = QtWidgets.QFrame(self)
        fr_info.setObjectName("fr_info")
        fr_info.setFrameShape(QtWidgets.QFrame.StyledPanel)

        # icon
        icon_la = QtWidgets.QLabel(fr_info)
        icon_la.setObjectName("icon_la")
        pix = QtGui.QPixmap(ICON_PATH)
        if not pix.isNull():
            # 24–28px
            pix = pix.scaled(QtCore.QSize(24, 24), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        icon_la.setPixmap(pix)
        icon_la.setFixedSize(24, 24)

        # text
        la_info = QtWidgets.QLabel(
            self.tr("Define the parameters for Constant Raster PWLs and how they will be normalized. "
                    "Click Help for more information."),
            fr_info
        )
        la_info.setObjectName("la_info")
        la_info.setWordWrap(True)

        # layout inside the banner
        fr_info_lay = QtWidgets.QHBoxLayout(fr_info)
        fr_info_lay.setContentsMargins(12, 10, 12, 10)
        fr_info_lay.setSpacing(12)
        fr_info_lay.addWidget(icon_la, 0, QtCore.Qt.AlignTop)
        fr_info_lay.addWidget(la_info, 1)

        # style
        fr_info.setStyleSheet("""
            QFrame#fr_info {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 6px;
            }
            QFrame#fr_info QLabel { color: palette(text); }
        """)

        # Help button on the right
        self._btn_help = QtWidgets.QToolButton()
        self._btn_help.setIcon(FileUtils.get_icon("mActionHelpContents_green.svg"))
        self._btn_help.setAutoRaise(True)
        self._btn_help.setToolTip(self.tr("Open documentation"))
        self._btn_help.clicked.connect(lambda *_: open_documentation(USER_DOCUMENTATION_SITE))

        # header row (banner + help)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 6, 0, 6)
        header_layout.addWidget(fr_info, 1)
        header_layout.addWidget(self._btn_help, 0, QtCore.Qt.AlignTop)

        # ---------- left: pathways list ----------
        self._ncs_pathway_model = NcsPathwayItemModel()
        self.lst_pathways = QtWidgets.QListView()
        self.lst_pathways.setModel(self._ncs_pathway_model)
        self.lst_pathways.selectionModel().selectionChanged.connect(self._on_pathway_selection_changed)

        # ---------- right: pathway editor ----------
        self.gp_const_pwl = QtWidgets.QGroupBox(tr("Constant Raster PWL for Selected Pathway"))
        self.gp_const_pwl.setCheckable(True)
        self.gp_const_pwl.toggled.connect(self._on_groupbox_toggled)

        # mode
        self.rb_mode_raster = QtWidgets.QRadioButton(tr("Use Raster"))
        self.rb_mode_const = QtWidgets.QRadioButton(tr("Use Constant Value"))
        self.rb_mode_const.setChecked(True)
        mode_h = QtWidgets.QHBoxLayout()
        mode_h.addWidget(self.rb_mode_raster)
        mode_h.addWidget(self.rb_mode_const)
        mode_h.addStretch(1)

        # raster path picker
        self._le_path = QtWidgets.QLineEdit()
        self._tb_browse = QtWidgets.QToolButton()
        self._tb_browse.setText("…")
        self._tb_browse.clicked.connect(self._browse_raster)
        path_h = QtWidgets.QHBoxLayout()
        path_h.addWidget(self._le_path)
        path_h.addWidget(self._tb_browse)

        # constant spin
        self._sb_const = QtWidgets.QDoubleSpinBox()
        self._sb_const.setDecimals(self.NUM_DECIMAL_PLACES)
        self._sb_const.setRange(self.MIN_VAL, self.MAX_VAL)

        # normalized path (read-only)
        self._le_norm = QtWidgets.QLineEdit()
        self._le_norm.setReadOnly(True)

        form = QtWidgets.QFormLayout()
        form.addRow(tr("Input Mode:"), self._mk_container(mode_h))
        form.addRow(tr("Raster Path:"), self._mk_container(path_h))
        form.addRow(tr("Constant Value:"), self._sb_const)
        form.addRow(tr("Normalized Path:"), self._le_norm)
        self.gp_const_pwl.setLayout(form)

        # enable/disable by mode
        self.rb_mode_raster.toggled.connect(self._toggle_mode_widgets)
        self._toggle_mode_widgets(self.rb_mode_raster.isChecked())

        # ---------- bottom: normalization + actions ----------
        self.cb_auto = QtWidgets.QCheckBox(tr("Auto Min/Max"))
        self.cb_auto.setChecked(True)
        self.sb_min = QtWidgets.QDoubleSpinBox(); self.sb_min.setDecimals(self.NUM_DECIMAL_PLACES)
        self.sb_min.setRange(self.MIN_VAL, self.MAX_VAL)
        self.sb_max = QtWidgets.QDoubleSpinBox(); self.sb_max.setDecimals(self.NUM_DECIMAL_PLACES)
        self.sb_max.setRange(self.MIN_VAL, self.MAX_VAL)
        self.sb_min.setEnabled(False); self.sb_max.setEnabled(False)
        self.cb_auto.toggled.connect(self._toggle_manual_minmax)

        self.cb_invert = QtWidgets.QCheckBox(tr("Invert (1 - x)"))

        norm_grid = QtWidgets.QGridLayout()
        norm_grid.addWidget(self.cb_auto, 0, 0, 1, 2)
        norm_grid.addWidget(QtWidgets.QLabel(tr("Min:")), 1, 0)
        norm_grid.addWidget(self.sb_min, 1, 1)
        norm_grid.addWidget(QtWidgets.QLabel(tr("Max:")), 2, 0)
        norm_grid.addWidget(self.sb_max, 2, 1)
        norm_grid.addWidget(self.cb_invert, 3, 0, 1, 2)

        # action buttons
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        ok_button = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        ok_button.setText(tr("Save"))
        ok_button.setAutoDefault(False)
        ok_button.setDefault(False)
        self.buttonBox.accepted.connect(self._on_save)
        self.buttonBox.rejected.connect(self.reject)

        # ---------- layout ----------
        right = QtWidgets.QVBoxLayout()
        right.addWidget(self.gp_const_pwl)
        right.addSpacing(6)
        right.addLayout(norm_grid)
        right.addSpacing(6)
        right.addWidget(self._message_bar)
        right.addWidget(self.buttonBox)

        split = QtWidgets.QHBoxLayout()
        split.addWidget(self.lst_pathways, 1)
        split.addLayout(right, 2)

        root = QtWidgets.QVBoxLayout(self)
        root.addLayout(header_layout)
        root.addLayout(split)

        # ---------- load data ----------
        self._load_pathways()
        self._load_collection()

    # ---------- helpers ----------
    def _mk_container(self, layout) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget(self); w.setLayout(layout); return w

    def _toggle_mode_widgets(self, raster_checked: bool):
        self._le_path.setEnabled(raster_checked)
        self._tb_browse.setEnabled(raster_checked)
        self._sb_const.setEnabled(not raster_checked)

    def _toggle_manual_minmax(self, auto: bool):
        self.sb_min.setEnabled(not auto)
        self.sb_max.setEnabled(not auto)

    def _browse_raster(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, tr("Select raster"), "", "GeoTIFF (*.tif *.tiff);;All Files (*)")
        if fn:
            self._le_path.setText(fn)

    def _load_pathways(self):
        self._ncs_pathway_model.clear()
        for p in settings_manager.get_all_ncs_pathways() or []:
            self._ncs_pathway_model.add_ncs_pathway(p)
        if self._ncs_pathway_model.rowCount() > 0:
            idx = self._ncs_pathway_model.index(0, 0)
            self.lst_pathways.selectionModel().select(idx, QtCore.QItemSelectionModel.ClearAndSelect)

    def _load_collection(self):
        coll = settings_manager.load_constant_pwl()
        if coll is None or len(coll.items) == 0:
            coll = make_default_collection_for_pathways(settings_manager.get_all_ncs_pathways() or [])
        self._collection = coll

        # set global opts
        self.cb_auto.setChecked(coll.scale_mode == ScaleMode.AUTO_MINMAX)
        self.sb_min.setValue(float(coll.min_value))
        self.sb_max.setValue(float(coll.max_value))
        self.cb_invert.setChecked(coll.invert_mode == Inversion.INVERT)
        self._toggle_manual_minmax(self.cb_auto.isChecked())

        # trigger UI for first pathway
        self._apply_current_pathway_to_ui()

    # ---------- pathway selection ----------
    def _on_pathway_selection_changed(self, *_):
        self._save_current_pathway_from_ui()
        self._apply_current_pathway_to_ui()

    def _current_pathway(self) -> Optional[NcsPathway]:
        sel = self.lst_pathways.selectedIndexes()
        if not sel:
            return None
        it = self._ncs_pathway_model.itemFromIndex(sel[0])
        return it.ncs_pathway if it else None

    # push UI values into current item
    def _save_current_pathway_from_ui(self):
        p = self._current_pathway()
        if p is None or self._collection is None:
            return

        item = self._find_or_create_item(p)
        item.enabled = self.gp_const_pwl.isChecked()
        item.input_mode = InputMode.RASTER_FILE if self.rb_mode_raster.isChecked() else InputMode.CONSTANT_VALUE
        item.raster_path = self._le_path.text().strip()
        item.constant_value = float(self._sb_const.value())
        item.normalized_raster_path = self._le_norm.text().strip()

    # pull item into UI
    def _apply_current_pathway_to_ui(self):
        p = self._current_pathway()
        if p is None:
            self.gp_const_pwl.setChecked(False)
            return

        item = self._find_or_create_item(p)
        self._current_pathway_identifier = str(p.uuid)

        self.gp_const_pwl.blockSignals(True)
        self.gp_const_pwl.setChecked(item.enabled)
        self.gp_const_pwl.blockSignals(False)

        if item.input_mode == InputMode.RASTER_FILE:
            self.rb_mode_raster.setChecked(True)
        else:
            self.rb_mode_const.setChecked(True)

        self._le_path.setText(item.raster_path or "")
        self._sb_const.setValue(float(item.constant_value or 0.0))
        self._le_norm.setText(item.normalized_raster_path or "")
        self._toggle_mode_widgets(self.rb_mode_raster.isChecked())

    def _find_or_create_item(self, pathway: NcsPathway) -> ConstantPwlItem:
        for it in self._collection.items:
            if str(it.pathway.uuid) == str(pathway.uuid):
                return it
        it = ConstantPwlItem(pathway=pathway, input_mode=InputMode.CONSTANT_VALUE)
        self._collection.items.append(it)
        return it

    # ---------- actions ----------
    def _on_groupbox_toggled(self, checked: bool):
        # nothing special here; we persist on Save
        del checked

    def _warn(self, msg: str):
        self._message_bar.pushMessage(msg, Qgis.Warning)

    def _validate_global(self) -> bool:
        if not self.cb_auto.isChecked():
            if self.sb_min.value() == self.sb_max.value():
                self._warn(tr("Minimum normalization value cannot equal maximum."))
                return False
        return True

    def _validate_current_item(self) -> bool:
        it = self._get_current_item()
        if it is None or not it.enabled:
            return True
        if it.input_mode == InputMode.RASTER_FILE and not self._le_path.text().strip():
            self._warn(tr("Raster mode selected but raster path is empty."))
            return False
        return True

    def _get_current_item(self) -> Optional[ConstantPwlItem]:
        p = self._current_pathway()
        if p is None:
            return None
        return self._find_or_create_item(p)

    def _on_save(self):
        self._message_bar.clearWidgets()

        self._save_current_pathway_from_ui()
        if not self._validate_global() or not self._validate_current_item():
            return

        # update global opts
        self._collection.scale_mode = ScaleMode.AUTO_MINMAX if self.cb_auto.isChecked() else ScaleMode.MANUAL_MINMAX
        self._collection.min_value = float(self.sb_min.value())
        self._collection.max_value = float(self.sb_max.value())
        self._collection.invert_mode = Inversion.INVERT if self.cb_invert.isChecked() else Inversion.NONE

        settings_manager.save_constant_pwl(self._collection)
        self.accept()
