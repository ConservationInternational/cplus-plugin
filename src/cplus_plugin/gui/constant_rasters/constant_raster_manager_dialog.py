# -*- coding: utf-8 -*-
"""
Dialog for managing constant rasters for activities.
"""

import os
import sys
import typing
from datetime import datetime

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
)
from qgis.gui import QgsGui, QgsMessageBar
from qgis.utils import iface

from ...conf import settings_manager, Settings
from ...models.base import ModelComponentType
from ...models.constant_raster import (
    ConstantRasterCollection,
    ConstantRasterComponent,
    ConstantRasterContext,
)
from ...lib.constant_raster import (
    constant_raster_registry,
)
from ...definitions.constants import (
    COMPONENT_TYPE_ATTRIBUTE,
    DEFAULT_VALUE_ATTRIBUTE_KEY,
    ID_ATTRIBUTE,
    NAME_ATTRIBUTE,
    MIN_VALUE_ATTRIBUTE_KEY,
    MAX_VALUE_ATTRIBUTE_KEY,
)
from ...definitions.defaults import (
    ICON_PATH,
    NPV_METADATA_ID,
    YEARS_EXPERIENCE_ACTIVITY_ID,
)
from ..component_item_model import ActivityItemModel
from .constant_raster_widgets import (
    ConstantRasterWidgetInterface,
    YearsExperienceWidget,
    GenericNumericWidget,
)
from .custom_type_dialog import CustomTypeDefinitionDialog
from .financial_npv_widget import ActivityNpvWidget
from ...utils import log, tr, clean_filename, FileUtils


