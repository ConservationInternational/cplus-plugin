# -*- coding: utf-8 -*-
"""
Dialog for managing constant rasters for NCS pathways and activities.
"""

import os
import typing
from pathlib import Path

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsFeedback,
    QgsSettings,
    QgsVectorLayer,
    QgsRasterLayer,
)
from qgis.gui import QgsGui, QgsMessageBar

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
    ConstantRasterProcessingUtils,
)
from ..definitions.defaults import (
    ICON_PATH,
    YEARS_EXPERIENCE_PATHWAY_ID,
    YEARS_EXPERIENCE_ACTIVITY_ID,
)
from .component_item_model import NcsPathwayItemModel, ActivityItemModel
from .constant_raster_widgets import (
    ConstantRasterWidgetInterface,
    YearsExperienceWidget,
)
from ..utils import log, FileUtils


class ConstantRastersManagerDialog(QtWidgets.QDialog):
    """Dialog for managing constant rasters."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._raster_registry = constant_raster_registry

        # Registry for configuration widgets
        self._registered_component_widgets = {}

        # Create UI
        self._create_ui()

        # Initialize
        self._initialize()

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
            "Define constant raster parameters for NCS pathways and activities. "
            "Configure input values (e.g., years of experience), "
            "specify the output normalization range, and create rasters clipped to your Area of Interest."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        main_layout.addWidget(info_banner)

        # Top section: Model Type + Description + Raster Type
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Model type selection (horizontal radio buttons)
        model_type_widget = QtWidgets.QWidget()
        model_type_layout = QtWidgets.QHBoxLayout(model_type_widget)
        model_type_layout.setContentsMargins(0, 0, 0, 0)
        model_type_label = QtWidgets.QLabel("<b>Model Type</b>")
        self.rb_pathway = QtWidgets.QRadioButton("NCS Pathway")
        self.rb_pathway.setChecked(True)
        self.rb_activity = QtWidgets.QRadioButton("Activity")
        model_type_layout.addWidget(model_type_label)
        model_type_layout.addWidget(self.rb_pathway)
        model_type_layout.addWidget(self.rb_activity)
        model_type_layout.addStretch()
        top_layout.addWidget(model_type_widget)

        # Description
        self.lbl_description = QtWidgets.QLabel(
            "<b>Description:</b> Constant rasters for NCS pathways"
        )
        self.lbl_description.setWordWrap(True)
        self.lbl_description.setStyleSheet("padding: 5px 0px;")
        top_layout.addWidget(self.lbl_description)

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

        # Middle section: Two-column layout
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Left column - Component list
        self._left_group = QtWidgets.QGroupBox()
        self._left_group.setTitle("NCS Pathways")
        left_layout = QtWidgets.QVBoxLayout(self._left_group)

        self.sw_model_type_container = QtWidgets.QStackedWidget()
        self.lst_pathways = QtWidgets.QListView()
        self.lst_activities = QtWidgets.QListView()
        self.sw_model_type_container.addWidget(self.lst_pathways)
        self.sw_model_type_container.addWidget(self.lst_activities)
        left_layout.addWidget(self.sw_model_type_container)

        content_layout.addWidget(self._left_group, 1)

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

        # Output range for normalization (collapsible)
        # This allows users to remap the normalized output to any range they want
        norm_group = QtWidgets.QGroupBox("Output Range (remapping)")
        norm_group.setCheckable(True)
        norm_group.setChecked(True)
        norm_group.setToolTip(
            "Adjust the output range for normalized values. Can be any range (e.g., 0-1, 0-100, etc.)"
        )
        norm_layout = QtWidgets.QFormLayout(norm_group)
        self.spin_min_value = QtWidgets.QDoubleSpinBox()
        self.spin_min_value.setRange(0.0, 9999999.0)
        self.spin_min_value.setDecimals(4)
        self.spin_min_value.setSingleStep(0.1)
        self.spin_min_value.setValue(0.0)
        self.spin_min_value.setToolTip("Minimum output value for the raster")
        self.spin_max_value = QtWidgets.QDoubleSpinBox()
        self.spin_max_value.setRange(0.0, 9999999.0)
        self.spin_max_value.setDecimals(4)
        self.spin_max_value.setSingleStep(0.1)
        self.spin_max_value.setValue(100.0)
        self.spin_max_value.setToolTip("Maximum output value for the raster")
        norm_layout.addRow("Minimum", self.spin_min_value)
        norm_layout.addRow("Maximum", self.spin_max_value)
        right_layout.addWidget(norm_group)

        content_layout.addWidget(right_widget, 1)
        main_layout.addWidget(content_widget, 1)

        # Bottom: Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.btn_create_current = QtWidgets.QPushButton("Create Rasters - Current View")
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

    def show_configuration_widget(self, metadata_id: str):
        """Show widget corresponding to the given metadata ID or a blank widget if not found.

        :param metadata_id: Metadata ID to show widget for
        """
        if metadata_id not in self._registered_component_widgets:
            # Show the blank widget (index 0)
            self.sw_component_container.setCurrentIndex(0)
            return

        self.sw_component_container.setCurrentIndex(
            self._registered_component_widgets[metadata_id]
        )

    def _register_sample_metadata(self):
        """Register sample metadata for demonstration.

        This creates "Years of Experience" metadata types for both
        NCS pathways and activities.
        In production, metadata would be loaded from settings or defined elsewhere.
        """
        # Register for NCS Pathways
        if YEARS_EXPERIENCE_PATHWAY_ID not in self._raster_registry.metadata_ids():
            collection_pathway = ConstantRasterCollection(
                min_value=0.0,
                max_value=100.0,  # Output range: 0-100
                components=[],
            )

            metadata_pathway = ConstantRasterMetadata(
                id=YEARS_EXPERIENCE_PATHWAY_ID,
                display_name="Years of Experience",
                fcollection=collection_pathway,
                deserializer=None,
                component_type=ModelComponentType.NCS_PATHWAY,
                input_range=(0.0, 100.0),  # Years of experience: 0-100 years
            )
            self._raster_registry.register_metadata(metadata_pathway)

        # Register for Activities
        if YEARS_EXPERIENCE_ACTIVITY_ID not in self._raster_registry.metadata_ids():
            collection_activity = ConstantRasterCollection(
                min_value=0.0,
                max_value=100.0,  # Output range: 0-100
                components=[],
            )

            metadata_activity = ConstantRasterMetadata(
                id=YEARS_EXPERIENCE_ACTIVITY_ID,
                display_name="Years of Experience",
                fcollection=collection_activity,
                deserializer=None,
                component_type=ModelComponentType.ACTIVITY,
                input_range=(0.0, 100.0),  # Years of experience: 0-100 years
            )
            self._raster_registry.register_metadata(metadata_activity)

    def _initialize(self):
        """Initialize UI components and connections."""
        # Register sample metadata if not already registered
        self._register_sample_metadata()

        # Load saved state from settings
        self._raster_registry.load()

        # Register widgets for known constant rasters
        metadata_ids = self._raster_registry.metadata_ids()
        if YEARS_EXPERIENCE_PATHWAY_ID in metadata_ids:
            experience_widget_pathway = YearsExperienceWidget()
            self.register_widget(YEARS_EXPERIENCE_PATHWAY_ID, experience_widget_pathway)

        if YEARS_EXPERIENCE_ACTIVITY_ID in metadata_ids:
            experience_widget_activity = YearsExperienceWidget()
            self.register_widget(
                YEARS_EXPERIENCE_ACTIVITY_ID, experience_widget_activity
            )

        # Load item models
        self._pathways_model = NcsPathwayItemModel(is_checkable=True)
        self.lst_pathways.setModel(self._pathways_model)
        for pathway in settings_manager.get_all_ncs_pathways():
            self._pathways_model.add_ncs_pathway(pathway)

        # Connect to the view's selection model, not the model itself
        self.lst_pathways.selectionModel().selectionChanged.connect(
            self._on_model_component_selection_changed
        )

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
        self.rb_pathway.toggled.connect(self.on_pathway_type_selected)
        self.rb_activity.toggled.connect(self.on_activity_type_selected)
        self.btn_create_current.clicked.connect(
            self.on_create_constant_raster_current_view
        )
        self.btn_close.clicked.connect(self._on_close)

        # Connect model itemChanged signals to save checkbox states
        self._pathways_model.itemChanged.connect(self._on_item_checked_changed)
        self._activities_model.itemChanged.connect(self._on_item_checked_changed)

        # Connect output range spinboxes to save the values to the collection
        self.spin_min_value.valueChanged.connect(self.on_output_range_changed)
        self.spin_max_value.valueChanged.connect(self.on_output_range_changed)

        # Restore UI state from saved components
        self._restore_ui_state()

    def on_pathway_type_selected(self, checked: bool):
        """Slot raised when pathway radio button is selected."""
        if not checked:
            return

        # Save previous state before switching
        self._save_dialog_state()

        self.sw_model_type_container.setCurrentIndex(0)
        self._left_group.setTitle("NCS Pathways")
        self.lbl_description.setText(
            "<b>Description:</b> Constant rasters for NCS pathways"
        )

        # Get metadata for pathways
        pathway_metadatas = self._raster_registry.metadata_by_component_type(
            ModelComponentType.NCS_PATHWAY
        )
        self.cbo_raster_type.clear()
        for metadata in pathway_metadatas:
            self.cbo_raster_type.addItem(metadata.display_name, metadata.id)

        # Try to restore the previously selected pathway raster type
        settings = QgsSettings()
        settings.beginGroup("cplus/constant_rasters_dialog")
        pathway_raster_type = settings.value("pathway_raster_type", None)
        settings.endGroup()

        # Select the saved raster type if available, otherwise first item
        if pathway_raster_type:
            for i in range(self.cbo_raster_type.count()):
                if self.cbo_raster_type.itemData(i) == pathway_raster_type:
                    self.cbo_raster_type.setCurrentIndex(i)
                    break
        elif self.cbo_raster_type.count() > 0:
            self.cbo_raster_type.setCurrentIndex(0)

        # Auto-select first checked pathway to load its values into widget
        for row in range(self._pathways_model.rowCount()):
            item = self._pathways_model.item(row)
            if item and item.checkState() == QtCore.Qt.Checked:
                index = self._pathways_model.indexFromItem(item)
                self.lst_pathways.setCurrentIndex(index)
                break

    def on_activity_type_selected(self, checked: bool):
        """Slot raised when activity radio button is selected."""
        if not checked:
            return

        # Save previous state before switching
        self._save_dialog_state()

        self.sw_model_type_container.setCurrentIndex(1)
        self._left_group.setTitle("Activities")
        self.lbl_description.setText(
            "<b>Description:</b> Constant rasters for activities"
        )

        # Get metadata for activities
        activity_metadatas = self._raster_registry.metadata_by_component_type(
            ModelComponentType.ACTIVITY
        )
        self.cbo_raster_type.clear()
        for metadata in activity_metadatas:
            self.cbo_raster_type.addItem(metadata.display_name, metadata.id)

        # Try to restore the previously selected activity raster type
        settings = QgsSettings()
        settings.beginGroup("cplus/constant_rasters_dialog")
        activity_raster_type = settings.value("activity_raster_type", None)
        settings.endGroup()

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
            self.show_configuration_widget(metadata_id)

            # Update min/max values from the collection
            collection = self._raster_registry.collection_by_id(metadata_id)
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

    def on_output_range_changed(self, value: float):
        """Slot raised when output range spinbox values change."""
        collection = self.current_constant_raster_collection()
        if collection is not None:
            min_val = self.spin_min_value.value()
            max_val = self.spin_max_value.value()

            # Validate: max must be greater than min
            if max_val <= min_val:
                self.message_bar.pushWarning(
                    "Invalid Range",
                    f"Maximum ({max_val}) must be greater than minimum ({min_val})",
                )
                return

            # Update collection with current spinbox values
            collection.min_value = min_val
            collection.max_value = max_val

            # Save to settings
            self._raster_registry.save()

    def current_constant_raster_collection(
        self,
    ) -> typing.Optional[ConstantRasterCollection]:
        """Returns the constant raster collection based on the current selection in the combobox or None if invalid."""
        metadata_id = self.cbo_raster_type.itemData(self.cbo_raster_type.currentIndex())
        if not metadata_id:
            return None

        return self._raster_registry.collection_by_id(metadata_id)

    def _on_model_component_selection_changed(
        self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection
    ):
        """Slot raised when the selection of model component changes."""
        selected_indexes = selected.indexes()
        if len(selected_indexes) == 0:
            return

        if not selected_indexes[0].isValid():
            return

        model = None
        if self.rb_pathway.isChecked():
            model = self._pathways_model
        elif self.rb_activity.isChecked():
            model = self._activities_model

        if model is None:
            return

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

        # Raster component for the pathway or activity
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
            self._raster_registry.save()

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

        # Update the component's skip_value based on checkbox state
        raster_collection = self.current_constant_raster_collection()
        if raster_collection is not None:
            component = raster_collection.component_by_id(item.uuid)

            if component:
                # Component exists, update its skip_value
                component.skip_value = not is_checked

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
                    new_component.skip_value = False  # It's checked
                    raster_collection.components.append(new_component)

                    # Load the new component into widget
                    self._load_component_into_widget(new_component)

            # Save to registry
            self._raster_registry.save()

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

            # NOTE: We don't call normalize() here because:
            # 1. The output range (min_value, max_value) is user-controlled via spinboxes
            # 2. Auto-normalizing would override the user's explicit settings
            # 3. The user sets these values directly in the UI, not derived from component values

        # Save the registry to settings
        self._raster_registry.save()

    def _ensure_checked_components_in_collection(self):
        """Ensure all checked items in the list have components in the collection.

        This method creates components for checked items that don't have them yet,
        and marks unchecked components as skipped.
        """
        # Get current model and collection
        model = None
        if self.rb_pathway.isChecked():
            model = self._pathways_model
        elif self.rb_activity.isChecked():
            model = self._activities_model

        if model is None:
            return

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
                    component.alias_name = item.text()

                # Apply the current widget value to newly created components
                # Existing components keep their saved values
                if items_created and item.text() in items_created:
                    # This is a new component, apply current widget value
                    if current_value is not None and component.value_info:
                        component.value_info.absolute = current_value

                # Mark as enabled
                component.skip_value = False
            else:
                # Item is unchecked - mark as disabled if it exists
                if component is not None:
                    component.skip_value = True

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

        # NOTE: We don't call normalize() here anymore because:
        # 1. The user specifies min/max values explicitly in the UI
        # 2. Auto-normalizing would override user values
        # 3. With only one component, min==max causes incorrect 0.5 fallback

    def _get_pixel_size_from_snap_layer(self) -> float:
        """Get pixel size from the snap layer for consistency with analysis.

        The snap layer is used as a reference to align all rasters during
        scenario analysis. Using its pixel size ensures constant rasters
        are consistent with other processing outputs.

        :returns: Pixel size in map units, defaults to 30.0 if snap layer unavailable
        """
        DEFAULT_PIXEL_SIZE = 30.0

        # Get snap layer path from settings
        snap_layer_path = settings_manager.get_value(Settings.SNAP_LAYER, default="")

        if not snap_layer_path:
            return DEFAULT_PIXEL_SIZE

        if not os.path.exists(snap_layer_path):
            return DEFAULT_PIXEL_SIZE

        try:
            snap_layer = QgsRasterLayer(snap_layer_path, "snap", "gdal")
            if not snap_layer.isValid():
                log(
                    f"Invalid snap layer: {snap_layer_path}, using default pixel size",
                    info=False,
                )
                return DEFAULT_PIXEL_SIZE

            # Get pixel size (use X resolution, assuming square pixels)
            pixel_size_x = snap_layer.rasterUnitsPerPixelX()
            pixel_size_y = snap_layer.rasterUnitsPerPixelY()

            # Use average if X and Y differ
            pixel_size = (pixel_size_x + pixel_size_y) / 2.0
            return pixel_size

        except Exception as e:
            log(
                f"Error reading snap layer pixel size: {str(e)}, using default",
                info=False,
            )
            return DEFAULT_PIXEL_SIZE

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
                from qgis.utils import iface

                canvas = iface.mapCanvas() if iface else None
            except:
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

        # Get pixel size from snap layer for consistency with analysis
        pixel_size = self._get_pixel_size_from_snap_layer()

        return ConstantRasterContext(
            extent=extent,
            pixel_size=pixel_size,
            crs=crs,
            output_dir=output_dir,
        )

    def on_create_constant_raster_current_view(self):
        """Slot raised to create constant rasters for the current view."""
        current_raster_collection = self.current_constant_raster_collection()
        if current_raster_collection is None:
            self.message_bar.pushWarning(
                "No Collection", "Please select a constant raster type first."
            )
            return

        # FIRST: Apply user-specified min/max values to the collection
        # (Do this BEFORE creating components so normalize() doesn't override)
        min_val = self.spin_min_value.value()
        max_val = self.spin_max_value.value()

        current_raster_collection.min_value = min_val
        current_raster_collection.max_value = max_val

        # Ensure all checked items have components in the collection
        self._ensure_checked_components_in_collection()

        # Save the state after creating/updating components
        self._raster_registry.save()

        # NOW check if there are any enabled components (after creating them)
        enabled_components = current_raster_collection.enabled_components()
        if not enabled_components:
            self.message_bar.pushWarning(
                "No Enabled Components",
                "Please check at least one pathway/activity and set its value.",
            )
            return

        # Show info about extent being used
        studyarea_path = settings_manager.get_value(Settings.STUDYAREA_PATH)
        if studyarea_path and os.path.exists(studyarea_path):
            self.message_bar.pushInfo(
                "Using AOI Extent",
                "Creating rasters clipped to the Area of Interest defined in the plugin settings.",
            )
        else:
            self.message_bar.pushInfo(
                "Using Current View",
                "Creating rasters using the current map canvas extent. To use AOI clipping, configure the study area in the main plugin.",
            )

        # Create context
        context = self._create_context()

        # Create progress dialog
        progress_dialog = QtWidgets.QProgressDialog(
            "Creating constant rasters...", "Cancel", 0, 100, self
        )
        progress_dialog.setWindowTitle("Creating Constant Rasters")
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.show()

        # Create feedback
        feedback = QgsProcessingFeedback()

        # Connect feedback to progress dialog
        def update_progress(progress):
            progress_dialog.setValue(int(progress))

        def update_label(message):
            progress_dialog.setLabelText(message)

        feedback.progressChanged.connect(update_progress)
        feedback.pushInfo = lambda msg: update_label(msg)

        # Check for cancel
        def check_cancel():
            return progress_dialog.wasCanceled()

        # Get the metadata to extract input_range
        metadata_id = self.cbo_raster_type.itemData(self.cbo_raster_type.currentIndex())
        metadata = (
            self._raster_registry._metadata_store.get(metadata_id)
            if metadata_id
            else None
        )
        input_range = metadata.input_range if metadata else (0.0, 100.0)

        try:
            created_rasters = ConstantRasterProcessingUtils.create_constant_rasters(
                current_raster_collection, context, input_range, feedback, metadata_id
            )

            progress_dialog.close()

            if created_rasters:
                self.message_bar.pushSuccess(
                    "Success",
                    f"Created {len(created_rasters)} constant raster(s) in {context.output_dir}",
                )
            else:
                self.message_bar.pushWarning(
                    "No Rasters Created",
                    "No enabled components found in the collection.",
                )

        except Exception as e:
            progress_dialog.close()
            log(f"Error creating constant rasters: {str(e)}", info=False)
            self.message_bar.pushCritical(
                "Error", f"Failed to create constant rasters: {str(e)}"
            )

    def _save_dialog_state(self):
        """Save dialog-level state (model type selection, raster type selection)."""
        settings = QgsSettings()
        settings.beginGroup("cplus/constant_rasters_dialog")

        # Save which model type is selected (pathway=0, activity=1)
        model_type = 0 if self.rb_pathway.isChecked() else 1
        settings.setValue("model_type", model_type)

        # Save the constant raster type selection for each model type
        current_metadata_id = self.cbo_raster_type.itemData(
            self.cbo_raster_type.currentIndex()
        )
        if current_metadata_id:
            if self.rb_pathway.isChecked():
                settings.setValue("pathway_raster_type", current_metadata_id)
            else:
                settings.setValue("activity_raster_type", current_metadata_id)

        settings.endGroup()

    def _restore_dialog_state(self):
        """Restore dialog-level state (model type selection, raster type selection)."""
        settings = QgsSettings()
        settings.beginGroup("cplus/constant_rasters_dialog")

        # Restore which model type was selected
        model_type = settings.value("model_type", 0, type=int)

        settings.endGroup()

        if model_type == 1:
            # Switch to activities
            self.rb_activity.setChecked(True)
            # Manually call handler to ensure it runs even if signal not triggered
            self.on_activity_type_selected(True)
        else:
            # Stay on pathways (default)
            self.rb_pathway.setChecked(True)
            # Manually call handler to ensure it runs even if signal not triggered
            self.on_pathway_type_selected(True)

    def _restore_ui_state(self):
        """Restore UI state from saved components (checkboxes, output range)."""
        # First restore dialog-level state (which tab, which raster type)
        self._restore_dialog_state()

        # Now restore component-level state for the current collection
        current_collection = self.current_constant_raster_collection()
        if current_collection is None:
            return

        # Restore output range for currently selected collection
        self.spin_min_value.blockSignals(True)
        self.spin_max_value.blockSignals(True)
        self.spin_min_value.setValue(current_collection.min_value)
        self.spin_max_value.setValue(current_collection.max_value)
        self.spin_min_value.blockSignals(False)
        self.spin_max_value.blockSignals(False)

        # Restore checked items for BOTH pathways and activities
        # (not just the currently selected tab)

        # Restore pathways
        pathway_collection = self._raster_registry.collection_by_id(
            YEARS_EXPERIENCE_PATHWAY_ID
        )
        if pathway_collection:
            first_pathway_index = None
            for row in range(self._pathways_model.rowCount()):
                item = self._pathways_model.item(row)
                if item is None:
                    continue

                component = pathway_collection.component_by_id(item.uuid)
                if component and not component.skip_value:
                    # Block signals to prevent triggering _on_item_checked_changed
                    self._pathways_model.blockSignals(True)
                    item.setCheckState(QtCore.Qt.Checked)
                    self._pathways_model.blockSignals(False)
                    if first_pathway_index is None:
                        first_pathway_index = self._pathways_model.indexFromItem(item)

            # Auto-select first checked pathway if on pathway tab
            if self.rb_pathway.isChecked() and first_pathway_index is not None:
                self.lst_pathways.setCurrentIndex(first_pathway_index)

        # Restore activities
        activity_collection = self._raster_registry.collection_by_id(
            YEARS_EXPERIENCE_ACTIVITY_ID
        )
        if activity_collection:
            first_activity_index = None
            for row in range(self._activities_model.rowCount()):
                item = self._activities_model.item(row)
                if item is None:
                    continue

                component = activity_collection.component_by_id(item.uuid)
                if component and not component.skip_value:
                    # Block signals to prevent triggering _on_item_checked_changed
                    self._activities_model.blockSignals(True)
                    item.setCheckState(QtCore.Qt.Checked)
                    self._activities_model.blockSignals(False)
                    if first_activity_index is None:
                        first_activity_index = self._activities_model.indexFromItem(item)

            # Auto-select first checked activity if on activity tab
            if self.rb_activity.isChecked() and first_activity_index is not None:
                self.lst_activities.setCurrentIndex(first_activity_index)

    def _on_close(self):
        """Handle close button click."""
        # Save component state
        self._raster_registry.save()

        # Save dialog-level state (which tab, which raster type)
        self._save_dialog_state()

        # Close the dialog
        self.reject()
