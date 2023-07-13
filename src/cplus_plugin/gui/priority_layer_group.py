# -*- coding: utf-8 -*-
"""
    Priority group item widget
"""

import os
import typing
import uuid

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtNetwork,
    QtWidgets,
)
from qgis.PyQt.uic import loadUiType

from ..models.base import PRIORITY_GROUP

from ..conf import settings_manager

from ..utils import log


DialogUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/priority_layer_dialog.ui")
)


class PriorityLayerDialog(QtWidgets.QDialog, DialogUi):
    """Dialog that provide UI for priority layer details."""

    slider_value_changed = QtCore.pyqtSignal()
    input_value_changed = QtCore.pyqtSignal()

    def __init__(
        self,
        layer=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.layer = layer

        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        ok_signals = [
            self.layer_name.textChanged,
            self.layer_description.textChanged,
        ]

        for signal in ok_signals:
            signal.connect(self.update_ok_buttons)

        self.initialize_ui()

    def update_ok_buttons(self):
        """Responsible for changing the state of the
        connection dialog OK button.
        """
        enabled_state = (
            self.layer_name.text() != "" and self.layer_description.toPlainText() != ""
        )
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(enabled_state)

    def initialize_ui(self):
        """Populate UI inputs when loading the dialog"""
        layer = self.layer
        if layer is not None:
            self.layer_name.setText(layer["name"])
            self.layer_description.setText(layer["description"])

            priority_groups = settings_manager.get_priority_groups()

            for group in priority_groups:
                layer_group = settings_manager.find_group_by_name(group["name"])
                layer_has_group = False

                for group_in_layer in layer.get("groups"):
                    if group_in_layer["name"] == layer_group["name"]:
                        layer_has_group = True
                        break

                if group["name"] == PRIORITY_GROUP.CARBON_IMPORTANCE.value:
                    self.carbon_importance_box.setValue(int(layer_group["value"]))
                    self.carbon_importance_chk.setChecked(layer_has_group)
                elif group["name"] == PRIORITY_GROUP.BIODIVERSITY.value:
                    self.biodiversity_box.setValue(int(layer_group["value"]))
                    self.biodiversity_chk.setChecked(layer_has_group)
                elif group["name"] == PRIORITY_GROUP.LIVELIHOOD.value:
                    self.livelihood_box.setValue(int(layer_group["value"]))
                    self.livelihood_chk.setChecked(layer_has_group)
                elif group["name"] == PRIORITY_GROUP.CLIMATE_RESILIENCE.value:
                    self.climate_resilience_box.setValue(int(layer_group["value"]))
                    self.climate_resilience_chk.setChecked(layer_has_group)
                elif (
                    layer_group["name"]
                    == PRIORITY_GROUP.ECOLOGICAL_INFRASTRUCTURE.value
                ):
                    self.ecological_box.setValue(int(layer_group["value"]))
                    self.ecological_chk.setChecked(layer_has_group)
                elif group["name"] == PRIORITY_GROUP.POLICY.value:
                    self.policy_box.setValue(int(layer_group["value"]))
                    self.policy_chk.setChecked(layer_has_group)
                elif group["name"] == PRIORITY_GROUP.FINANCE_YEARS_EXPERIENCE.value:
                    self.finance_experience_box.setValue(int(layer_group["value"]))
                    self.finance_experience_chk.setChecked(layer_has_group)
                elif group["name"] == PRIORITY_GROUP.FINANCE_MARKET_TRENDS.value:
                    self.finance_market_box.setValue(int(layer_group["value"]))
                    self.finance_market_chk.setChecked(layer_has_group)
                elif group["name"] == PRIORITY_GROUP.FINANCE_NET_PRESENT_VALUE.value:
                    self.finance_present_value_box.setValue(int(layer_group["value"]))
                    self.finance_present_value_chk.setChecked(layer_has_group)
                elif group["name"] == PRIORITY_GROUP.FINANCE_CARBON.value:
                    self.finance_carbon_box.setValue(int(layer_group["value"]))
                    self.finance_carbon_chk.setChecked(layer_has_group)

        self.carbon_importance_chk.toggled.connect(self.group_toggle)
        self.biodiversity_chk.toggled.connect(self.group_toggle)
        self.livelihood_chk.toggled.connect(self.group_toggle)
        self.climate_resilience_chk.toggled.connect(self.group_toggle)
        self.ecological_chk.toggled.connect(self.group_toggle)
        self.policy_chk.toggled.connect(self.group_toggle)
        self.finance_experience_chk.toggled.connect(self.group_toggle)
        self.finance_present_value_chk.toggled.connect(self.group_toggle)
        self.finance_market_chk.toggled.connect(self.group_toggle)
        self.finance_carbon_chk.toggled.connect(self.group_toggle)

    def group_toggle(self):
        sender = self.sender()
        name = None

        if sender == self.carbon_importance_chk:
            name = PRIORITY_GROUP.CARBON_IMPORTANCE.value
        elif sender == self.biodiversity_chk:
            name = PRIORITY_GROUP.BIODIVERSITY.value
        elif sender == self.livelihood_chk:
            name = PRIORITY_GROUP.LIVELIHOOD.value
        elif sender == self.climate_resilience_chk:
            name = PRIORITY_GROUP.CLIMATE_RESILIENCE.value
        elif sender == self.ecological_chk:
            name = PRIORITY_GROUP.ECOLOGICAL_INFRASTRUCTURE.value
        elif sender == self.policy_chk:
            name = PRIORITY_GROUP.POLICY.value
        elif sender == self.finance_experience_chk:
            name = PRIORITY_GROUP.FINANCE_YEARS_EXPERIENCE.value
        elif sender == self.finance_present_value_chk:
            name = PRIORITY_GROUP.FINANCE_NET_PRESENT_VALUE.value
        elif sender == self.finance_market_chk:
            name = PRIORITY_GROUP.FINANCE_MARKET_TRENDS.value
        elif sender == self.finance_carbon_chk:
            name = PRIORITY_GROUP.FINANCE_CARBON.value

        if name:
            self.add_group(name, 0)

    def add_group(self, name, value):
        if self.layer is not None:
            groups = self.layer.get("groups")
            group = {}
            group["name"] = name
            group["value"] = value
            found = False
            for group in groups:
                if group["name"] == name:
                    group["value"] = value
                    found = True
            if not found:
                groups.append(group)
            settings_manager.save_priority_layer(self.layer)

    def accept(self):
        """Handles logic for adding new connections"""
        layer_id = uuid.uuid4()
        layer = {}
        groups = []

        if self.layer is not None:
            layer_id = self.layer.get("uuid")
            check_boxes_names = {
                self.carbon_importance_chk: PRIORITY_GROUP.CARBON_IMPORTANCE.value,
                self.biodiversity_chk: PRIORITY_GROUP.BIODIVERSITY.value,
                self.livelihood_chk: PRIORITY_GROUP.LIVELIHOOD.value,
                self.climate_resilience_chk: PRIORITY_GROUP.CLIMATE_RESILIENCE.value,
                self.ecological_chk: PRIORITY_GROUP.ECOLOGICAL_INFRASTRUCTURE.value,
                self.policy_chk: PRIORITY_GROUP.POLICY.value,
                self.finance_experience_chk: PRIORITY_GROUP.FINANCE_YEARS_EXPERIENCE.value,
                self.finance_present_value_chk: PRIORITY_GROUP.FINANCE_NET_PRESENT_VALUE.value,
                self.finance_market_chk: PRIORITY_GROUP.FINANCE_MARKET_TRENDS.value,
                self.finance_carbon_chk: PRIORITY_GROUP.FINANCE_CARBON.value,
            }

            check_boxes_input = {
                self.carbon_importance_chk: self.carbon_importance_box.value(),
                self.biodiversity_chk: self.biodiversity_box.value(),
                self.livelihood_chk: self.livelihood_box.value(),
                self.climate_resilience_chk: self.climate_resilience_box.value(),
                self.ecological_chk: self.ecological_box.value(),
                self.policy_chk: self.policy_box.value(),
                self.finance_experience_chk: self.finance_experience_box.value(),
                self.finance_present_value_chk: self.finance_present_value_box.value(),
                self.finance_market_chk: self.finance_market_box.value(),
                self.finance_carbon_chk: self.finance_carbon_box.value(),
            }

            for chbox, group_name in check_boxes_names.items():
                if chbox.isChecked():
                    group = {"name": group_name, "value": check_boxes_input[chbox]}
                    groups.append(group)

        layer["uuid"] = str(layer_id)
        layer["name"] = self.layer_name.text()
        layer["description"] = self.layer_description.toPlainText()
        layer["selected"] = True
        layer["groups"] = groups

        settings_manager.save_priority_layer(layer)
        settings_manager.set_current_priority_layer(layer_id)

        # TODO remove this hack for fixing the 'selected' attribute value
        settings_manager.save_priority_layer(layer)
        super().accept()