class ConstantRastersManagerDialog(QtWidgets.QDialog):
    """Dialog for managing constant rasters."""

    # Signal emitted when user requests to create constant rasters
    # Parameters: (context: ConstantRasterContext, collection: ConstantRasterCollection,
    #             input_range: tuple, metadata_id: str, current_view: bool)
    # current_view: True = current view only, False = all constant raster types
    create_rasters_requested = QtCore.pyqtSignal(
        ConstantRasterContext, ConstantRasterCollection, tuple, str, bool
    )

    # Signal emitted when raster creation is complete (for showing results in dialog)
    # Parameters: (success: bool, message: str, count: int)
    raster_creation_completed = QtCore.pyqtSignal(bool, str, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        QgsGui.enableAutoGeometryRestore(self)

        self.setWindowTitle(tr("Constant Raster Manager"))

        self.constant_raster_registry = constant_raster_registry

        # Registry for configuration widgets
        self._registered_component_widgets = {}

        # Current raster collection being viewed/edited
        self.current_raster_collection: typing.Optional[ConstantRasterCollection] = None

        # Create UI
        self._create_ui()

        # Initialize
        self.initialize()

    def _create_ui(self):
        """Create the user interface."""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Information banner
        info_banner = QtWidgets.QFrame()
        info_banner.setFrameShape(QtWidgets.QFrame.StyledPanel)
        info_banner.setFrameShadow(QtWidgets.QFrame.Raised)
        info_banner.setMinimumHeight(100)
        info_banner.setMaximumHeight(100)
        info_banner.setAutoFillBackground(False)
        info_banner.setStyleSheet("background-color: rgb(255, 255, 255);")

        info_layout = QtWidgets.QHBoxLayout(info_banner)

        # CPLUS logo/icon
        icon_label = QtWidgets.QLabel()
        icon_label.setMaximumSize(91, 81)
        icon_label.setPixmap(QtGui.QPixmap(ICON_PATH))
        icon_label.setScaledContents(True)
        info_layout.addWidget(icon_label)

        # Information text
        info_text = QtWidgets.QLabel(
            self.tr(
                "Define constant raster parameters for activities. "
                "Configure input values, specify the output normalization "
                "range, and create rasters clipped to your project's "
                "extent as defined in Step 1."
            )
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        main_layout.addWidget(info_banner)

        # Top section: Description + Raster Type
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Message bar for feedback
        self.message_bar = QgsMessageBar()
        top_layout.addWidget(self.message_bar)

        # Constant raster type selection
        raster_type_widget = QtWidgets.QWidget()
        raster_type_layout = QtWidgets.QHBoxLayout(raster_type_widget)
        raster_type_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_raster_type = QtWidgets.QLabel(self.tr("Constant raster type:"))
        self.cbo_raster_type = QtWidgets.QComboBox()
        self.cbo_raster_type.setMinimumWidth(200)
        raster_type_layout.addWidget(self.lbl_raster_type)
        raster_type_layout.addWidget(self.cbo_raster_type)

        # Custom type management buttons
        add_icon = FileUtils.get_icon("symbologyAdd.svg")
        self.btn_add_custom_type = QtWidgets.QToolButton()
        self.btn_add_custom_type.setIcon(add_icon)
        self.btn_add_custom_type.setToolTip(self.tr("Add New Constant Raster Type"))
        raster_type_layout.addWidget(self.btn_add_custom_type)

        edit_icon = FileUtils.get_icon("mActionToggleEditing.svg")
        self.btn_edit_custom_type = QtWidgets.QToolButton()
        self.btn_edit_custom_type.setIcon(edit_icon)
        self.btn_edit_custom_type.setToolTip(self.tr("Edit Constant Raster Type"))
        self.btn_edit_custom_type.setEnabled(False)
        raster_type_layout.addWidget(self.btn_edit_custom_type)

        delete_icon = FileUtils.get_icon("symbologyRemove.svg")
        self.btn_delete_custom_type = QtWidgets.QToolButton()
        self.btn_delete_custom_type.setIcon(delete_icon)
        self.btn_delete_custom_type.setToolTip(self.tr("Delete Constant Raster Type"))
        self.btn_delete_custom_type.setEnabled(False)
        raster_type_layout.addWidget(self.btn_delete_custom_type)

        raster_type_layout.addStretch()
        top_layout.addWidget(raster_type_widget)

        main_layout.addWidget(top_widget)

        # Middle section: Two-column layout with splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Left column - Component list
        self._left_group = QtWidgets.QGroupBox()
        self._left_group.setTitle(self.tr("Activities"))
        left_layout = QtWidgets.QVBoxLayout(self._left_group)

        self.lst_activities = QtWidgets.QListView()
        left_layout.addWidget(self.lst_activities)

        splitter.addWidget(self._left_group)

        # Right column - Configuration + Min/Max
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Configuration widget container
        self.sw_component_container = QtWidgets.QStackedWidget()

        # Add a blank widget as default
        blank_widget = QtWidgets.QLabel(self.tr("Select a component to configure"))
        blank_widget.setAlignment(QtCore.Qt.AlignCenter)
        blank_widget.setStyleSheet("color: gray; padding: 20px;")
        self.sw_component_container.addWidget(blank_widget)

        right_layout.addWidget(self.sw_component_container, 1)

        # Normalization range (collapsible)
        # This allows users to remap the normalized output to any range they want
        self.grp_normalization_range = QtWidgets.QGroupBox(
            self.tr("Normalization Range")
        )
        self.grp_normalization_range.setCheckable(True)
        self.grp_normalization_range.setChecked(True)
        self.grp_normalization_range.setToolTip(
            self.tr(
                "When checked: manually set min/max values.\n"
                "When unchecked: automatically calculate min/max from component values."
            )
        )
        norm_layout = QtWidgets.QFormLayout(self.grp_normalization_range)
        self.spin_min_value = QtWidgets.QDoubleSpinBox()
        self.spin_min_value.setRange(0.0, sys.float_info.max)
        self.spin_min_value.setDecimals(3)
        self.spin_min_value.setSingleStep(0.1)
        self.spin_min_value.setValue(0.0)
        self.spin_min_value.setToolTip(self.tr("Minimum output value for the raster"))
        self.spin_max_value = QtWidgets.QDoubleSpinBox()
        self.spin_max_value.setRange(0.0, sys.float_info.max)
        self.spin_max_value.setDecimals(3)
        self.spin_max_value.setSingleStep(0.1)
        self.spin_max_value.setValue(0.0)
        self.spin_max_value.setToolTip(self.tr("Maximum output value for the raster"))
        norm_layout.addRow(self.tr("Minimum"), self.spin_min_value)
        norm_layout.addRow(self.tr("Maximum"), self.spin_max_value)
        right_layout.addWidget(self.grp_normalization_range)

        # Last updated timestamp label
        self.lbl_last_updated = QtWidgets.QLabel("")
        self.lbl_last_updated.setStyleSheet(
            "color: gray; font-size: 9pt; font-style: italic;"
        )
        self.lbl_last_updated.setAlignment(QtCore.Qt.AlignLeft)
        self.lbl_last_updated.setContentsMargins(5, 5, 5, 5)
        right_layout.addWidget(self.lbl_last_updated)

        splitter.addWidget(right_widget)

        # Set initial splitter sizes (40% left, 60% right)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter, 1)

        # Bottom: Action buttons
        button_layout = QtWidgets.QHBoxLayout()

        # Create tool button with dropdown menu for raster creation
        self.btn_create_current = QtWidgets.QToolButton()
        self.btn_create_current.setText(self.tr("Create Rasters"))
        self.btn_create_current.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.btn_create_current.setToolTip(
            self.tr("Create constant rasters for current view or all types")
        )

        # Create menu for the button
        create_menu = QtWidgets.QMenu(self)

        # Add menu actions
        self.action_create_current = create_menu.addAction(
            self.tr("Create - Current View")
        )
        self.action_create_current.triggered.connect(
            lambda: self.update_current_widget(current_view=True)
        )

        self.action_create_all = create_menu.addAction(
            self.tr("Create - All Constant Raster Types")
        )
        self.action_create_all.triggered.connect(
            lambda: self.update_current_widget(current_view=False)
        )

        # Set menu to button
        self.btn_create_current.setMenu(create_menu)

        # Set default action (triggered when button clicked directly)
        self.btn_create_current.setDefaultAction(self.action_create_current)

        self.btn_close = QtWidgets.QPushButton(self.tr("Close"))
        button_layout.addWidget(self.btn_create_current)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_close)
        main_layout.addLayout(button_layout)

    def register_widget(
        self, metadata_id: str, config_widget: ConstantRasterWidgetInterface
    ) -> bool:
        """Register a configuration widget for a particular constant raster type.

        :param metadata_id: Metadata ID for the constant raster type
        :param config_widget: Widget implementing ConstantRasterWidgetInterface
        :returns: False if a widget for the given metadata id has already been registered
        """
        if metadata_id in self._registered_component_widgets:
            return False

        idx = self.sw_component_container.addWidget(config_widget)
        self._registered_component_widgets[metadata_id] = idx

        # Check if it implements the raster widget interface
        if isinstance(config_widget, ConstantRasterWidgetInterface):
            if hasattr(config_widget, "update_requested"):
                config_widget.update_requested.connect(self.on_update_raster_component)

        return True

    def widget_by_identifier(
        self, metadata_id: str
    ) -> typing.Optional[ConstantRasterWidgetInterface]:
        """Return configuration widget by metadata ID.

        :param metadata_id: Metadata ID to look up
        :returns: Widget if found, None otherwise
        """
        if metadata_id not in self._registered_component_widgets:
            return None

        idx = self._registered_component_widgets[metadata_id]
        return self.sw_component_container.widget(idx)

    def show_widget(self, metadata_id: str):
        """Show widget corresponding to the given metadata ID or a blank widget if not found.

        :param metadata_id: Metadata ID to show widget for
        """
        if metadata_id not in self._registered_component_widgets:
            # Show the blank widget (index 0)
            self.sw_component_container.setCurrentIndex(0)
            # Show error message to user
            self.message_bar.pushWarning(
                self.tr("Configuration Error"),
                self.tr(
                    "No widget defined for metadata ID '{metadata_id}'. Please contact the plugin developer."
                ).format(metadata_id=metadata_id),
            )
            return

        self.sw_component_container.setCurrentIndex(
            self._registered_component_widgets[metadata_id]
        )

    def _populate_component_references(self, activities):
        """Connect loaded components with actual Activity objects.

        After loading from settings, components have component=None. This method
        matches them with actual Activity objects based on saved component_ids.

        :param activities: List of Activity objects
        """
        # Create lookup dict for activities by UUID
        activity_lookup = {str(activity.uuid): activity for activity in activities}

        # Populate component references in all collections
        for metadata in self.constant_raster_registry.items():
            if metadata.raster_collection:
                for component in metadata.raster_collection.components:
                    # Skip if already has component reference
                    if component.component is not None:
                        continue

                    # Look up activity by saved UUID
                    saved_uuid = getattr(component, "_saved_component_uuid", None)
                    if saved_uuid and saved_uuid in activity_lookup:
                        component.component = activity_lookup[saved_uuid]
                        # Clean up temporary attribute
                        delattr(component, "_saved_component_uuid")

    def initialize(self):
        """Initialize UI components and connections."""

        # Load saved state from settings
        self.constant_raster_registry.load()

        # Register widgets for known constant rasters
        metadata_ids = self.constant_raster_registry.metadata_ids()
        if YEARS_EXPERIENCE_ACTIVITY_ID in metadata_ids:
            experience_widget_activity = YearsExperienceWidget()
            self.register_widget(
                YEARS_EXPERIENCE_ACTIVITY_ID, experience_widget_activity
            )

        if NPV_METADATA_ID in metadata_ids:
            self.register_widget(NPV_METADATA_ID, ActivityNpvWidget())

        # Register widgets for custom types
        for metadata_id in metadata_ids:
            metadata = self.constant_raster_registry.metadata_by_id(metadata_id)
            if metadata and metadata.user_defined:
                # Get custom type definition to retrieve configuration
                type_def = self.constant_raster_registry.get_custom_type_definition(
                    metadata_id
                )
                if type_def:
                    # Create widget for this custom type
                    widget = GenericNumericWidget(
                        label=type_def.get(NAME_ATTRIBUTE, self.tr("Custom Type")),
                        metadata_id=metadata_id,
                        min_value=type_def.get(MIN_VALUE_ATTRIBUTE_KEY, 0.0),
                        max_value=type_def.get(MAX_VALUE_ATTRIBUTE_KEY, 100.0),
                        default_value=type_def.get(DEFAULT_VALUE_ATTRIBUTE_KEY, 0.0),
                        parent=self.sw_component_container,
                    )
                    self.register_widget(metadata_id, widget)

        # Load activity model
        self._activities_model = ActivityItemModel(
            load_pathways=False, is_checkable=True
        )
        self.lst_activities.setModel(self._activities_model)
        activities = settings_manager.get_all_activities()
        for activity in activities:
            self._activities_model.add_activity(activity)

        # Populate component references with actual activity objects
        self._populate_component_references(activities)

        # Connect to the view's selection model, not the model itself
        self.lst_activities.selectionModel().selectionChanged.connect(
            self._on_model_component_selection_changed
        )

        # Connections
        self.cbo_raster_type.currentIndexChanged.connect(
            self.on_raster_type_selection_changed
        )
        self.btn_add_custom_type.clicked.connect(self.on_add_custom_type_clicked)
        self.btn_edit_custom_type.clicked.connect(self.on_edit_custom_type_clicked)
        self.btn_delete_custom_type.clicked.connect(self.on_delete_custom_type_clicked)
        # Note: btn_create_current uses menu actions, not direct clicked connection
        self.btn_close.clicked.connect(self.close)

        # Connect model itemChanged signals to save checkbox states
        self._activities_model.itemChanged.connect(self._on_item_checked_changed)

        # Connect normalization range spinboxes to save the values to the collection
        self.spin_min_value.valueChanged.connect(self.on_normalization_range_changed)
        self.spin_max_value.valueChanged.connect(self.on_normalization_range_changed)

        # Connect normalization group box toggle to auto-calculate min/max
        self.grp_normalization_range.toggled.connect(self.on_normalization_toggled)

        # Restore UI state from saved components
        self._restore_ui_state()

    def load_activities(self):
        """Load activity metadata into the raster type dropdown and restore selection."""
        # Get metadata for activities
        activity_metadatas = self.constant_raster_registry.metadata_by_component_type(
            ModelComponentType.ACTIVITY
        )
        self.cbo_raster_type.clear()
        for metadata in activity_metadatas:
            self.cbo_raster_type.addItem(metadata.display_name, metadata.id)

        # Try to restore the previously selected activity raster type
        activity_raster_type = settings_manager.get_value(
            Settings.CONSTANT_RASTERS_DIALOG_ACTIVITY_TYPE, default=None
        )

        # Select the saved raster type if available, otherwise first item
        if activity_raster_type:
            for i in range(self.cbo_raster_type.count()):
                if self.cbo_raster_type.itemData(i) == activity_raster_type:
                    self.cbo_raster_type.setCurrentIndex(i)
                    break
        elif self.cbo_raster_type.count() > 0:
            self.cbo_raster_type.setCurrentIndex(0)

        # Auto-select first checked activity to load its values into widget
        for row in range(self._activities_model.rowCount()):
            item = self._activities_model.item(row)
            if item and item.checkState() == QtCore.Qt.Checked:
                index = self._activities_model.indexFromItem(item)
                self.lst_activities.setCurrentIndex(index)
                break

    def on_raster_type_selection_changed(self, index: int):
        """Slot raised when the selection in the combobox for raster type has changed."""
        metadata_id = self.cbo_raster_type.itemData(index)
        if metadata_id:
            self.show_widget(metadata_id)

            # Restore normalization mode for this metadata_id
            auto_mode_key = f"constant_rasters_dialog/auto_mode/{metadata_id}"
            is_auto_mode = settings_manager.get_value(
                auto_mode_key, default=False, setting_type=bool
            )

            self.grp_normalization_range.blockSignals(True)
            self.grp_normalization_range.setChecked(not is_auto_mode)
            self.grp_normalization_range.blockSignals(False)

            self.spin_min_value.setEnabled(not is_auto_mode)
            self.spin_max_value.setEnabled(not is_auto_mode)

            # Update min/max values from the collection
            collection = self.constant_raster_registry.collection_by_id(metadata_id)
            if collection is not None:
                # Block signals while loading
                self.spin_min_value.blockSignals(True)
                self.spin_max_value.blockSignals(True)

                # Reset invalid range
                if collection.min_value > collection.max_value:
                    collection.min_value = 0.0
                    collection.max_value = 0.0

                self.spin_min_value.setValue(collection.min_value)
                self.spin_max_value.setValue(collection.max_value)

                self.spin_min_value.blockSignals(False)
                self.spin_max_value.blockSignals(False)

                # Update button states based on skip_raster flag
                self._update_create_button_states(collection)

                # Update custom type button states
                self._update_custom_type_button_states()

                # Update last updated timestamp display
                self._update_last_updated_display(collection)

            # Reload currently selected activity's component into the new widget
            current_index = self.lst_activities.currentIndex()
            if current_index.isValid():
                model_item = self._activities_model.itemFromIndex(current_index)
                if model_item:
                    model_identifier = model_item.uuid
                    current_config_widget = self.sw_component_container.currentWidget()

                    if isinstance(current_config_widget, ConstantRasterWidgetInterface):
                        # Get the component for this activity in the new collection
                        raster_component = collection.component_by_id(model_identifier)
                        component_created = False

                        if raster_component is None:
                            # Create a default one for this activity in the new collection
                            raster_component = (
                                current_config_widget.create_raster_component(
                                    model_item.model_component
                                )
                            )
                            collection.components.append(raster_component)
                            component_created = True

                        # Load into widget
                        current_config_widget.raster_component = raster_component
                        current_config_widget.reset()
                        current_config_widget.load(raster_component)

                        # Save if we created a new component
                        if component_created:
                            self.constant_raster_registry.save()

    def _update_create_button_states(self, collection):
        """Update create button states based on collection's skip_raster flag.

        :param collection: ConstantRasterCollection to check
        """
        if collection is None:
            return

        # Disable current view action if skip_raster is True
        if collection.skip_raster:
            self.action_create_current.setEnabled(True)  # Always enabled
            self.action_create_current.setToolTip(
                self.tr(
                    "Current view disabled - this constant raster type does not require rasters"
                )
            )
        else:
            self.action_create_current.setEnabled(True)
            self.action_create_current.setToolTip(
                self.tr("Create rasters for the current view")
            )

        # "All types" action is always enabled
        self.action_create_all.setEnabled(True)

    def _update_last_updated_display(self, collection):
        """Update the last updated timestamp display.

        :param collection: ConstantRasterCollection to display timestamp for
        """
        if collection is None or not collection.last_updated:
            self.lbl_last_updated.setText("")
            return

        # Parse ISO timestamp and format it nicely
        try:
            timestamp = datetime.fromisoformat(collection.last_updated)
            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            self.lbl_last_updated.setText(
                self.tr("Last updated: {time}").format(time=formatted_time)
            )
        except (ValueError, AttributeError):
            # If parsing fails, show the raw timestamp
            self.lbl_last_updated.setText(
                self.tr("Last updated: {time}").format(time=collection.last_updated)
            )

    def on_normalization_range_changed(self, value: float):
        """Slot raised when normalization range spinbox values change."""
        collection = self.current_constant_raster_collection()
        if collection is not None:
            min_val = self.spin_min_value.value()
            max_val = self.spin_max_value.value()

            # Basic validation: min must not be greater than max
            # Allow equal values (e.g., during initialization or for constant output)
            if min_val > max_val:
                self.message_bar.pushWarning(
                    self.tr("Invalid Range"),
                    self.tr("Minimum value must not be greater than maximum value."),
                )
                return

            collection.min_value = min_val
            collection.max_value = max_val

            # If in manual mode, save the manual values to QgsSettings
            if self.grp_normalization_range.isChecked():
                current_metadata_id = self.cbo_raster_type.itemData(
                    self.cbo_raster_type.currentIndex()
                )
                if current_metadata_id:
                    manual_min_key = (
                        f"constant_rasters_dialog/manual_min/{current_metadata_id}"
                    )
                    manual_max_key = (
                        f"constant_rasters_dialog/manual_max/{current_metadata_id}"
                    )
                    settings_manager.set_value(manual_min_key, min_val)
                    settings_manager.set_value(manual_max_key, max_val)

            # Update timestamp
            collection.last_updated = datetime.now().isoformat()
            self._update_last_updated_display(collection)

            self.constant_raster_registry.save()

    def on_normalization_toggled(self, checked: bool):
        """Slot raised when normalization range group box is toggled.

        When unchecked, automatically calculate min/max from component values.
        When checked, allow manual editing and restore previous manual values.

        :param checked: True if group box is checked (manual mode)
        """
        # Save the checkbox state
        current_metadata_id = self.cbo_raster_type.itemData(
            self.cbo_raster_type.currentIndex()
        )
        if current_metadata_id:
            auto_mode_key = f"constant_rasters_dialog/auto_mode/{current_metadata_id}"
            settings_manager.set_value(auto_mode_key, not checked)

        # Enable/disable spinboxes based on checked state
        self.spin_min_value.setEnabled(checked)
        self.spin_max_value.setEnabled(checked)

        if not checked:
            # Save current manual values to QgsSettings before switching to auto mode
            if current_metadata_id:
                manual_min_key = (
                    f"constant_rasters_dialog/manual_min/{current_metadata_id}"
                )
                manual_max_key = (
                    f"constant_rasters_dialog/manual_max/{current_metadata_id}"
                )
                settings_manager.set_value(manual_min_key, self.spin_min_value.value())
                settings_manager.set_value(manual_max_key, self.spin_max_value.value())

            # Auto-calculate mode - update from collection
            self._auto_calculate_normalization_range()
        else:
            # Manual mode - restore previous manual values from QgsSettings
            if current_metadata_id:
                manual_min_key = (
                    f"constant_rasters_dialog/manual_min/{current_metadata_id}"
                )
                manual_max_key = (
                    f"constant_rasters_dialog/manual_max/{current_metadata_id}"
                )

                manual_min = settings_manager.get_value(
                    manual_min_key, default=None, setting_type=float
                )
                manual_max = settings_manager.get_value(
                    manual_max_key, default=None, setting_type=float
                )

                if manual_min is not None and manual_max is not None:
                    # Restore saved manual values
                    self.spin_min_value.blockSignals(True)
                    self.spin_max_value.blockSignals(True)

                    self.spin_min_value.setValue(manual_min)
                    self.spin_max_value.setValue(manual_max)

                    self.spin_min_value.blockSignals(False)
                    self.spin_max_value.blockSignals(False)

            # Explicitly set the collection's min/max from spinboxes
            collection = self.current_constant_raster_collection()
            if collection is not None:
                collection.min_value = self.spin_min_value.value()
                collection.max_value = self.spin_max_value.value()

                # Update timestamp
                collection.last_updated = datetime.now().isoformat()
                self._update_last_updated_display(collection)

                # Save to registry
                self.constant_raster_registry.save()

    def _auto_calculate_normalization_range(self):
        """Auto-calculate normalization range from component absolute values."""
        collection = self.current_constant_raster_collection()
        if collection is None:
            return

        # Call normalize to calculate min/max from component values
        collection.normalize()

        # Update UI to show calculated values
        self.spin_min_value.blockSignals(True)
        self.spin_max_value.blockSignals(True)
        self.spin_min_value.setValue(collection.min_value)
        self.spin_max_value.setValue(collection.max_value)
        self.spin_min_value.blockSignals(False)
        self.spin_max_value.blockSignals(False)

        # Update timestamp
        collection.last_updated = datetime.now().isoformat()
        self._update_last_updated_display(collection)

        # Save to registry
        self.constant_raster_registry.save()

    def current_constant_raster_collection(
        self,
    ) -> typing.Optional[ConstantRasterCollection]:
        """Returns the constant raster collection based on the current selection in the combobox or None if invalid."""
        metadata_id = self.cbo_raster_type.itemData(self.cbo_raster_type.currentIndex())
        if not metadata_id:
            return None

        return self.constant_raster_registry.collection_by_id(metadata_id)

    def _on_model_component_selection_changed(
        self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection
    ):
        """Slot raised when the selection of model component changes."""
        selected_indexes = selected.indexes()
        if len(selected_indexes) == 0:
            return

        if not selected_indexes[0].isValid():
            return

        model = self._activities_model
        model_item = model.itemFromIndex(selected_indexes[0])
        if model_item is None:
            return

        model_identifier = model_item.uuid

        # Get current raster collection
        raster_collection = self.current_constant_raster_collection()
        if raster_collection is None:
            return

        # Reset current widget and load information
        current_config_widget = self.sw_component_container.currentWidget()

        # Check if it implements the raster interface
        if not isinstance(current_config_widget, ConstantRasterWidgetInterface):
            return

        # Raster component for the activity
        raster_component = raster_collection.component_by_id(model_identifier)
        component_created = False
        if raster_component is None:
            # Create a default one and add it to the collection
            raster_component = current_config_widget.create_raster_component(
                model_item.model_component
            )
            raster_collection.components.append(raster_component)
            component_created = True

        current_config_widget.raster_component = raster_component
        current_config_widget.reset()
        current_config_widget.load(raster_component)

        # Save if we created a new component
        if component_created:
            self.constant_raster_registry.save()

    def _load_component_into_widget(self, component: ConstantRasterComponent):
        """Load a component's values into the current configuration widget.

        :param component: The component to load
        """
        current_config_widget = self.sw_component_container.currentWidget()

        if not isinstance(current_config_widget, ConstantRasterWidgetInterface):
            return

        current_config_widget.raster_component = component
        current_config_widget.reset()
        current_config_widget.load(component)

    def _on_item_checked_changed(self, item: QtGui.QStandardItem):
        """Slot raised when an item's checkbox state changes."""
        is_checked = item.checkState() == QtCore.Qt.Checked

        # Update the component's enabled state based on checkbox state
        raster_collection = self.current_constant_raster_collection()
        if raster_collection is not None:
            component = raster_collection.component_by_id(item.uuid)

            if component:
                # Component exists, update its enabled state
                component.enabled = is_checked

                # If checked, load this component into the widget
                if is_checked:
                    self._load_component_into_widget(component)

            elif is_checked:
                # Component doesn't exist and item was just checked - create it
                metadata_id = self.cbo_raster_type.itemData(
                    self.cbo_raster_type.currentIndex()
                )
                current_config_widget = self.widget_by_identifier(metadata_id)

                if current_config_widget and hasattr(item, "model_component"):
                    new_component = current_config_widget.create_raster_component(
                        item.model_component
                    )
                    new_component.enabled = True  # It's checked
                    raster_collection.components.append(new_component)

                    # Load the new component into widget
                    self._load_component_into_widget(new_component)

            # Update timestamp
            raster_collection.last_updated = datetime.now().isoformat()
            self._update_last_updated_display(raster_collection)

            # Auto-calculate normalization range if unchecked
            if not self.grp_normalization_range.isChecked():
                self._auto_calculate_normalization_range()
            else:
                # Save to registry (auto-calculate saves internally)
                self.constant_raster_registry.save()

    def on_update_raster_component(self, raster_component: ConstantRasterComponent):
        """Slot raised when the component has been updated through the configuration widget."""
        raster_collection = self.current_constant_raster_collection()
        if raster_collection is not None:
            existing_component = raster_collection.component_by_id(
                raster_component.component_id
            )

            if existing_component is None:
                # Component not in collection, add it
                raster_collection.components.append(raster_component)

            # Update timestamp
            raster_collection.last_updated = datetime.now().isoformat()
            self._update_last_updated_display(raster_collection)

            # Auto-calculate normalization range if unchecked
            if not self.grp_normalization_range.isChecked():
                self._auto_calculate_normalization_range()
            else:
                # Save the registry to settings (auto-calculate saves internally)
                self.constant_raster_registry.save()

    def _ensure_checked_components_in_collection(self):
        """Ensure all checked items in the list have components in the collection.

        This method creates components for checked items that don't have them yet,
        and marks unchecked components as skipped.
        """
        # Get current model and collection
        model = self._activities_model
        raster_collection = self.current_constant_raster_collection()
        if raster_collection is None:
            return

        # Get the current configuration widget
        current_config_widget = self.sw_component_container.currentWidget()
        if not isinstance(current_config_widget, ConstantRasterWidgetInterface):
            return

        # Get the current value from the widget to use for ALL checked items
        current_value = None
        if (
            current_config_widget.raster_component
            and current_config_widget.raster_component.value_info
        ):
            current_value = current_config_widget.raster_component.value_info.absolute

        # First, build a set of all model item UUIDs for quick lookup
        model_uuids = set()
        for row in range(model.rowCount()):
            item = model.item(row)
            if item is not None:
                model_uuids.add(item.uuid)

        # Disable any components that don't correspond to current model items
        # (these are "orphaned" components from previous sessions)
        for component in raster_collection.components:
            if component.component_id not in model_uuids:
                component.enabled = False

        # Track items that were created/updated
        items_created = []
        items_updated = []

        # Iterate through all items in the model
        for row in range(model.rowCount()):
            item = model.item(row)
            if item is None:
                continue

            model_identifier = item.uuid
            is_checked = item.checkState() == QtCore.Qt.Checked

            # Find or create component for this item
            component = raster_collection.component_by_id(model_identifier)

            if is_checked:
                # Item is checked - ensure it has a component
                if component is None:
                    # Create a new component
                    component = current_config_widget.create_raster_component(
                        item.model_component
                    )
                    raster_collection.components.append(component)
                    items_created.append(item.text())
                else:
                    items_updated.append(item.text())

                # Link the model component if not already set
                if component.component is None:
                    component.component = item.model_component

                # Apply the current widget value to newly created components
                # Existing components keep their saved values
                if items_created and item.text() in items_created:
                    # This is a new component, apply current widget value
                    if current_value is not None and component.value_info:
                        component.value_info.absolute = current_value

                # Mark as enabled
                component.enabled = True
            else:
                # Item is unchecked - mark as disabled if it exists
                if component is not None:
                    component.enabled = False

        # Info message about what was done
        if items_created or items_updated:
            msg_parts = []
            if items_created:
                msg_parts.append(
                    self.tr("Created {count} component(s)").format(
                        count=len(items_created)
                    )
                )
            if items_updated:
                msg_parts.append(
                    self.tr("Updated {count} component(s)").format(
                        count=len(items_updated)
                    )
                )
            msg = " and ".join(msg_parts)

            if current_value is not None:
                self.message_bar.pushInfo(
                    self.tr("Components Configured"),
                    self.tr("{msg} with value: {value}").format(
                        msg=msg, value=current_value
                    ),
                )
            else:
                self.message_bar.pushWarning(
                    self.tr("Using Default Values"),
                    self.tr(
                        "{msg} with default value (0.0). Enter a value in the widget first."
                    ).format(msg=msg),
                )

            # Update timestamp when components are created or updated
            raster_collection.last_updated = datetime.now().isoformat()
            self._update_last_updated_display(raster_collection)

            # Auto-calculate normalization range if unchecked
            if not self.grp_normalization_range.isChecked():
                self._auto_calculate_normalization_range()

    def _get_pixel_size(self, target_crs: QgsCoordinateReferenceSystem = None) -> float:
        """Get pixel size using cascading fallback strategy.

        Priority order:
        1. NCS pathway resolution (from metadata for API layers, or from layer for local files)
        2. Snap layer resolution (if configured)

        :returns: Pixel size in map units
        :raises ValueError: If pixel size cannot be determined
        """
        # Try NCS pathways first
        pathways = settings_manager.get_all_ncs_pathways()
        if pathways:
            for pathway in pathways:
                try:
                    # For API layers (cplus://), use metadata
                    if pathway.layer_uuid:
                        default_layers = settings_manager.get_default_layers(
                            "ncs_pathway", as_dict=True
                        )
                        if pathway.layer_uuid in default_layers:
                            layer_metadata = default_layers[pathway.layer_uuid].get(
                                "metadata", {}
                            )
                            if (
                                "resolution" in layer_metadata
                                and layer_metadata["resolution"]
                            ):
                                resolution = layer_metadata["resolution"]
                                pixel_size_raw = (resolution[0] + resolution[1]) / 2.0

                                # Check if resolution is in degrees and target CRS is projected
                                unit = layer_metadata.get("unit", "")
                                is_geographic = layer_metadata.get(
                                    "is_geographic", False
                                )

                                if (
                                    unit == "degree" or is_geographic
                                ) and target_crs is not None:
                                    if target_crs.isGeographic():
                                        # Both in degrees, use as-is
                                        pixel_size = pixel_size_raw
                                    else:
                                        # Convert degrees to meters (approximate at equator)
                                        # 1 degree ≈ 111,320 meters
                                        pixel_size = pixel_size_raw * 111320.0
                                        log(
                                            f"Converted pixel size from {pixel_size_raw} degrees to {pixel_size} meters",
                                            info=True,
                                        )
                                else:
                                    pixel_size = pixel_size_raw

                                log(
                                    f"Using pixel size {pixel_size} from NCS pathway metadata: {pathway.name}",
                                    info=True,
                                )
                                return pixel_size
                    # For user-uploaded layers, try to load the layer
                    else:
                        pathway_layer = pathway.to_map_layer()
                        if pathway_layer and pathway_layer.isValid():
                            pixel_size_x = pathway_layer.rasterUnitsPerPixelX()
                            pixel_size_y = pathway_layer.rasterUnitsPerPixelY()

                            if pixel_size_x > 0 and pixel_size_y > 0:
                                pixel_size = (pixel_size_x + pixel_size_y) / 2.0
                                log(
                                    f"Using pixel size {pixel_size} from NCS pathway: {pathway.name}",
                                    info=True,
                                )
                                return pixel_size
                except Exception as e:
                    log(
                        f"Could not get pixel size from pathway {pathway.name}: {str(e)}",
                        info=False,
                    )
                    continue

        # Try snap layer as fallback
        snap_layer_path = settings_manager.get_value(
            Settings.SNAP_LAYER, default="", setting_type=str
        )
        if snap_layer_path:
            try:
                snap_layer = QgsRasterLayer(snap_layer_path, "snap_layer")
                if snap_layer.isValid():
                    pixel_size_x = snap_layer.rasterUnitsPerPixelX()
                    pixel_size_y = snap_layer.rasterUnitsPerPixelY()

                    if pixel_size_x > 0 and pixel_size_y > 0:
                        pixel_size = (pixel_size_x + pixel_size_y) / 2.0
                        log(f"Using pixel size {pixel_size} from snap layer", info=True)
                        return pixel_size
            except Exception as e:
                log(f"Could not get pixel size from snap layer: {str(e)}", info=False)

        # No pixel size available
        raise ValueError(
            self.tr(
                "Cannot determine pixel size. Please configure either:\n"
                "1. NCS pathways in the plugin, or\n"
                "2. Snap layer in Settings > Advanced"
            )
        )

    def _create_context(self) -> ConstantRasterContext:
        """Create a ConstantRasterContext from current map canvas and settings.

        :returns: Configured ConstantRasterContext
        """
        clip_to_studyarea = settings_manager.get_value(
            Settings.CLIP_TO_STUDYAREA, False
        )
        studyarea_path = settings_manager.get_value(Settings.STUDYAREA_PATH)
        use_aoi = (
            clip_to_studyarea and studyarea_path and os.path.exists(studyarea_path)
        )

        if use_aoi:
            aoi_layer = QgsVectorLayer(studyarea_path, "temp_aoi", "ogr")
            if aoi_layer.isValid():
                extent = aoi_layer.extent()
                crs = aoi_layer.crs()
            else:
                log(f"AOI layer invalid: {studyarea_path}", info=False)
                use_aoi = False

        if not use_aoi:
            # Fallback to map canvas extent
            try:
                canvas = iface.mapCanvas() if iface else None
            except Exception:
                canvas = None

            if canvas:
                extent = canvas.extent()
                crs = canvas.mapSettings().destinationCrs()
            else:
                # Last resort: use project CRS and default extent
                project = QgsProject.instance()
                crs = project.crs()
                # Default extent if no canvas
                extent = QgsRectangle(0, 0, 1000, 1000)
                log("Warning: No map canvas found, using default extent", info=False)

        # Get output directory from BASE_DIR setting
        base_dir = settings_manager.get_value(Settings.BASE_DIR)
        if not base_dir:
            # Fallback to temp directory if BASE_DIR not set
            base_dir = os.path.join(os.path.expanduser("~"), "cplus")

        output_dir = os.path.join(base_dir, "constant_rasters")

        pixel_size = self._get_pixel_size(target_crs=crs)

        return ConstantRasterContext(
            extent=extent,
            pixel_size=pixel_size,
            crs=crs,
            output_dir=output_dir,
        )

    def _on_raster_creation_completed(self, success: bool, message: str, count: int):
        """Handle completion of raster creation.

        :param success: True if creation was successful
        :param message: Message to display
        :param count: Number of rasters created
        """
        if success:
            self.message_bar.pushSuccess(self.tr("Success"), message)
        else:
            self.message_bar.pushWarning(self.tr("Warning"), message)

    def update_current_widget(self, current_view: bool = True):
        """Update current widget - creates constant rasters (if skip_raster is False) then saves the current collection in settings.

        This method validates the configuration and emits a signal for
        the caller to handle the actual raster creation.

        :param current_view: If True, create rasters for current view only;
                           if False, create for all constant raster types
        """
        current_raster_collection = self.current_constant_raster_collection()
        if current_raster_collection is None:
            self.message_bar.pushWarning(
                self.tr("No Collection"),
                self.tr("Please select a constant raster type first."),
            )
            return

        # Apply user-specified min/max values to the collection
        min_val = self.spin_min_value.value()
        max_val = self.spin_max_value.value()

        current_raster_collection.min_value = min_val
        current_raster_collection.max_value = max_val

        # Ensure all checked items have components in the collection
        self._ensure_checked_components_in_collection()

        # Update timestamp
        current_raster_collection.last_updated = datetime.now().isoformat()
        self._update_last_updated_display(current_raster_collection)

        # Save the state after creating/updating components
        self.constant_raster_registry.save()

        # Validate based on current_view flag
        if current_view:
            # For current view, check if current collection has enabled components
            enabled_components = current_raster_collection.enabled_components()
            if not enabled_components:
                self.message_bar.pushWarning(
                    self.tr("No Enabled Components"),
                    self.tr("Please check at least one activity and set its value."),
                )
                return
        else:
            # For all types, check if ANY collection has enabled components
            has_any_enabled = False
            for metadata_id in self.constant_raster_registry.metadata_ids():
                collection = self.constant_raster_registry.collection_by_id(metadata_id)
                if collection and not collection.skip_raster:
                    if collection.enabled_components():
                        has_any_enabled = True
                        break

            if not has_any_enabled:
                self.message_bar.pushWarning(
                    self.tr("No Enabled Components"),
                    self.tr(
                        "No enabled components found in any constant raster collection. Please check at least one activity and set its value."
                    ),
                )
                return

        # Create context for raster creation
        try:
            context = self._create_context()
        except ValueError as e:
            self.message_bar.pushWarning(self.tr("Cannot Create Context"), str(e))
            return

        # Get the metadata to extract input_range
        metadata_id = self.cbo_raster_type.itemData(self.cbo_raster_type.currentIndex())
        metadata = (
            self.constant_raster_registry.metadata_by_id(metadata_id)
            if metadata_id
            else None
        )
        input_range = metadata.input_range if metadata else (0.0, 100.0)

        # Emit signal for caller to handle raster creation
        self.create_rasters_requested.emit(
            context, current_raster_collection, input_range, metadata_id, current_view
        )

    def _save_dialog_state(self):
        """Save dialog-level state (raster type selection and normalization mode)."""
        # Save the constant raster type selection
        current_metadata_id = self.cbo_raster_type.itemData(
            self.cbo_raster_type.currentIndex()
        )
        if current_metadata_id:
            settings_manager.set_value(
                Settings.CONSTANT_RASTERS_DIALOG_ACTIVITY_TYPE, current_metadata_id
            )

            # Save normalization mode (manual/auto) per metadata_id
            auto_mode_key = f"constant_rasters_dialog/auto_mode/{current_metadata_id}"
            settings_manager.set_value(
                auto_mode_key, not self.grp_normalization_range.isChecked()
            )

    def _restore_dialog_state(self):
        """Restore dialog-level state (raster type selection)."""
        # Load activities (the only model type supported)
        self.load_activities()

    def _restore_ui_state(self):
        """Restore UI state from saved components (checkboxes, normalization range)."""
        # First restore dialog-level state (which tab, which raster type)
        self._restore_dialog_state()

        # Now restore component-level state for the current collection
        current_collection = self.current_constant_raster_collection()
        if current_collection is None:
            return

        # Restore normalization mode (manual/auto) for current metadata_id
        current_metadata_id = self.cbo_raster_type.itemData(
            self.cbo_raster_type.currentIndex()
        )
        if current_metadata_id:
            auto_mode_key = f"constant_rasters_dialog/auto_mode/{current_metadata_id}"
            is_auto_mode = settings_manager.get_value(
                auto_mode_key, default=False, setting_type=bool
            )

            # Set checkbox state (checked = manual, unchecked = auto)
            self.grp_normalization_range.blockSignals(True)
            self.grp_normalization_range.setChecked(not is_auto_mode)
            self.grp_normalization_range.blockSignals(False)

            # Enable/disable spinboxes based on mode
            self.spin_min_value.setEnabled(not is_auto_mode)
            self.spin_max_value.setEnabled(not is_auto_mode)

        # Restore normalization range for currently selected collection
        self.spin_min_value.blockSignals(True)
        self.spin_max_value.blockSignals(True)
        self.spin_min_value.setValue(current_collection.min_value)
        self.spin_max_value.setValue(current_collection.max_value)
        self.spin_min_value.blockSignals(False)
        self.spin_max_value.blockSignals(False)

        # Update last updated display
        self._update_last_updated_display(current_collection)

        # Restore checked items for activities
        activity_collection = self.constant_raster_registry.collection_by_id(
            YEARS_EXPERIENCE_ACTIVITY_ID
        )
        if activity_collection:
            first_activity_index = None
            for row in range(self._activities_model.rowCount()):
                item = self._activities_model.item(row)
                if item is None:
                    continue

                component = activity_collection.component_by_id(item.uuid)
                if component and component.enabled:
                    self._activities_model.blockSignals(True)
                    item.setCheckState(QtCore.Qt.Checked)
                    self._activities_model.blockSignals(False)
                    if first_activity_index is None:
                        first_activity_index = self._activities_model.indexFromItem(
                            item
                        )

            if first_activity_index is not None:
                self.lst_activities.setCurrentIndex(first_activity_index)

    def _update_custom_type_button_states(self):
        """Update Edit and Delete button states based on current metadata's user_defined flag."""
        current_index = self.cbo_raster_type.currentIndex()
        if current_index < 0:
            self.btn_edit_custom_type.setEnabled(False)
            self.btn_delete_custom_type.setEnabled(False)
            return

        metadata_id = self.cbo_raster_type.itemData(current_index)
        if not metadata_id:
            self.btn_edit_custom_type.setEnabled(False)
            self.btn_delete_custom_type.setEnabled(False)
            return

        metadata = self.constant_raster_registry.metadata_by_id(metadata_id)
        if metadata and metadata.user_defined:
            self.btn_edit_custom_type.setEnabled(True)
            self.btn_delete_custom_type.setEnabled(True)
            self.btn_edit_custom_type.setToolTip(
                self.tr("Edit the selected custom type")
            )
            self.btn_delete_custom_type.setToolTip(
                self.tr("Delete the selected custom type")
            )
        else:
            self.btn_edit_custom_type.setEnabled(False)
            self.btn_delete_custom_type.setEnabled(False)
            self.btn_edit_custom_type.setToolTip(self.tr("Cannot edit built-in types"))
            self.btn_delete_custom_type.setToolTip(
                self.tr("Cannot delete built-in types")
            )

    def on_add_custom_type_clicked(self):
        """Handle Add Custom Type button click."""
        # Get existing type names for validation
        existing_names = [
            self.constant_raster_registry.metadata_by_id(meta_id).display_name
            for meta_id in self.constant_raster_registry.metadata_ids()
            if self.constant_raster_registry.metadata_by_id(meta_id)
        ]

        # Show dialog
        dialog = CustomTypeDefinitionDialog(
            parent=self, edit_mode=False, existing_types=existing_names
        )

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            type_def = dialog.get_type_definition()

            # Generate unique ID from type name (like "training_hours")
            base_id = clean_filename(type_def[NAME_ATTRIBUTE].lower().replace(" ", "_"))

            # Ensure uniqueness by checking existing IDs
            metadata_id = base_id
            counter = 2
            while metadata_id in self.constant_raster_registry.metadata_ids():
                metadata_id = f"{base_id}_{counter}"
                counter += 1

            # Create metadata
            metadata = GenericNumericWidget.create_metadata(
                metadata_id=metadata_id,
                component_type=ModelComponentType.ACTIVITY,
                display_name=type_def[NAME_ATTRIBUTE],
                min_value=type_def[MIN_VALUE_ATTRIBUTE_KEY],
                max_value=type_def[MAX_VALUE_ATTRIBUTE_KEY],
                user_defined=True,
            )

            # Register metadata
            if self.constant_raster_registry.add_metadata(metadata):
                # Store custom type definition
                custom_type_def = {
                    ID_ATTRIBUTE: metadata_id,
                    NAME_ATTRIBUTE: type_def[NAME_ATTRIBUTE],
                    MIN_VALUE_ATTRIBUTE_KEY: type_def[MIN_VALUE_ATTRIBUTE_KEY],
                    MAX_VALUE_ATTRIBUTE_KEY: type_def[MAX_VALUE_ATTRIBUTE_KEY],
                    DEFAULT_VALUE_ATTRIBUTE_KEY: type_def[DEFAULT_VALUE_ATTRIBUTE_KEY],
                    COMPONENT_TYPE_ATTRIBUTE: type_def[COMPONENT_TYPE_ATTRIBUTE],
                }
                self.constant_raster_registry.add_custom_type_definition(
                    custom_type_def
                )

                # Create and register widget
                widget = GenericNumericWidget(
                    label=type_def[NAME_ATTRIBUTE],
                    metadata_id=metadata_id,
                    min_value=type_def[MIN_VALUE_ATTRIBUTE_KEY],
                    max_value=type_def[MAX_VALUE_ATTRIBUTE_KEY],
                    default_value=type_def[DEFAULT_VALUE_ATTRIBUTE_KEY],
                    parent=self.sw_component_container,
                )
                self.register_widget(metadata_id, widget)

                # Add to dropdown
                self.cbo_raster_type.addItem(type_def[NAME_ATTRIBUTE], metadata_id)

                # Select the new type
                new_index = self.cbo_raster_type.findData(metadata_id)
                if new_index >= 0:
                    self.cbo_raster_type.setCurrentIndex(new_index)

                # Save
                self.constant_raster_registry.save()

                self.message_bar.pushSuccess(
                    self.tr("Success"),
                    self.tr(
                        f"Custom type '{type_def[NAME_ATTRIBUTE]}' created successfully."
                    ),
                )

    def on_edit_custom_type_clicked(self):
        """Handle Edit Custom Type button click."""
        current_index = self.cbo_raster_type.currentIndex()
        if current_index < 0:
            return

        metadata_id = self.cbo_raster_type.itemData(current_index)
        if not metadata_id:
            return

        metadata = self.constant_raster_registry.metadata_by_id(metadata_id)
        if not metadata or not metadata.user_defined:
            return

        # Get custom type definition
        type_def = self.constant_raster_registry.get_custom_type_definition(metadata_id)
        if not type_def:
            self.message_bar.pushWarning(
                self.tr("Error"),
                self.tr("Could not load custom type definition."),
            )
            return

        # Get existing type names for validation (excluding current)
        existing_names = [
            self.constant_raster_registry.metadata_by_id(meta_id).display_name
            for meta_id in self.constant_raster_registry.metadata_ids()
            if (
                self.constant_raster_registry.metadata_by_id(meta_id)
                and meta_id != metadata_id
            )
        ]

        # Show dialog in edit mode
        dialog = CustomTypeDefinitionDialog(
            parent=self, edit_mode=True, existing_types=existing_names
        )
        dialog.set_values(type_def)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            updated_def = dialog.get_type_definition()

            # Update metadata
            metadata.display_name = updated_def[NAME_ATTRIBUTE]
            metadata.input_range = (
                updated_def[MIN_VALUE_ATTRIBUTE_KEY],
                updated_def[MAX_VALUE_ATTRIBUTE_KEY],
            )

            # Update custom type definition
            updated_type_def = {
                ID_ATTRIBUTE: metadata_id,
                NAME_ATTRIBUTE: updated_def[NAME_ATTRIBUTE],
                MIN_VALUE_ATTRIBUTE_KEY: updated_def[MIN_VALUE_ATTRIBUTE_KEY],
                MAX_VALUE_ATTRIBUTE_KEY: updated_def[MAX_VALUE_ATTRIBUTE_KEY],
                DEFAULT_VALUE_ATTRIBUTE_KEY: updated_def[DEFAULT_VALUE_ATTRIBUTE_KEY],
                COMPONENT_TYPE_ATTRIBUTE: updated_def[COMPONENT_TYPE_ATTRIBUTE],
            }
            self.constant_raster_registry.update_custom_type_definition(
                metadata_id, updated_type_def
            )

            # Update dropdown item
            self.cbo_raster_type.setItemText(current_index, updated_def[NAME_ATTRIBUTE])

            # Update widget (recreate it)
            widget = GenericNumericWidget(
                label=updated_def[NAME_ATTRIBUTE],
                metadata_id=metadata_id,
                min_value=updated_def[MIN_VALUE_ATTRIBUTE_KEY],
                max_value=updated_def[MAX_VALUE_ATTRIBUTE_KEY],
                default_value=updated_def[DEFAULT_VALUE_ATTRIBUTE_KEY],
                parent=self.sw_component_container,
            )

            # Replace widget in stacked widget
            old_widget_index = self._registered_component_widgets.get(metadata_id)
            if old_widget_index is not None:
                old_widget = self.sw_component_container.widget(old_widget_index)
                if old_widget:
                    self.sw_component_container.removeWidget(old_widget)
                    new_widget_index = self.sw_component_container.insertWidget(
                        old_widget_index, widget
                    )
                    old_widget.deleteLater()
                    self._registered_component_widgets[metadata_id] = new_widget_index
            else:
                # Fallback: register as new widget
                new_widget_index = self.sw_component_container.addWidget(widget)
                self._registered_component_widgets[metadata_id] = new_widget_index

            # Reconnect widget update signal
            if hasattr(widget, "update_requested"):
                widget.update_requested.connect(self.on_update_raster_component)

            # Show updated widget
            self.show_widget(metadata_id)

            # Reload currently selected activity's component into the new widget
            current_activity_index = self.lst_activities.currentIndex()
            if current_activity_index.isValid():
                model_item = self._activities_model.itemFromIndex(
                    current_activity_index
                )
                if model_item:
                    model_identifier = model_item.uuid
                    collection = self.constant_raster_registry.collection_by_id(
                        metadata_id
                    )
                    if collection:
                        raster_component = collection.component_by_id(model_identifier)
                        if raster_component:
                            widget.raster_component = raster_component
                            widget.reset()
                            widget.load(raster_component)

            # Save
            self.constant_raster_registry.save()

            self.message_bar.pushSuccess(
                self.tr("Success"),
                self.tr(f"Custom type '{updated_def['name']}' updated successfully."),
            )

    def on_delete_custom_type_clicked(self):
        """Handle Delete Custom Type button click."""
        current_index = self.cbo_raster_type.currentIndex()
        if current_index < 0:
            return

        metadata_id = self.cbo_raster_type.itemData(current_index)
        if not metadata_id:
            return

        metadata = self.constant_raster_registry.metadata_by_id(metadata_id)
        if not metadata or not metadata.user_defined:
            return

        # Confirmation dialog
        reply = QtWidgets.QMessageBox.question(
            self,
            self.tr("Confirm Deletion"),
            self.tr(
                f"Are you sure you want to delete the custom type '{metadata.display_name}'?\n\n"
                "This will remove the type definition and all associated data."
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        # Remove from dropdown first
        self.cbo_raster_type.removeItem(current_index)

        # Remove widget
        widget_index = self._registered_component_widgets.pop(metadata_id, None)
        if widget_index is not None:
            widget = self.sw_component_container.widget(widget_index)
            if widget:
                self.sw_component_container.removeWidget(widget)
                widget.deleteLater()

        # Remove from registry
        self.constant_raster_registry.remove_metadata(metadata_id)
        self.constant_raster_registry.remove_custom_type_definition(metadata_id)

        # Save
        self.constant_raster_registry.save()

        self.message_bar.pushSuccess(
            self.tr("Success"),
            self.tr(f"Custom type '{metadata.display_name}' deleted successfully."),
        )

    def close(self):
        """Handle close button click."""
        # Save component state
        self.constant_raster_registry.save()

        # Save dialog-level state (which tab, which raster type)
        self._save_dialog_state()

        # Close the dialog
        self.reject()
