# -*- coding: utf-8 -*-
"""
Dialog for creating and editing custom constant raster type definitions.
"""

import sys

from qgis.PyQt import QtCore, QtWidgets, QtGui

from ...models.base import ModelComponentType


class CustomTypeDefinitionDialog(QtWidgets.QDialog):
    """Dialog for defining custom constant raster types.

    Supports both create and edit modes for user-defined constant raster types.
    Custom types are always for activities.
    """

    def __init__(self, parent=None, edit_mode=False, existing_types=None):
        """Initialize the dialog.

        :param parent: Parent widget
        :param edit_mode: If True, dialog is in edit mode
        :param existing_types: List of existing type names for validation
        """
        super().__init__(parent)

        self.edit_mode = edit_mode
        self.existing_types = existing_types or []
        self.original_name = None  # Store original name in edit mode

        if edit_mode:
            self.setWindowTitle(self.tr("Edit Constant Raster Type"))
        else:
            self.setWindowTitle(self.tr("Add New Constant Raster Type"))
        self.setMinimumWidth(400)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Create the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)

        # Type configuration
        form_layout = QtWidgets.QFormLayout()

        # Type Name
        self.txt_type_name = QtWidgets.QLineEdit()
        self.txt_type_name.setPlaceholderText(self.tr("e.g., Market Trends"))
        form_layout.addRow(self.tr("Name:"), self.txt_type_name)

        # Range configuration group
        range_group = QtWidgets.QGroupBox(self.tr("Normalization Range Configuration"))
        range_layout = QtWidgets.QFormLayout(range_group)

        # Minimum value
        self.spin_min_value = QtWidgets.QDoubleSpinBox()
        self.spin_min_value.setRange(0.0, sys.float_info.max)
        self.spin_min_value.setDecimals(1)
        self.spin_min_value.setValue(0.0)
        self.spin_min_value.setToolTip(
            self.tr("Minimum value users can enter in the widget")
        )
        range_layout.addRow(self.tr("Minimum:"), self.spin_min_value)

        # Maximum value
        self.spin_max_value = QtWidgets.QDoubleSpinBox()
        self.spin_max_value.setRange(0.0, sys.float_info.max)
        self.spin_max_value.setDecimals(1)
        self.spin_max_value.setValue(100.0)
        self.spin_max_value.setToolTip(
            self.tr("Maximum value users can enter in the widget")
        )
        range_layout.addRow(self.tr("Maximum:"), self.spin_max_value)

        # Default value
        self.spin_default_value = QtWidgets.QDoubleSpinBox()
        self.spin_default_value.setRange(0.0, sys.float_info.max)
        self.spin_default_value.setDecimals(1)
        self.spin_default_value.setValue(0.0)
        self.spin_default_value.setToolTip(
            self.tr("Default value shown when creating a new raster component")
        )
        range_layout.addRow(self.tr("Default Value:"), self.spin_default_value)

        layout.addLayout(form_layout)
        layout.addWidget(range_group)

        # Validation message
        self.lbl_validation = QtWidgets.QLabel()
        self.lbl_validation.setStyleSheet("QLabel { color: red; }")
        self.lbl_validation.setWordWrap(True)
        self.lbl_validation.hide()
        layout.addWidget(self.lbl_validation)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _connect_signals(self):
        """Connect widget signals."""
        # Clear validation message when user types
        self.txt_type_name.textChanged.connect(lambda: self.lbl_validation.hide())
        self.spin_min_value.valueChanged.connect(self._validate_default_range)
        self.spin_max_value.valueChanged.connect(self._validate_default_range)
        self.spin_default_value.valueChanged.connect(self._validate_default_range)

    def _validate_default_range(self):
        """Ensure default value always stays between min and max."""
        min_val = self.spin_min_value.value()
        max_val = self.spin_max_value.value()
        default_val = self.spin_default_value.value()

        # Block ALL spinboxes to prevent circular valueChanged loops
        self.spin_min_value.blockSignals(True)
        self.spin_max_value.blockSignals(True)
        self.spin_default_value.blockSignals(True)

        # Auto-fix default value if outside new range
        if default_val < min_val:
            self.spin_default_value.setValue(min_val)
            default_val = min_val

        if default_val > max_val:
            self.spin_default_value.setValue(max_val)
            default_val = max_val

        # Unblock signals
        self.spin_min_value.blockSignals(False)
        self.spin_default_value.blockSignals(False)
        self.spin_max_value.blockSignals(False)

        # Hide any previous error while user edits
        self.lbl_validation.hide()

    def validate_and_accept(self):
        """Validate input and accept dialog if valid."""
        # Get value
        type_name = self.txt_type_name.text().strip()

        # Validate type name
        if not type_name:
            self._show_validation_error(self.tr("Type name cannot be empty."))
            return

        # Check for duplicate names (skip check if editing and name unchanged)
        if not (self.edit_mode and type_name == self.original_name):
            if type_name in self.existing_types:
                self._show_validation_error(
                    self.tr(
                        "A type named '{0}' already exists. Please choose a different name."
                    ).format(type_name)
                )
                return

        # Validate range values
        min_val = self.spin_min_value.value()
        max_val = self.spin_max_value.value()
        default_val = self.spin_default_value.value()

        if min_val >= max_val:
            self._show_validation_error(
                self.tr("Minimum value must be less than maximum value.")
            )
            return

        if default_val < min_val or default_val > max_val:
            self._show_validation_error(
                self.tr("Default value must be between minimum and maximum values.")
            )
            return

        # All validation passed
        self.accept()

    def _show_validation_error(self, message: str):
        """Show validation error message.

        :param message: Error message to display
        """
        self.lbl_validation.setText(message)
        self.lbl_validation.show()

    def set_values(self, type_def: dict):
        """Set dialog values from a type definition.

        Used in edit mode to populate the dialog with existing values.

        :param type_def: Dictionary with type definition
        """
        self.original_name = type_def.get("name", "")
        self.txt_type_name.setText(self.original_name)
        self.spin_min_value.setValue(type_def.get("min_value", 0.0))
        self.spin_max_value.setValue(type_def.get("max_value", 100.0))
        self.spin_default_value.setValue(type_def.get("default_value", 0.0))

    def get_type_definition(self) -> dict:
        """Get the type definition from dialog values.

        Returns user-configured values for min, max, and default.

        :returns: Dictionary with type definition
        """
        return {
            "name": self.txt_type_name.text().strip(),
            "component_type": ModelComponentType.ACTIVITY.value,
            "min_value": self.spin_min_value.value(),
            "max_value": self.spin_max_value.value(),
            "default_value": self.spin_default_value.value(),
        }
