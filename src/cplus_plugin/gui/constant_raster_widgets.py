# -*- coding: utf-8 -*-
"""
Widgets for managing constant raster parameters.
"""

import typing

from qgis.PyQt import QtCore, QtWidgets

from ..models.base import LayerModelComponent
from ..models.constant_raster import (
    ConstantRasterComponent,
    ConstantRasterInfo,
)


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
        self._raster_component = None

    @property
    def raster_component(self) -> typing.Optional[ConstantRasterComponent]:
        """Get the current raster component.

        :returns: Current raster component or None
        """
        return self._raster_component

    @raster_component.setter
    def raster_component(self, component: ConstantRasterComponent):
        """Set the current raster component.

        :param component: Raster component to set
        """
        self._raster_component = component

    def notify_update(self):
        """Notify calling widget that an update has been
        requested so that, for example, the changes can be
        processed and saved.
        """
        if hasattr(self, "update_requested") and self._raster_component is not None:
            self.update_requested.emit(self._raster_component)

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
        user clicks on an NCS pathway or activity in the list view.

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

        :param model_component: The layer model component (pathway/activity)
        :returns: A constant raster component object for
        use in defining the default component to use for
        new mappings.
        :rtype: ConstantRasterComponent
        """
        raise NotImplementedError

    @classmethod
    def create_metadata(
        cls, metadata_id: str, component_type: "ModelComponentType"
    ) -> "ConstantRasterMetadata":
        """Creates metadata for this constant raster type.

        Provides default implementation that can be overridden by subclasses.
        Each widget type should define its own display name, input range,
        and other metadata properties.

        :param metadata_id: Unique identifier for this metadata instance
        :param component_type: Type of component (NCS_PATHWAY or ACTIVITY)
        :returns: ConstantRasterMetadata object
        """
        from ..models.constant_raster import (
            ConstantRasterMetadata,
            ConstantRasterCollection,
        )
        from ..models.base import ModelComponentType

        # Default implementation - subclasses should override
        collection = ConstantRasterCollection(
            min_value=0.0,
            max_value=100.0,
            component_type=component_type,
            components=[],
            allowable_max=100.0,
            allowable_min=0.0,
        )

        return ConstantRasterMetadata(
            id=metadata_id,
            display_name="Constant Raster",  # Override in subclass
            fcollection=collection,
            deserializer=None,
            component_type=component_type,
            input_range=(0.0, 100.0),  # Override in subclass
        )


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
            self.sb_experience.setValue(0.0)

    def load(self, raster_component: ConstantRasterComponent):
        """Interface implementation."""
        self._raster_component = raster_component

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
        if self._raster_component and self._raster_component.value_info:
            self._raster_component.value_info.absolute = value
        self.notify_update()

    @classmethod
    def create_raster_component(
        cls, model_component: LayerModelComponent
    ) -> ConstantRasterComponent:
        """Interface implementation.

        Creates a component with default value 0.0. The actual value
        will be set later when the user enters it in the widget.
        """
        from ..models.base import ModelComponentType

        # Determine component type
        component_type = ModelComponentType.UNKNOWN
        if hasattr(model_component, "__class__"):
            class_name = model_component.__class__.__name__
            if class_name == "NcsPathway":
                component_type = ModelComponentType.NCS_PATHWAY
            elif class_name == "Activity":
                component_type = ModelComponentType.ACTIVITY

        return ConstantRasterComponent(
            value_info=ConstantRasterInfo(absolute=0.0),  # Default value
            component=model_component,
            component_id=(
                str(model_component.uuid) if hasattr(model_component, "uuid") else ""
            ),
            component_type=component_type,
            alias_name=(
                model_component.name if hasattr(model_component, "name") else ""
            ),
            skip_value=False,
        )

    @classmethod
    def create_metadata(
        cls, metadata_id: str, component_type: "ModelComponentType"
    ) -> "ConstantRasterMetadata":
        """Create metadata for Years of Experience constant raster type.

        Overrides the default implementation to provide specific
        metadata for this widget type.

        :param metadata_id: Unique identifier for this metadata instance
        :param component_type: Type of component (NCS_PATHWAY or ACTIVITY)
        :returns: ConstantRasterMetadata object configured for years of experience
        """
        from ..models.constant_raster import (
            ConstantRasterMetadata,
            ConstantRasterCollection,
        )

        collection = ConstantRasterCollection(
            min_value=0.0,
            max_value=100.0,
            component_type=component_type,
            components=[],
            allowable_max=100.0,
            allowable_min=0.0,
        )

        return ConstantRasterMetadata(
            id=metadata_id,
            display_name="Years of Experience",
            fcollection=collection,
            deserializer=None,
            component_type=component_type,
            input_range=(0.0, 100.0),  # 0-100 years
        )
