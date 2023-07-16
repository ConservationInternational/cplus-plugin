# -*- coding: utf-8 -*-
"""
Registers custom report variables for layout design
and handles report generation.
"""
import typing

from qgis.PyQt import QtCore

from qgis.core import QgsPrintLayout

from ...models.report import ReportContext, ReportResult
from ...utils import tr
from .variables import LayoutVariableRegister


class ReportManager(QtCore.QObject):
    """Registers custom report variables for
    layout design and handles report generation.
    """

    VAR_NAMES_PROPERTY = "variableNames"
    VAR_VALUES_PROPERTY = "variableValues"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._variable_register = LayoutVariableRegister()
        self.report_name = tr("Scenario Analysis Report")

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
        # Remove any duplicate cplus variable names and values
        var_names, var_values = self.remove_variables(layout)

        # Get cplus variable names and corresponding initial values
        var_name_init_values = self._variable_register.var_name_init_values
        for var_name, init_value in var_name_init_values.items():
            var_names.append(var_name)
            var_values.append(init_value)

        layout.setCustomProperty(self.VAR_NAMES_PROPERTY, var_names)
        layout.setCustomProperty(self.VAR_VALUES_PROPERTY, var_values)

    def remove_variables(
        self, layout: QgsPrintLayout
    ) -> typing.Tuple[typing.List, typing.List]:
        """Removes duplicate variable names from the layout,
        this is done prior to registering new ones.

        :param layout: Layout whose cplus variables are to be removed.
        :type layout: QgsPrintLayout

        :returns: Tuple only containing non-cplus variable names
        and corresponding values respectively.
        :rtype: tuple
        """
        cplus_var_names = self._variable_register.variable_names
        var_names = layout.customProperty(self.VAR_NAMES_PROPERTY, list())
        var_values = layout.customProperty(self.VAR_VALUES_PROPERTY, list())

        # Remove only cplus variable names and values
        for cvn in cplus_var_names:
            self.remove_var_name_in_collection(cvn, var_names, var_values)

        return var_names, var_values

    @classmethod
    def remove_var_name_in_collection(
        cls,
        cplus_var_name: str,
        layout_var_names: typing.List[str],
        layout_var_values: typing.List[str],
    ):
        """Remove cplus variable name matches and corresponding
        values in the layout variable name/value mapping.
        """
        while cplus_var_name in layout_var_names:
            idx = layout_var_names.index(cplus_var_name)
            _ = layout_var_names.pop(idx)
            _ = layout_var_values.pop(idx)

    def generate(self) -> ReportResult:
        """Initiates the report generation process using information
        resulting from the scenario analysis.

        :returns: Result from the report generation process.
        :rtype: ReportResult
        """
        pass

    def open_layout_designer(self, result: ReportResult) -> bool:
        """Opens the analysis report in the layout designer. The
        layout needs to exist in the currently loaded project.

        :param result: Result object from the report generation
        process.
        :type result: ReportResult

        :returns: True if the layout was successfully loaded, else
        False if the result from the generation process was False
        or if the layout does not exist in the current project.
        :rtype: bool
        """
        pass

    def view_pdf(self, result: ReportResult) -> bool:
        """Opens the analysis in the host's default PDF viewer.

        :param result: Result object from the report generation
        process.
        :type result: ReportResult

        :returns: True if the PDF was successfully loaded, else
        False if the result from the generation process was False.
        :rtype: bool
        """
        pass


report_manager = ReportManager()
