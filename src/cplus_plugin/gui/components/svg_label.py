# -*- coding: utf-8 -*-
"""
Custom label for displaying SVG images.
"""

import os
import typing

from qgis.PyQt import QtCore, QtGui, QtSvg, QtWidgets


class SvgLabel(QtWidgets.QLabel):
    """Label for displaying an SVG image."""

    def __init__(self, parent=None, svg_path=None):
        super().__init__(parent)
        self._svg_path = svg_path
        self._update()

    @property
    def svg_path(self) -> str:
        """Gets the path to the SVG file.

        :returns: The path to the SVG file or an empty
        string if not specified.
        :rtype: str
        """
        return self._svg_path

    @svg_path.setter
    def svg_path(self, svg_path: str):
        """Sets the path to the SVG file.

        :param svg_path: Path to the SVG file. If empty,
        the label will display a blank image.
        :type svg_path: str
        """
        if svg_path != self._svg_path:
            self._svg_path = svg_path
            self._update()

    def _update(self):
        """Render the SVG image."""
        pixmap = QtGui.QPixmap()

        if self._svg_path:
            renderer = QtSvg.QSvgRenderer(os.path.normpath(self._svg_path))
            pixmap = QtGui.QPixmap(renderer.defaultSize())
            pixmap.fill(QtCore.Qt.GlobalColor.transparent)
            painter = QtGui.QPainter(pixmap)
            renderer.render(painter)
            painter.end()

        self.setPixmap(pixmap)
