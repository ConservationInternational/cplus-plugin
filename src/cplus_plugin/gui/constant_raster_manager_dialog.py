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
)
from qgis.gui import QgsGui, QgsMessageBar

from ..conf import settings_manager, Settings
from ..models.base import ModelComponentType
from ..models.constant_raster import (
    ConstantRasterCollection,
    ConstantRasterComponent,
    ConstantRasterContext,
    constant_raster_registry,
)
from ..definitions.defaults import ICON_PATH
from .component_item_model import NcsPathwayItemModel, ActivityItemModel
from .constant_raster_widgets import (
    ConstantRasterWidgetInterface,
    YearsExperienceWidget,
)
from ..lib.constant_raster import create_constant_rasters
from ..utils import log, FileUtils

# Constant raster type IDs
YEARS_EXPERIENCE_PATHWAY_ID = "years_experience_pathway"
YEARS_EXPERIENCE_ACTIVITY_ID = "years_experience_activity"


class ConstantRastersManagerDialog(QtWidgets.QWidget):
    """Widget for managing constant rasters (embedded in PWL Manager tabs)."""

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
            "Define constant raster parameters for NCS pathways and activities to be included "
            "as Priority Weighting Layers (PWLs). Configure input values (e.g., years of experience), "
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
            "<b>Description:</b> Constant rasters for NCS pathways will be added to the collection of normalized PWLs"
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
        # This allows users to remap the normalized output, e.g., 0-1 to 0.2-0.8
        norm_group = QtWidgets.QGroupBox("Output Range (remapping)")
        norm_group.setCheckable(True)
        norm_group.setChecked(True)
        norm_group.setToolTip(
            "Adjust the output range for normalized values. Default 0-1 means full range."
        )
        norm_layout = QtWidgets.QFormLayout(norm_group)
        self.spin_min_value = QtWidgets.QDoubleSpinBox()
        self.spin_min_value.setRange(0.0, 1.0)
        self.spin_min_value.setDecimals(4)
        self.spin_min_value.setSingleStep(0.01)
        self.spin_min_value.setValue(0.0)
        self.spin_min_value.setToolTip("Minimum output value (0.0 = lowest priority)")
        self.spin_max_value = QtWidgets.QDoubleSpinBox()
        self.spin_max_value.setRange(0.0, 1.0)
        self.spin_max_value.setDecimals(4)
        self.spin_max_value.setSingleStep(0.01)
        self.spin_max_value.setValue(1.0)
        self.spin_max_value.setToolTip("Maximum output value (1.0 = highest priority)")
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
        from ..models.constant_raster import (
            ConstantRasterMetadata,
            ConstantRasterCollection,
        )

        # Register for NCS Pathways
        if YEARS_EXPERIENCE_PATHWAY_ID not in self._raster_registry.metadata_ids():
            collection_pathway = ConstantRasterCollection(
                filter_value=0.0,
                total_value=1.0,  # Output range: 0-1 (normalized)
                components=[],
                skip_raster=False,
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
                filter_value=0.0,
                total_value=1.0,  # Output range: 0-1 (normalized)
                components=[],
                skip_raster=False,
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

        # Connect output range spinboxes to save the values to the collection
        self.spin_min_value.valueChanged.connect(self.on_output_range_changed)
        self.spin_max_value.valueChanged.connect(self.on_output_range_changed)

        # Initialize with pathways selected
        self.on_pathway_type_selected(True)

        # Restore UI state from saved components
        self._restore_ui_state()

    def on_pathway_type_selected(self, checked: bool):
        """Slot raised when pathway radio button is selected."""
        if not checked:
            return

        self.sw_model_type_container.setCurrentIndex(0)
        self._left_group.setTitle("NCS Pathways")
        self.lbl_description.setText(
            "<b>Description:</b> Constant rasters for NCS pathways will be added to the collection of normalized PWLs"
        )

        # Get metadata for pathways
        pathway_metadatas = self._raster_registry.metadata_by_component_type(
            ModelComponentType.NCS_PATHWAY
        )
        self.cbo_raster_type.clear()
        for metadata in pathway_metadatas:
            self.cbo_raster_type.addItem(metadata.display_name, metadata.id)

    def on_activity_type_selected(self, checked: bool):
        """Slot raised when activity radio button is selected."""
        if not checked:
            return

        self.sw_model_type_container.setCurrentIndex(1)
        self._left_group.setTitle("Activities")
        self.lbl_description.setText(
            "<b>Description:</b> Constant rasters for activities will be added to the collection of normalized PWLs"
        )

        # Get metadata for activities
        activity_metadatas = self._raster_registry.metadata_by_component_type(
            ModelComponentType.ACTIVITY
        )
        self.cbo_raster_type.clear()
        for metadata in activity_metadatas:
            self.cbo_raster_type.addItem(metadata.display_name, metadata.id)

    def on_raster_type_selection_changed(self, index: int):
        """Slot raised when the selection in the combobox for raster type has changed."""
        metadata_id = self.cbo_raster_type.itemData(index)
        if metadata_id:
            self.show_configuration_widget(metadata_id)

            # Update min/max values from the collection
            collection = self._raster_registry.collection_by_id(metadata_id)
            if collection:
                # Block signals temporarily to avoid triggering save while loading
                self.spin_min_value.blockSignals(True)
                self.spin_max_value.blockSignals(True)

                # Sanity check: if the range is invalid, reset to defaults
                if collection.filter_value >= collection.total_value:
                    log(
                        f"Invalid range detected: min={collection.filter_value}, max={collection.total_value}. Resetting to 0-1.",
                        info=True,
                    )
                    collection.filter_value = 0.0
                    collection.total_value = 1.0

                self.spin_min_value.setValue(collection.filter_value)
                self.spin_max_value.setValue(collection.total_value)

                self.spin_min_value.blockSignals(False)
                self.spin_max_value.blockSignals(False)

    def on_output_range_changed(self, value: float):
        """Slot raised when output range spinbox values change."""
        collection = self.current_constant_raster_collection()
        if collection:
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
            collection.filter_value = min_val
            collection.total_value = max_val

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
        if not raster_collection:
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
            log(f"Created new component for {model_identifier}", info=True)
        else:
            log(
                f"Found existing component for {model_identifier} with value: {raster_component.value_info.absolute if raster_component.value_info else 'None'}",
                info=True,
            )

        current_config_widget.raster_component = raster_component
        current_config_widget.reset()
        current_config_widget.load(raster_component)

        # Save if we created a new component
        if component_created:
            self._raster_registry.save()

    def on_update_raster_component(self, raster_component: ConstantRasterComponent):
        """Slot raised when the component has been updated through the configuration widget."""
        # Get current collection and ensure the component is in it
        raster_collection = self.current_constant_raster_collection()
        if raster_collection:
            # Make sure the component is in the collection
            if raster_component not in raster_collection.components:
                raster_collection.components.append(raster_component)

            # NOTE: We don't call normalize() here because:
            # 1. The output range (filter_value, total_value) is user-controlled via spinboxes
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
        if not raster_collection:
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

    def _create_context(self) -> ConstantRasterContext:
        """Create a ConstantRasterContext from current map canvas and settings.

        :returns: Configured ConstantRasterContext
        """
        # Try to get extent from AOI/Study Area first
        studyarea_path = settings_manager.get_value(Settings.STUDYAREA_PATH)
        use_aoi = studyarea_path and os.path.exists(studyarea_path)

        if use_aoi:
            # Use AOI extent
            from qgis.core import QgsVectorLayer

            aoi_layer = QgsVectorLayer(studyarea_path, "temp_aoi", "ogr")
            if aoi_layer.isValid():
                extent = aoi_layer.extent()
                crs = aoi_layer.crs()
                log(f"Using AOI extent: {extent.toString()}", info=True)
                log(f"AOI CRS: {crs.authid()}", info=True)
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

                # Log extent details for debugging
                log(f"Canvas extent: {extent.toString()}", info=True)
                log(f"Canvas CRS: {crs.authid()}", info=True)
                log(
                    f"Extent bounds: xmin={extent.xMinimum()}, xmax={extent.xMaximum()}, ymin={extent.yMinimum()}, ymax={extent.yMaximum()}",
                    info=True,
                )
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

        return ConstantRasterContext(
            extent=extent,
            pixel_size=30.0,  # Default 30m resolution
            crs=crs,
            output_dir=output_dir,
        )

    def on_create_constant_raster_current_view(self):
        """Slot raised to create constant rasters for the current view."""
        current_raster_collection = self.current_constant_raster_collection()
        if not current_raster_collection:
            self.message_bar.pushWarning(
                "No Collection", "Please select a constant raster type first."
            )
            return

        # FIRST: Apply user-specified min/max values to the collection
        # (Do this BEFORE creating components so normalize() doesn't override)
        min_val = self.spin_min_value.value()
        max_val = self.spin_max_value.value()

        log(f"Setting collection range: min={min_val}, max={max_val}", info=True)

        current_raster_collection.filter_value = min_val
        current_raster_collection.total_value = max_val

        # Ensure all checked items have components in the collection
        self._ensure_checked_components_in_collection()

        # Save the state after creating/updating components
        self._raster_registry.save()

        log(
            f"After ensuring components, collection range: min={current_raster_collection.filter_value}, max={current_raster_collection.total_value}",
            info=True,
        )

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

        log(f"Using input_range: {input_range}", info=True)

        try:
            created_rasters = create_constant_rasters(
                current_raster_collection, context, input_range, feedback
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

    def _restore_ui_state(self):
        """Restore UI state from saved components (checkboxes, output range)."""
        current_collection = self.current_constant_raster_collection()
        if not current_collection:
            return

        # Restore output range
        self.spin_min_value.setValue(current_collection.filter_value)
        self.spin_max_value.setValue(current_collection.total_value)

        # Restore checked items based on saved components
        model = None
        if self.rb_pathway.isChecked():
            model = self._pathways_model
        elif self.rb_activity.isChecked():
            model = self._activities_model

        if model:
            for row in range(model.rowCount()):
                item = model.item(row)
                if item is None:
                    continue

                # Check if this item has a saved component
                component = current_collection.component_by_id(item.uuid)
                if component and not component.skip_value:
                    # This item was checked before, restore it
                    item.setCheckState(QtCore.Qt.Checked)

    def _on_close(self):
        """Handle close button click."""
        # Save state before closing
        self._raster_registry.save()

        # Since this widget is embedded in a dialog, close the parent dialog
        parent_dialog = self.window()
        if parent_dialog:
            parent_dialog.reject()
