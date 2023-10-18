# -*- coding: utf-8 -*-
"""
Checks if the current extent is within the pilot area of interest.
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
)
from qgis.utils import iface

from qgis.PyQt import QtCore, QtGui

from ..conf import settings_manager, Settings
from ..definitions.defaults import DEFAULT_CRS_ID, PILOT_AREA_EXTENT
from ..utils import FileUtils, log, tr


class PilotExtentCheck(QtCore.QObject):
    """Checks if current map extents is within the pilot area."""

    extent_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None, pilot_extent=None):
        """Constructor.

        :param parent: Parent object or owner.
        :type parent: QtCore.QObject

        :param pilot_extent: Extent of the pilot area. If None is
        specified, it will fetch the value specified
        in :py:mod:`cplus_plugin.definitions.defaults.py` module.
        :type pilot_extent: QgsRectangle
        """
        super().__init__(parent)

        self._pilot_extent = pilot_extent
        if self._pilot_extent is None:
            extent_list = PILOT_AREA_EXTENT["coordinates"]
            self._pilot_extent = QgsRectangle(
                extent_list[0], extent_list[2], extent_list[1], extent_list[3]
            )

        self._map_canvas = iface.mapCanvas()
        self._map_canvas.extentsChanged.connect(self._on_extent_changed)

    def _on_extent_changed(self):
        """Slot raised when the current map extent has changed. This
        will be cascaded to trigger an `extent_changed` signal.
        """
        self.extent_changed.emit()

    def is_within_pilot_area(self) -> bool:
        """Checks if the current extent is within the pilot area.

        :returns: True if the current map canvas extent is within the
        pilot area, else False.
        :rtype: bool
        """
        return self.pilot_extent.contains(self.current_extent)

    @property
    def current_extent(self) -> QgsRectangle:
        """Get the visible extent of the map canvas.

        :returns: The current visible extent of the map canvas.
        :rtype: QgsRectangle
        """
        return self._map_canvas.extent()

    @property
    def pilot_extent(self) -> QgsRectangle:
        """Get the extent of the pilot area in the project's CRS.

        :returns: Extent of the pilot area in the project's CRS.
        :rtype: QgsRectangle
        """
        default_crs = QgsCoordinateReferenceSystem.fromEpsgId(DEFAULT_CRS_ID)
        project_crs = QgsProject.instance().crs()

        if default_crs == project_crs:
            # No need for transformation
            return self._pilot_extent

        coordinate_xform = QgsCoordinateTransform(
            default_crs, project_crs, QgsProject.instance()
        )

        return coordinate_xform.transformBoundingBox(self._pilot_extent)
