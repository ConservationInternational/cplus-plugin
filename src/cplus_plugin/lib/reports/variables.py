# -*- coding: utf-8 -*-
"""
Manages custom variable data for report design and generation.
"""
import typing
from dataclasses import dataclass, field

from qgis.core import QgsExpressionContextUtils, QgsPrintLayout

from ...conf import Settings, settings_manager
from ...models.report import ReportContext
from ...utils import tr


@dataclass
class CplusVariableInfo:
    """Contains information about a CPLUS variable
    within a layout scope.
    """

    name: str
    # Applied on first time use of the variable in the layout.
    init_value: str
    # Used if final value cannot be processed or used.
    default_value: object
    final_value: object

    def update_final_value(self, context: ReportContext):
        """Computes the final value of the variable to be used
        in the layout.

        Default implementation does nothing.

        :param context: Report context object used to compute the
        final variable value.
        :type context: ReportContext
        """
        pass


@dataclass
class SettingsVariableInfo(CplusVariableInfo):
    """Metadata for a settings-related variable."""

    settings_type: Settings
    init_value: str = field(init=False)
    default_value: str = field(init=False)
    final_value: object = field(init=False)

    def __post_init__(self):
        # Prefix variable name with 'cplus_setting'
        prefix = "cplus_setting"
        if not self.name.startswith(prefix):
            self.name = f"{prefix}_{self.name}"

        settings_value = self._get_setting_value()
        self.init_value = settings_value
        self.default_value = settings_value

    def _get_setting_value(self) -> str:
        """Returns the settings value."""
        return settings_manager.get_value(self.settings_type, "")

    def update_final_value(self, context: ReportContext):
        """Computes the final value of the variable to be used
        in the layout.

        Fetches the latest settings value.

        :param context: Report context object used to compute the
        final variable value.
        :type context: ReportContext
        """
        self.final_value = self._get_setting_value()


@dataclass
class NoneValueSettingsVariableInfo(SettingsVariableInfo):
    """Sets final value as "N/A" if there is no text specified in
    the settings.
    """

    def update_final_value(self, context: ReportContext):
        """Computes the final value of the variable to be used
        in the layout.

        Fetches the latest settings value.

        :param context: Report context object used to compute the
        final variable value.
        :type context: ReportContext
        """
        settings_value = self._get_setting_value()
        self.final_value = settings_value if settings_value else tr("N/A")


@dataclass
class ScenarioNameVariableInfo(CplusVariableInfo):
    """Metadata for a scenario name variable."""

    name: str = field(init=False)
    init_value: str = field(init=False)
    default_value: str = field(init=False)
    final_value: object = field(init=False)

    def __post_init__(self):
        # Prefix variable name with 'cplus_setting'
        self.name = "cplus_model_scenario_name"
        msg = tr("Scenario name will be inserted here")
        self.init_value = msg
        self.default_value = ""
        self.final_value = ""

    def update_final_value(self, context: ReportContext):
        """Set the scenario name."""
        self.final_value = context.scenario.name


@dataclass
class ScenarioDescriptionVariableInfo(CplusVariableInfo):
    """Metadata for a scenario description variable."""

    name: str = field(init=False)
    init_value: str = field(init=False)
    default_value: str = field(init=False)
    final_value: object = field(init=False)

    def __post_init__(self):
        # Prefix variable name with 'cplus_setting'
        self.name = "cplus_model_scenario_description"
        msg = tr("Scenario description will be inserted here")
        self.init_value = msg
        self.default_value = ""
        self.final_value = ""

    def update_final_value(self, context: ReportContext):
        """Set the scenario description."""
        self.final_value = context.scenario.description


