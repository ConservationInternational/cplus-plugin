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
from qgis.gui import QgsMessageBar
from qgis.utils import iface

from ..conf import settings_manager, Settings
from ..models.base import ModelComponentType
from ..models.constant_raster import (
    ConstantRasterCollection,
    ConstantRasterComponent,
    ConstantRasterContext,
    ConstantRasterMetadata,
)
from ..lib.constant_raster import (
    constant_raster_registry,
)
from ..definitions.defaults import (
    ICON_PATH,
    YEARS_EXPERIENCE_ACTIVITY_ID,
)
from .component_item_model import ActivityItemModel
from .constant_raster_widgets import (
    ConstantRasterWidgetInterface,
    YearsExperienceWidget,
)
from ..utils import log, tr


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
        self.setWindowTitle(tr("Constant Rasters Manager"))

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
            "Define constant raster parameters for activities. "
            "Configure input values (e.g., years of experience), "
            "specify the output normalization range, and create rasters clipped to your Area of Interest."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        main_layout.addWidget(info_banner)

        # Top section: Description + Raster Type
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Constant raster type selection
        raster_type_widget = QtWidgets.QWidget()
        raster_type_layout = QtWidgets.QHBoxLayout(raster_type_widget)
        raster_type_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_raster_type = QtWidgets.QLabel("Constant raster type:")
        self.cbo_raster_type = QtWidgets.QComboBox()
        self.cbo_raster_type.setMinimumWidth(200)
        raster_type_layout.addWidget(self.lbl_raster_type)
        raster_type_layout.addWidget(self.cbo_raster_type)
        raster_type_layout.addStretch()
        top_layout.addWidget(raster_type_widget)

        main_layout.addWidget(top_widget)

        # Message bar for feedback
        self.message_bar = QgsMessageBar()
        main_layout.addWidget(self.message_bar)

        # Middle section: Two-column layout with splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Left column - Component list
        self._left_group = QtWidgets.QGroupBox()
        self._left_group.setTitle("Activities")
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
        blank_widget = QtWidgets.QLabel("Select a component to configure")
        blank_widget.setAlignment(QtCore.Qt.AlignCenter)
        blank_widget.setStyleSheet("color: gray; padding: 20px;")
        self.sw_component_container.addWidget(blank_widget)

        right_layout.addWidget(self.sw_component_container, 1)

        # Last updated timestamp label
        self.lbl_last_updated = QtWidgets.QLabel("")
        self.lbl_last_updated.setStyleSheet(
            "color: gray; font-size: 9pt; font-style: italic;"
        )
        self.lbl_last_updated.setAlignment(QtCore.Qt.AlignLeft)
        self.lbl_last_updated.setContentsMargins(5, 5, 5, 5)
        right_layout.addWidget(self.lbl_last_updated)

        # Normalization range (collapsible)
        # This allows users to remap the normalized output to any range they want
        norm_group = QtWidgets.QGroupBox("Normalization Range")
        norm_group.setCheckable(True)
        norm_group.setChecked(True)
        norm_group.setToolTip(
            "Adjust the normalization range for normalized values. Can be any range (e.g., 0-1, 0-100, etc.)"
        )
        norm_layout = QtWidgets.QFormLayout(norm_group)
        self.spin_min_value = QtWidgets.QDoubleSpinBox()
        self.spin_min_value.setRange(0.0, sys.float_info.max)
        self.spin_min_value.setDecimals(3)
        self.spin_min_value.setSingleStep(0.1)
        self.spin_min_value.setValue(0.0)
        self.spin_min_value.setToolTip("Minimum output value for the raster")
        self.spin_max_value = QtWidgets.QDoubleSpinBox()
        self.spin_max_value.setRange(0.0, sys.float_info.max)
        self.spin_max_value.setDecimals(3)
        self.spin_max_value.setSingleStep(0.1)
        self.spin_max_value.setValue(0.0)
        self.spin_max_value.setToolTip("Maximum output value for the raster")
        norm_layout.addRow("Minimum", self.spin_min_value)
        norm_layout.addRow("Maximum", self.spin_max_value)
        right_layout.addWidget(norm_group)

        splitter.addWidget(right_widget)

        # Set initial splitter sizes (40% left, 60% right)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter, 1)

        # Bottom: Action buttons
        button_layout = QtWidgets.QHBoxLayout()

        # Create tool button with dropdown menu for raster creation
        self.btn_create_current = QtWidgets.QToolButton()
        self.btn_create_current.setText("Create Rasters")
        self.btn_create_current.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.btn_create_current.setToolTip(
            "Create constant rasters for current view or all types"
        )

        # Create menu for the button
        create_menu = QtWidgets.QMenu(self)

        # Add menu actions
        self.action_create_current = create_menu.addAction("Create - Current View")
        self.action_create_current.triggered.connect(
            lambda: self.update_current_widget(current_view=True)
        )

        self.action_create_all = create_menu.addAction(
            "Create - All Constant Raster Types"
        )
        self.action_create_all.triggered.connect(
            lambda: self.update_current_widget(current_view=False)
        )

        # Set menu to button
        self.btn_create_current.setMenu(create_menu)

        # Set default action (triggered when button clicked directly)
        self.btn_create_current.setDefaultAction(self.action_create_current)

        self.btn_close = QtWidgets.QPushButton("Close")
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
                "Configuration Error",
                f"No widget defined for metadata ID '{metadata_id}'. Please contact the plugin developer.",
            )
            return

        self.sw_component_container.setCurrentIndex(
            self._registered_component_widgets[metadata_id]
        )

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

        # Load activity model
        self._activities_model = ActivityItemModel(
            load_pathways=False, is_checkable=True
        )
        self.lst_activities.setModel(self._activities_model)
        for activity in settings_manager.get_all_activities():
            self._activities_model.add_activity(activity)

        # Connect to the view's selection model, not the model itself
        self.lst_activities.selectionModel().selectionChanged.connect(
            self._on_model_component_selection_changed
        )

        # Connections
        self.cbo_raster_type.currentIndexChanged.connect(
            self.on_raster_type_selection_changed
        )
        # Note: btn_create_current uses menu actions, not direct clicked connection
        self.btn_close.clicked.connect(self.close)

        # Connect model itemChanged signals to save checkbox states
        self._activities_model.itemChanged.connect(self._on_item_checked_changed)

        # Connect normalization range spinboxes to save the values to the collection
        self.spin_min_value.valueChanged.connect(self.on_normalization_range_changed)
        self.spin_max_value.valueChanged.connect(self.on_normalization_range_changed)

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

            # Update min/max values from the collection
            collection = self.constant_raster_registry.collection_by_id(metadata_id)
            if collection is not None:
                # Block signals temporarily to avoid triggering save while loading
                self.spin_min_value.blockSignals(True)
                self.spin_max_value.blockSignals(True)

                # Sanity check: if the range is invalid, reset to defaults
                if collection.min_value >= collection.max_value:
                    collection.min_value = 0.0
                    collection.max_value = 100.0

                self.spin_min_value.setValue(collection.min_value)
                self.spin_max_value.setValue(collection.max_value)

                self.spin_min_value.blockSignals(False)
                self.spin_max_value.blockSignals(False)

                # Update button states based on skip_raster flag
                self._update_create_button_states(collection)

                # Update last updated timestamp display
                self._update_last_updated_display(collection)

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
                "Current view disabled - this constant raster type does not require rasters"
            )
        else:
            self.action_create_current.setEnabled(True)
            self.action_create_current.setToolTip("Create rasters for the current view")

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
            self.lbl_last_updated.setText(f"Last updated: {formatted_time}")
        except (ValueError, AttributeError):
            # If parsing fails, show the raw timestamp
            self.lbl_last_updated.setText(f"Last updated: {collection.last_updated}")

    def on_normalization_range_changed(self, value: float):
        """Slot raised when normalization range spinbox values change."""
        collection = self.current_constant_raster_collection()
        if collection is not None:
            min_val = self.spin_min_value.value()
            max_val = self.spin_max_value.value()

            collection.min_value = min_val
            collection.max_value = max_val

            metadata_id = self.cbo_raster_type.itemData(
                self.cbo_raster_type.currentIndex()
            )
            metadata = self.constant_raster_registry.metadata_by_id(metadata_id)

            try:
                collection.validate(metadata)
            except ValueError as e:
                self.message_bar.pushWarning("Invalid Range", str(e))
                return

            # Update timestamp
            collection.last_updated = datetime.now().isoformat()
            self._update_last_updated_display(collection)

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

            # Save to registry
            self.constant_raster_registry.save()

    def on_update_raster_component(self, raster_component: ConstantRasterComponent):
        """Slot raised when the component has been updated through the configuration widget."""
        # Get current collection and ensure the component is in it
        raster_collection = self.current_constant_raster_collection()
        if raster_collection is not None:
            # Check if component is already in collection by UUID (safer than using 'in')
            existing_component = raster_collection.component_by_id(
                raster_component.component_id
            )

            if existing_component is None:
                # Component not in collection, add it
                raster_collection.components.append(raster_component)

            # Update timestamp
            raster_collection.last_updated = datetime.now().isoformat()
            self._update_last_updated_display(raster_collection)

        # Save the registry to settings
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
        if hasattr(current_config_widget, "sb_experience"):
            current_value = current_config_widget.sb_experience.value()

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
                msg_parts.append(f"Created {len(items_created)} component(s)")
            if items_updated:
                msg_parts.append(f"Updated {len(items_updated)} component(s)")
            msg = " and ".join(msg_parts)

            if current_value is not None:
                self.message_bar.pushInfo(
                    "Components Configured", f"{msg} with value: {current_value}"
                )
            else:
                self.message_bar.pushWarning(
                    "Using Default Values",
                    f"{msg} with default value (0.0). Enter a value in the widget first.",
                )

            # Update timestamp when components are created or updated
            raster_collection.last_updated = datetime.now().isoformat()
            self._update_last_updated_display(raster_collection)

        # NOTE: We don't call normalize() here anymore because:
        # 1. The user specifies min/max values explicitly in the UI
        # 2. Auto-normalizing would override user values
        # 3. With only one component, min==max causes incorrect 0.5 fallback

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
            "Cannot determine pixel size. Please configure either:\n"
            "1. NCS pathways in the plugin, or\n"
            "2. Snap layer in Settings > Advanced"
        )

    def _create_context(self) -> ConstantRasterContext:
        """Create a ConstantRasterContext from current map canvas and settings.

        :returns: Configured ConstantRasterContext
        """
        # Try to get extent from AOI/Study Area first
        studyarea_path = settings_manager.get_value(Settings.STUDYAREA_PATH)
        use_aoi = studyarea_path and os.path.exists(studyarea_path)

        if use_aoi:
            # Use AOI extent
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
            self.message_bar.pushSuccess("Success", message)
        else:
            self.message_bar.pushWarning("Warning", message)

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
                "No Collection", "Please select a constant raster type first."
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
                    "No Enabled Components",
                    "Please check at least one activity and set its value.",
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
                    "No Enabled Components",
                    "No enabled components found in any constant raster collection. Please check at least one activity and set its value.",
                )
                return

        # Create context for raster creation
        try:
            context = self._create_context()
        except ValueError as e:
            self.message_bar.pushWarning("Cannot Create Context", str(e))
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
        """Save dialog-level state (raster type selection)."""
        # Save the constant raster type selection
        current_metadata_id = self.cbo_raster_type.itemData(
            self.cbo_raster_type.currentIndex()
        )
        if current_metadata_id:
            settings_manager.set_value(
                Settings.CONSTANT_RASTERS_DIALOG_ACTIVITY_TYPE, current_metadata_id
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

        # Restore normalization range for currently selected collection
        self.spin_min_value.blockSignals(True)
        self.spin_max_value.blockSignals(True)
        self.spin_min_value.setValue(current_collection.min_value)
        self.spin_max_value.setValue(current_collection.max_value)
        self.spin_min_value.blockSignals(False)
        self.spin_max_value.blockSignals(False)

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

    def close(self):
        """Handle close button click."""
        # Save component state
        self.constant_raster_registry.save()

        # Save dialog-level state (which tab, which raster type)
        self._save_dialog_state()

        # Close the dialog
        self.reject()
