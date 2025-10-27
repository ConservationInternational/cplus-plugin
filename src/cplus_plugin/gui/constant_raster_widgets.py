# -*- coding: utf-8 -*-
"""
Widgets for managing constant raster parameters.
"""

import os
import typing

from qgis.PyQt import QtCore, QtWidgets
from qgis.PyQt.uic import loadUiType

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
        if hasattr(self, 'update_requested') and self._raster_component is not None:
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

    def create_raster_component(self, model_component: LayerModelComponent) -> ConstantRasterComponent:
        """Creates a new default constant raster component.

        To be implemented by subclasses. Can use self to access
        current widget state (e.g., current spinbox value).

        :returns: A constant raster component object for
        use in defining the default component to use for
        new mappings.
        :rtype: ConstantRasterComponent
        """
        raise NotImplementedError


# Try to load UI file for YearsExperienceWidget
try:
    YearsExperienceWidgetUi, _ = loadUiType(
        os.path.join(os.path.dirname(__file__), "../ui/years_experience_widget.ui")
    )
except:
    # Fallback if UI file doesn't exist yet
    YearsExperienceWidgetUi = QtWidgets.QWidget


class YearsExperienceWidget(YearsExperienceWidgetUi, ConstantRasterWidgetInterface):
    """Widget for managing years of experience values."""

    update_requested = QtCore.pyqtSignal(ConstantRasterComponent)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Only setup UI if the UI file was loaded
        if hasattr(self, 'setupUi'):
            self.setupUi(self)
        else:
            # Create a simple layout manually if UI file doesn't exist
            self._create_manual_ui()

        # Connect signals
        if hasattr(self, 'sb_experience'):
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
        if hasattr(self, 'sb_experience'):
            self.sb_experience.setValue(0.0)

    def load(self, raster_component: ConstantRasterComponent):
        """Interface implementation."""
        self._raster_component = raster_component

        # Block signals temporarily to prevent notify_update from
        # being called to save the value being loaded.
        if hasattr(self, 'sb_experience'):
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

    def create_raster_component(self, layer_model_component: LayerModelComponent) -> ConstantRasterComponent:
        """Interface implementation."""
        from ..models.base import ModelComponentType

        # Determine component type
        component_type = ModelComponentType.UNKNOWN
        if hasattr(layer_model_component, '__class__'):
            class_name = layer_model_component.__class__.__name__
            if class_name == 'NcsPathway':
                component_type = ModelComponentType.NCS_PATHWAY
            elif class_name == 'Activity':
                component_type = ModelComponentType.ACTIVITY

        # Use current spinbox value if available, otherwise default to 0.0
        current_value = 0.0
        if hasattr(self, 'sb_experience'):
            current_value = self.sb_experience.value()

        return ConstantRasterComponent(
            value_info=ConstantRasterInfo(absolute=current_value),
            component=layer_model_component,
            component_id=str(layer_model_component.uuid) if hasattr(layer_model_component, 'uuid') else "",
            component_type=component_type,
            alias_name=layer_model_component.name if hasattr(layer_model_component, 'name') else "",
            skip_value=False
        )