class LayoutVariableRegister:
    """Manages variables and their corresponding values for use in layout
    design and report generation.
    """

    VAR_PREFIX = "cplus"
    VAR_NAMES_PROPERTY = "variableNames"
    VAR_VALUES_PROPERTY = "variableValues"
    VAR_CPLUS_REPORT_PROPERTY = "analysisReport"

    def __init__(self):
        self._var_infos = {}
        self._init_vars()

    @property
    def variable_names(self) -> typing.List[str]:
        """Gets the names of the registered variables.

        :returns: A collection of registered variable names.
        :rtype: list
        """
        return list(self._var_infos.keys())

    @property
    def var_name_init_values(self) -> dict:
        """Creates a collection of variable names and
        their corresponding initial values.

        :returns: Collection of variable names and
        corresponding initial values.
        :rtype: dict
        """
        return {v_name: v_info.init_value for v_name, v_info in self._var_infos.items()}

    def _init_vars(self):
        """Initialize variable information."""
        # Setting - organization
        org_var_info = SettingsVariableInfo(
            "organization", Settings.REPORT_ORGANIZATION
        )
        self._var_infos[org_var_info.name] = org_var_info

        # Setting - email
        email_var_info = SettingsVariableInfo("email", Settings.REPORT_CONTACT_EMAIL)
        self._var_infos[email_var_info.name] = email_var_info

        # Setting - website
        web_var_info = SettingsVariableInfo("website", Settings.REPORT_WEBSITE)
        self._var_infos[web_var_info.name] = web_var_info

        # Setting - logo
        logo_var_info = SettingsVariableInfo("custom_logo", Settings.REPORT_LOGO_DIR)
        self._var_infos[logo_var_info.name] = logo_var_info

        # Setting - CPLUS logo
        cplus_logo_var_info = SettingsVariableInfo(
            "cplus_logo", Settings.REPORT_CPLUS_LOGO
        )
        self._var_infos[cplus_logo_var_info.name] = cplus_logo_var_info

        # Setting - CI logo
        ci_logo_var_info = SettingsVariableInfo("ci_logo", Settings.REPORT_CI_LOGO)
        self._var_infos[ci_logo_var_info.name] = ci_logo_var_info

        # Setting - footer
        footer_var_info = SettingsVariableInfo("footer", Settings.REPORT_FOOTER)
        self._var_infos[footer_var_info.name] = footer_var_info

        # Setting - disclaimer
        disclaimer_var_info = SettingsVariableInfo(
            "disclaimer", Settings.REPORT_DISCLAIMER
        )
        self._var_infos[disclaimer_var_info.name] = disclaimer_var_info

        # Setting - license
        license_var_info = SettingsVariableInfo("license", Settings.REPORT_LICENSE)
        self._var_infos[license_var_info.name] = license_var_info

        # Setting - base directory
        base_dir_var_info = SettingsVariableInfo("base_dir", Settings.BASE_DIR)
        self._var_infos[base_dir_var_info.name] = base_dir_var_info

        # Scenario name
        scenario_name_var_info = ScenarioNameVariableInfo()
        self._var_infos[scenario_name_var_info.name] = scenario_name_var_info

        # Scenario description
        scenario_desc_var_info = ScenarioDescriptionVariableInfo()
        self._var_infos[scenario_desc_var_info.name] = scenario_desc_var_info

        # Setting - report stakeholders
        stakeholders_var_info = NoneValueSettingsVariableInfo(
            "stakeholders_relationships", Settings.REPORT_STAKEHOLDERS
        )
        self._var_infos[stakeholders_var_info.name] = stakeholders_var_info

        # Setting - report cultural policies
        cultural_policies_var_info = NoneValueSettingsVariableInfo(
            "cultural_policies", Settings.REPORT_CULTURE_POLICIES
        )
        self._var_infos[cultural_policies_var_info.name] = cultural_policies_var_info

        # Setting - report cultural considerations
        culture_considerations_var_info = NoneValueSettingsVariableInfo(
            "cultural_considerations", Settings.REPORT_CULTURE_CONSIDERATIONS
        )
        self._var_infos[
            culture_considerations_var_info.name
        ] = culture_considerations_var_info

    def _create_activities_var_infos(self):
        """Add variable info objects for activities."""
        activities = settings_manager.get_all_activities()
        for activity in activities:
            normalized_name = activity.name.replace(" ", "_").lower()
            activity_name = f"activity_{normalized_name}"
            # Activity name only
            activity_var_info = CplusVariableInfo(
                f"{self.VAR_PREFIX}_{activity_name}", f"{activity.name}", "", ""
            )
            self._var_infos[activity_var_info.name] = activity_var_info

            # Activity with NCS pathway names
            ncs_pathway_tr = tr("NCS pathway")
            with_tr = tr("with")
            init_value = create_bulleted_text(
                activity.name, [f"{ncs_pathway_tr} 1", f"{ncs_pathway_tr} 2", "..."]
            )
            activity_ncs_var_info = CplusVariableInfo(
                f"{self.VAR_PREFIX}_{activity_name}_{with_tr}_ncs", init_value, "", ""
            )
            self._var_infos[activity_ncs_var_info.name] = activity_ncs_var_info

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
        cplus_var_names = self.variable_names
        var_names = layout.customProperty(self.VAR_NAMES_PROPERTY, list())
        var_values = layout.customProperty(self.VAR_VALUES_PROPERTY, list())

        # Remove only cplus variable names and values
        for cvn in cplus_var_names:
            self.remove_var_name_in_collection(cvn, var_names, var_values)

        return var_names, var_values

    def is_analysis_report(self, layout: QgsPrintLayout) -> bool:
        """Checks whether the layout has been produced from a report
        generation process.

        :param layout: Layout to check whether its from a report
        generation process.
        :type layout: QgsPrintLayout

        :returns: True if the layout is from a report generation
        process, else False.
        :rtype: bool
        """
        return layout.customProperty(self.VAR_CPLUS_REPORT_PROPERTY, False)

    def register_variables(self, layout: QgsPrintLayout):
        """Registers custom variables and their corresponding
        initial values in the layout.

        :param layout: Layout object where the custom
        variables will be registered.
        :type layout: QgsPrintLayout
        """
        # If layout from analysis process, do not register
        # the variables.
        if self.is_analysis_report(layout):
            return

        # Remove any duplicate cplus variable names and values
        var_names, var_values = self.remove_variables(layout)

        # Get cplus variable names and corresponding initial values
        var_name_init_values = self.var_name_init_values
        for var_name, init_value in var_name_init_values.items():
            var_names.append(var_name)
            var_values.append(init_value)

        layout.setCustomProperty(self.VAR_NAMES_PROPERTY, var_names)
        layout.setCustomProperty(self.VAR_VALUES_PROPERTY, var_values)

    def set_report_flag(self, layout: QgsPrintLayout):
        """Set a flag indicating that the layout has been produced
        from a report generation process.

        :param layout: Layout to add the flag as a custom property.
        :type layout: QgsPrintLayout
        """
        layout.setCustomProperty(self.VAR_CPLUS_REPORT_PROPERTY, True)

    def update_variables(self, layout: QgsPrintLayout, context: ReportContext):
        """Update the values for the CPLUS variables in the layout.

        :param layout: Layout object whose CPLUS variable values
        will be updated.
        :type layout: QgsPrintLayout

        :param context: Context object containing the report information that
        will be used for computing the final value of the variable during
        the report generation process.
        :type context: ReportContext
        """
        exp_scope = QgsExpressionContextUtils.layoutScope(layout)
        var_names = exp_scope.variableNames()
        var_values = []
        vn = list(self._var_infos.keys())
        for name in var_names:
            if name in self._var_infos:
                var_info = self._var_infos[name]
                var_info.update_final_value(context)
                var_values.append(var_info.final_value)
            else:
                if not exp_scope.hasVariable(name):
                    continue
                value = exp_scope.variable(name)
                var_values.append(value)

        layout.setCustomProperty(self.VAR_NAMES_PROPERTY, var_names)
        layout.setCustomProperty(self.VAR_VALUES_PROPERTY, var_values)
        layout.refresh()


def create_bulleted_text(main_text: str, bulleted_items: typing.List[str]) -> str:
    """Returns string containing text and bulleted/dashed text
    below it.

    :param main_text: Primary non-bulleted text.
    :type main_text: str

    :param bulleted_items: List containing bulleted items that will
    be rendered below the main text.
    :type bulleted_items: list

    :returns: Text containing primary text with bulleted items
    below it.
    :rtype: str
    """
    bulleted_items = "\n- ".join(bulleted_items)

    if not main_text:
        return f"- {bulleted_items}"

    return f"{main_text}\n- {bulleted_items}"
