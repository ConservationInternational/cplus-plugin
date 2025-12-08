# -*- coding: utf-8 -*-
"""
Widgets for managing constant raster parameters.
"""

import sys
import typing

from qgis.PyQt import QtCore, QtWidgets

from ...definitions.defaults import YEARS_EXPERIENCE_ACTIVITY_ID
from ...models.base import LayerModelComponent, ModelComponentType
from ...models.constant_raster import (
    ConstantRasterComponent,
    ConstantRasterInfo,
    ConstantRasterMetadata,
    ConstantRasterCollection,
    InputRange,
)
from ...models.helpers import (
    constant_raster_collection_to_dict,
    constant_raster_collection_from_dict,
)
from ...utils import tr


class ConstantRasterWidgetInterface:
    """Provides common interface for each widget managing constant
    raster parameters. Should be implemented in custom widgets.

    See example implementation below.

    Each widget should define an update_requested signal with
    the following structure:
    update_requested = QtCore.pyqtSignal(ConstantRasterComponent)
    """

    def __init__(self, *args, **kwargs):
        #  This is included so that the interface is compatible
        # with multiple MRO chains in subclass implementations.
        super().__init__(*args, **kwargs)
        self._constant_raster_component = None

    @property
    def raster_component(self) -> typing.Optional[ConstantRasterComponent]:
        """Get the current raster component.

        :returns: Current raster component or None
        """
        return self._constant_raster_component

    @raster_component.setter
    def raster_component(self, component: ConstantRasterComponent):
        """Set the current raster component.

        :param component: Raster component to set
        """
        self._constant_raster_component = component

    def notify_update(self):
        """Notify calling widget that an update has been
        requested so that, for example, the changes can be
        processed and saved.
        """
        if (
            hasattr(self, "update_requested")
            and self._constant_raster_component is not None
        ):
            self.update_requested.emit(self._constant_raster_component)

    def reset(self):
        """Widget implementations should define how the
        controls will be reset before new values are
        populated via the load function.
        """
        pass

    def load(self, raster_component: ConstantRasterComponent):
        """Widget to implement this and specify how the information
        in the raster component will update the corresponding
        controls in the widget. This will be called when a
        user clicks on an activity in the list view.

        The raster component passed in this function will also be
        automatically set in the attribute so no further action
        required to set it.
        """
        raise NotImplementedError

    @classmethod
    def create_raster_component(
        cls, model_component: LayerModelComponent
    ) -> ConstantRasterComponent:
        """Creates a new default constant raster component.

        To be implemented by subclasses. Should create a component
        with default values (typically 0.0 for numeric values).
        The actual value will be set later when the user enters it.

        :param model_component: The activity model component
        :returns: A constant raster component object for
        use in defining the default component to use for
        new mappings.
        :rtype: ConstantRasterComponent
        """
        raise NotImplementedError

    @classmethod
    def create_metadata(cls) -> "ConstantRasterMetadata":
        """Creates metadata for this constant raster type.

        Convenience function for returning default metadata for
        this constant raster type.

        Subclasses need to override this function.

        :returns: Metadata definition for the constant raster
        type.
        :rtype: ConstantRasterMetadata
        """
        raise NotImplementedError


class YearsExperienceWidget(QtWidgets.QWidget, ConstantRasterWidgetInterface):
    """Widget for managing years of experience values."""

    update_requested = QtCore.pyqtSignal(ConstantRasterComponent)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create UI programmatically
        self._create_manual_ui()

        # Connect signals
        if hasattr(self, "sb_experience"):
            self.sb_experience.valueChanged.connect(self.on_experience_value_changed)

    def _create_manual_ui(self):
        """Create UI manually if UI file doesn't exist."""
        layout = QtWidgets.QVBoxLayout(self)

        # Label
        label = QtWidgets.QLabel("Years of Experience:")
        layout.addWidget(label)

        # Spin box
        self.sb_experience = QtWidgets.QDoubleSpinBox()
        self.sb_experience.setMinimum(0.0)
        self.sb_experience.setMaximum(100.0)
        self.sb_experience.setValue(0.0)
        self.sb_experience.setDecimals(1)
        layout.addWidget(self.sb_experience)

        # Stretch
        layout.addStretch()

    def reset(self):
        """Interface implementation."""
        if hasattr(self, "sb_experience"):
            self.sb_experience.blockSignals(True)
            self.sb_experience.setValue(0.0)
            self.sb_experience.blockSignals(False)

    def load(self, raster_component: ConstantRasterComponent):
        """Interface implementation."""
        # Block signals temporarily to prevent notify_update from
        # being called to save the value being loaded.
        if hasattr(self, "sb_experience"):
            self.sb_experience.blockSignals(True)
            if raster_component and raster_component.value_info:
                self.sb_experience.setValue(raster_component.value_info.absolute)
            else:
                self.sb_experience.setValue(0.0)
            self.sb_experience.blockSignals(False)

    def on_experience_value_changed(self, value: float):
        """Slot raised when spin box value changes."""
        if (
            self._constant_raster_component
            and self._constant_raster_component.value_info
        ):
            self._constant_raster_component.value_info.absolute = value
        self.notify_update()

    @classmethod
    def create_raster_component(
        cls, model_component: LayerModelComponent
    ) -> ConstantRasterComponent:
        """Interface implementation.

        Creates a component with default value 0.0. The actual value
        will be set later when the user enters it in the widget.
        """
        # Component type is always ACTIVITY for constant rasters
        component_type = ModelComponentType.ACTIVITY

        return ConstantRasterComponent(
            value_info=ConstantRasterInfo(absolute=0.0),  # Default value
            component=model_component,
            skip_raster=False,
        )

    @classmethod
    def create_metadata(cls) -> "ConstantRasterMetadata":
        """Create metadata for Years of Experience constant raster type.

        Overrides the default implementation to provide specific
        metadata for this widget type.

        :returns: ConstantRasterMetadata object configured for years of experience
        """
        collection = ConstantRasterCollection(
            min_value=0.0,
            max_value=0.0,
            component_type=ModelComponentType.ACTIVITY,
            components=[],
            allowable_max=sys.float_info.max,
            allowable_min=0.0,
            use_manual=False,
        )

        return ConstantRasterMetadata(
            id=YEARS_EXPERIENCE_ACTIVITY_ID,
            display_name=tr("Years of Experience"),
            raster_collection=collection,
            serializer=constant_raster_collection_to_dict,
            deserializer=constant_raster_collection_from_dict,
            component_type=ModelComponentType.ACTIVITY,
            input_range=InputRange(min=0.0, max=100.0),  # 0-100 years
        )


