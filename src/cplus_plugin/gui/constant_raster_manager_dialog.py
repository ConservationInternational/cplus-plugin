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
YEARS_EXPERIENCE_ID = "years_experience"


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

        # Min/Max normalization range (collapsible)
        norm_group = QtWidgets.QGroupBox("Min/Max Normalization Range")
        norm_group.setCheckable(True)
        norm_group.setChecked(True)
        norm_layout = QtWidgets.QFormLayout(norm_group)
        self.spin_min_value = QtWidgets.QDoubleSpinBox()
        self.spin_min_value.setReadOnly(True)
        self.spin_min_value.setButtonSymbols(QtWidgets.QDoubleSpinBox.NoButtons)
        self.spin_min_value.setDecimals(2)
        self.spin_max_value = QtWidgets.QDoubleSpinBox()
        self.spin_max_value.setReadOnly(True)
        self.spin_max_value.setButtonSymbols(QtWidgets.QDoubleSpinBox.NoButtons)
        self.spin_max_value.setDecimals(2)
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

    def register_widget(self, metadata_id: str, config_widget: ConstantRasterWidgetInterface) -> bool:
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
            if hasattr(config_widget, 'update_requested'):
                config_widget.update_requested.connect(self.on_update_raster_component)

        return True

    def widget_by_identifier(self, metadata_id: str) -> typing.Optional[ConstantRasterWidgetInterface]:
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

        self.sw_component_container.setCurrentIndex(self._registered_component_widgets[metadata_id])

    def _register_sample_metadata(self):
        """Register sample metadata for demonstration.

        This creates a "Years of Experience" metadata type for NCS pathways.
        In production, metadata would be loaded from settings or defined elsewhere.
        """
        from ..models.constant_raster import ConstantRasterMetadata, ConstantRasterCollection

        # Check if already registered
        if YEARS_EXPERIENCE_ID in self._raster_registry.metadata_ids():
            return

        # Create an empty collection (components will be added dynamically)
        collection = ConstantRasterCollection(
            filter_value=0.0,
            total_value=100.0,
            components=[],
            skip_raster=False
        )

        # Create metadata
        metadata = ConstantRasterMetadata(
            id=YEARS_EXPERIENCE_ID,
            display_name="Years of Experience",
            fcollection=collection,
            deserializer=None  # Use default
        )

        # Register it
        self._raster_registry.register_metadata(metadata)

    def _initialize(self):
        """Initialize UI components and connections."""
        # Register sample metadata if not already registered
        self._register_sample_metadata()

        # Register widgets for known constant rasters
        metadata_ids = self._raster_registry.metadata_ids()
        if YEARS_EXPERIENCE_ID in metadata_ids:
            experience_widget = YearsExperienceWidget()
            self.register_widget(YEARS_EXPERIENCE_ID, experience_widget)

        # Load item models
        self._pathways_model = NcsPathwayItemModel(is_checkable=True)
        self.lst_pathways.setModel(self._pathways_model)
        for pathway in settings_manager.get_all_ncs_pathways():
            self._pathways_model.add_ncs_pathway(pathway)

        # Connect to the view's selection model, not the model itself
        self.lst_pathways.selectionModel().selectionChanged.connect(
            self._on_model_component_selection_changed
        )

        self._activities_model = ActivityItemModel(load_pathways=False, is_checkable=True)
        self.lst_activities.setModel(self._activities_model)
        for activity in settings_manager.get_all_activities():
            self._activities_model.add_activity(activity)

        # Connect to the view's selection model, not the model itself
        self.lst_activities.selectionModel().selectionChanged.connect(
            self._on_model_component_selection_changed
        )

        # Connections
        self.cbo_raster_type.currentIndexChanged.connect(self.on_raster_type_selection_changed)
        self.rb_pathway.toggled.connect(self.on_pathway_type_selected)
        self.rb_activity.toggled.connect(self.on_activity_type_selected)
        self.btn_create_current.clicked.connect(self.on_create_constant_raster_current_view)
        self.btn_close.clicked.connect(self._on_close)

        # Initialize with pathways selected
        self.on_pathway_type_selected(True)

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
        pathway_metadatas = self._raster_registry.metadata_by_component_type(ModelComponentType.NCS_PATHWAY)
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
        activity_metadatas = self._raster_registry.metadata_by_component_type(ModelComponentType.ACTIVITY)
        self.cbo_raster_type.clear()
        for metadata in activity_metadatas:
            self.cbo_raster_type.addItem(metadata.display_name, metadata.id)

    def on_raster_type_selection_changed(self, index: int):
        """Slot raised when the selection in the combobox for raster type has changed."""
        metadata_id = self.cbo_raster_type.itemData(index)
        if metadata_id:
            self.show_configuration_widget(metadata_id)

    def current_constant_raster_collection(self) -> typing.Optional[ConstantRasterCollection]:
        """Returns the constant raster collection based on the current selection in the combobox or None if invalid."""
        metadata_id = self.cbo_raster_type.itemData(self.cbo_raster_type.currentIndex())
        if not metadata_id:
            return None

        return self._raster_registry.collection_by_id(metadata_id)

    def _on_model_component_selection_changed(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection):
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
        if raster_component is None:
            # Create a default one and add it to the collection
            raster_component = current_config_widget.create_raster_component(model_item.model_component)
            raster_collection.components.append(raster_component)

        current_config_widget.raster_component = raster_component
        current_config_widget.reset()
        current_config_widget.load(raster_component)

    def on_update_raster_component(self, raster_component: ConstantRasterComponent):
        """Slot raised when the component has been updated through the configuration widget."""
        # Get current collection and ensure the component is in it
        raster_collection = self.current_constant_raster_collection()
        if raster_collection:
            # Make sure the component is in the collection
            if raster_component not in raster_collection.components:
                raster_collection.components.append(raster_component)

            # Update min/max values
            raster_collection.normalize()

            # Update min/max UI controls
            self.spin_min_value.setValue(raster_collection.filter_value)
            self.spin_max_value.setValue(raster_collection.total_value)

        # Save the registry to settings
        self._raster_registry.save()

    def _create_context(self) -> ConstantRasterContext:
        """Create a ConstantRasterContext from current map canvas and settings.

        :returns: Configured ConstantRasterContext
        """
        # Get extent and CRS from the current map canvas
        canvas = FileUtils.iface.mapCanvas() if hasattr(FileUtils, 'iface') and FileUtils.iface else None

        if canvas:
            extent = canvas.extent()
            crs = canvas.mapSettings().destinationCrs()
        else:
            # Fallback: use project CRS and extent
            project = QgsProject.instance()
            crs = project.crs()
            # Default extent if no canvas
            extent = QgsRectangle(0, 0, 1000, 1000)

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
            output_dir=output_dir
        )

    def on_create_constant_raster_current_view(self):
        """Slot raised to create constant rasters for the current view."""
        current_raster_collection = self.current_constant_raster_collection()
        if not current_raster_collection:
            self.message_bar.pushWarning(
                "No Collection",
                "Please select a constant raster type first."
            )
            return

        # Create context
        context = self._create_context()

        # Create progress dialog
        progress_dialog = QtWidgets.QProgressDialog(
            "Creating constant rasters...",
            "Cancel",
            0,
            100,
            self
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

        try:
            created_rasters = create_constant_rasters(
                current_raster_collection,
                context,
                feedback
            )

            progress_dialog.close()

            if created_rasters:
                self.message_bar.pushSuccess(
                    "Success",
                    f"Created {len(created_rasters)} constant raster(s) in {context.output_dir}"
                )
            else:
                self.message_bar.pushWarning(
                    "No Rasters Created",
                    "No enabled components found in the collection."
                )

        except Exception as e:
            progress_dialog.close()
            log(f"Error creating constant rasters: {str(e)}", info=False)
            self.message_bar.pushCritical(
                "Error",
                f"Failed to create constant rasters: {str(e)}"
            )

    def _on_close(self):
        """Handle close button click."""
        # Since this widget is embedded in a dialog, close the parent dialog
        parent_dialog = self.window()
        if parent_dialog:
            parent_dialog.reject()
