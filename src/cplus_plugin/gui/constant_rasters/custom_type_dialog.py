# -*- coding: utf-8 -*-
"""
Dialog for creating and editing custom constant raster type definitions.
"""

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

        self.setWindowTitle("Edit Custom Type" if edit_mode else "Add Custom Type")
        self.setMinimumWidth(400)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Create the dialog UI."""
        layout = QtWidgets.QVBoxLayout(self)

        # Type Name
        name_group = QtWidgets.QGroupBox("Type Information")
        name_layout = QtWidgets.QFormLayout(name_group)

        self.txt_type_name = QtWidgets.QLineEdit()
        self.txt_type_name.setPlaceholderText("e.g., Market Trends")
        name_layout.addRow("Type Name:", self.txt_type_name)

        layout.addWidget(name_group)

        # Validation message
        self.lbl_validation = QtWidgets.QLabel()
        self.lbl_validation.setStyleSheet("QLabel { color: red; }")
        self.lbl_validation.setWordWrap(True)
        self.lbl_validation.hide()
        layout.addWidget(self.lbl_validation)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _connect_signals(self):
        """Connect widget signals."""
        # Clear validation message when user types
        self.txt_type_name.textChanged.connect(lambda: self.lbl_validation.hide())

    def validate_and_accept(self):
        """Validate input and accept dialog if valid."""
        # Get value
        type_name = self.txt_type_name.text().strip()

        # Validate type name
        if not type_name:
            self._show_validation_error("Type name cannot be empty.")
            return

        # Check for duplicate names (skip check if editing and name unchanged)
        if not (self.edit_mode and type_name == self.original_name):
            if type_name in self.existing_types:
                self._show_validation_error(
                    f"A type named '{type_name}' already exists. Please choose a different name."
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

        :param type_def: Dictionary with type definition (name)
        """
        self.original_name = type_def.get("name", "")
        self.txt_type_name.setText(self.original_name)

    def get_type_definition(self) -> dict:
        """Get the type definition from dialog values.

        Returns default values for min_value and max_value
        that match Years of Experience widget.

        :returns: Dictionary with type definition
        """
        return {
            "name": self.txt_type_name.text().strip(),
            "component_type": ModelComponentType.ACTIVITY.value,
            "min_value": 0.0,
            "max_value": 100.0,
        }
