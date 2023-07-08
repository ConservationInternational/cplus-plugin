# -*- coding: utf-8 -*-
"""
Registers custom report variables for layout design
and handles report generation.
"""

from qgis.PyQt import QtCore

from qgis.core import QgsPrintLayout

from .variable_register import LayoutVariableRegister


class ReportManager(QtCore.QObject):
    """Registers custom report variables for
    layout design and handles report generation.
    """
    def __int__(self, parent=None):
        super().__init__(parent)
        self._variable_register = LayoutVariableRegister()

    @property
    def variable_register(self) -> LayoutVariableRegister:
        """Get the instance of the variable register used
        for the management of variables.

        :returns: The register for managing variables in
        report layout scope.
        :rtype: LayoutVariableRegister
        """
        return self._variable_register

    def register_variables(self, layout: QgsPrintLayout):
        """Registers custom variables and their corresponding
        initial values in the layout.

        :param layout: Layout object where the custom
        variables will be registered.
        :type layout: QgsPrintLayout
        """
        pass

    def load_template(self, template_name=None) -> QgsPrintLayout:
        """Loads the template with the given file name in the
        app_data directory and returns the corresponding layout
        object.

        :param template_name: Template name as defined in the
        app_data/reports directory.
        :type template_name: str

        :returns: The layout object corresponding to the template
        file else None if the file does not exist or could not be
        loaded.
        :rtype: QgsPrintLayout
        """
        pass


report_manager = ReportManager()