class GenericNumericWidget(QtWidgets.QWidget, ConstantRasterWidgetInterface):
    """Generic configurable widget for numeric constant raster values.

    This widget can be configured with custom labels, ranges, and decimal places,
    allowing dynamic creation of constant raster types without code duplication.
    """

    update_requested = QtCore.pyqtSignal(ConstantRasterComponent)

    def __init__(
        self,
        label: str,
        metadata_id: str,
        min_value: float = 0.0,
        max_value: float = 100.0,
        default_value: float = None,
        parent=None,
    ):
        """Initialize the generic numeric widget.

        :param label: Display label for the input (e.g., "Training Hours")
        :param metadata_id: Unique identifier for the metadata
        :param min_value: Minimum allowed value (default: 0.0)
        :param max_value: Maximum allowed value (default: 100.0)
        :param default_value: Default value for new components (default: min_value)
        :param parent: Parent widget
        """
        super().__init__(parent)

        # Store configuration
        self.label = label
        self.metadata_id = metadata_id
        self.min_value = min_value
        self.max_value = max_value
        self.default_value = default_value if default_value is not None else min_value

        # Create UI
        self._create_ui()

        # Connect signals
        self.spin_box.valueChanged.connect(self.on_value_changed)

    def _create_ui(self):
        """Create UI with configurable parameters."""
        layout = QtWidgets.QVBoxLayout(self)

        # Label
        label = QtWidgets.QLabel(f"{self.label}:")
        layout.addWidget(label)

        # Spin box
        self.spin_box = QtWidgets.QDoubleSpinBox()
        self.spin_box.setMinimum(self.min_value)
        self.spin_box.setMaximum(self.max_value)
        self.spin_box.setValue(self.default_value)
        self.spin_box.setDecimals(1)
        layout.addWidget(self.spin_box)

        # Stretch
        layout.addStretch()

    def set_range(self, min_value: float, max_value: float):
        """Update the allowed range for the spinbox.

        :param min_value: New minimum value
        :param max_value: New maximum value
        """
        self.min_value = min_value
        self.max_value = max_value
        if hasattr(self, "spin_box"):
            self.spin_box.setMinimum(min_value)
            self.spin_box.setMaximum(max_value)

    def reset(self):
        """Reset widget to default value."""
        if hasattr(self, "spin_box"):
            self.spin_box.blockSignals(True)
            self.spin_box.setValue(self.default_value)
            self.spin_box.blockSignals(False)

    def load(self, raster_component: ConstantRasterComponent):
        """Load values from raster component."""
        if hasattr(self, "spin_box"):
            self.spin_box.blockSignals(True)
            if raster_component and raster_component.value_info:
                self.spin_box.setValue(raster_component.value_info.absolute)
            else:
                self.spin_box.setValue(self.default_value)
            self.spin_box.blockSignals(False)

    def on_value_changed(self, value: float):
        """Handle value changes."""
        if (
            self._constant_raster_component
            and self._constant_raster_component.value_info
        ):
            self._constant_raster_component.value_info.absolute = value
        self.notify_update()

    def create_raster_component(
        self, model_component: LayerModelComponent
    ) -> ConstantRasterComponent:
        """Create a default raster component.

        Creates a component with the configured default value.
        The actual value will be set later when the user enters it in the widget.
        """
        return ConstantRasterComponent(
            value_info=ConstantRasterInfo(absolute=self.default_value),
            component=model_component,
            skip_raster=False,
        )

    @classmethod
    def create_metadata(cls) -> "ConstantRasterMetadata":
        """Create metadata for this generic numeric constant raster type.

        Base class override.

        :returns: ConstantRasterMetadata object configured for this
        generic type.
        :rtype: ConstantRasterMetadata
        """
        collection = ConstantRasterCollection(
            min_value=0.0,
            max_value=100.0,
            component_type=ModelComponentType.ACTIVITY,
            components=[],
            allowable_max=sys.float_info.max,
            allowable_min=0.0,
        )

        return ConstantRasterMetadata(
            raster_collection=collection,
            serializer=constant_raster_collection_to_dict,
            deserializer=constant_raster_collection_from_dict,
            component_type=ModelComponentType.ACTIVITY,
            user_defined=True,
        )
