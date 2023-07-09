# -*- coding: utf-8 -*-
"""
Manages custom variable data for report design and generation.
"""
import typing
from dataclasses import dataclass

from ...conf import Settings, settings_manager
from ...models.base import ImplementationModel
from ...utils import tr


@dataclass
class _CplusVariableInfo:
    """Contains information about layout variables."""

    name: str
    # Used on first time use in the layout.
    init_value: str
    # Used if final value cannot be processed or used.
    default_value: object
    final_value: object

    def process_input(self, value: object) -> object:
        """Format value from an external source for use as the
        final value.

        Default implementation does nothing and returns the
        input value.

        :param value: Source value to be processed for use as
        the final value.
        :type value: object

        :returns: Value that can be used in a format or type
        expected for the final value.
        :rtype: object
        """
        return value


class LayoutVariableRegister:
    """Manages variables and their corresponding values for use in layout
    design and report generation.
    """

    var_prefix = "cplus"

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

    @classmethod
    def _create_settings_var_info(
        cls, settings_type: Settings, variable_name: str
    ) -> _CplusVariableInfo:
        """Create a variable info object for a
        settings type.
        """
        settings_value = settings_manager.get_value(settings_type)

        return _CplusVariableInfo(
            variable_name, settings_value, settings_value, settings_value
        )

    def _init_vars(self):
        """Initialize variable information."""
        setting_str = "setting"
        # Setting - organization
        org_var_name = f"{self.var_prefix}_{setting_str}_organization"
        org_var_info = self._create_settings_var_info(
            Settings.REPORT_ORGANIZATION, org_var_name
        )
        self._var_infos[org_var_name] = org_var_info

        # Setting - email
        email_var_name = f"{self.var_prefix}_{setting_str}_email"
        email_var_info = self._create_settings_var_info(
            Settings.REPORT_CONTACT_EMAIL, email_var_name
        )
        self._var_infos[email_var_name] = email_var_info

        # Setting - website
        web_var_name = f"{self.var_prefix}_{setting_str}_website"
        web_var_info = self._create_settings_var_info(
            Settings.REPORT_WEBSITE, web_var_name
        )
        self._var_infos[web_var_name] = web_var_info

        # Setting - logo
        logo_var_name = f"{self.var_prefix}_{setting_str}_logo"
        logo_var_info = self._create_settings_var_info(
            Settings.REPORT_LOGO_DIR, logo_var_name
        )
        self._var_infos[logo_var_name] = logo_var_info

        # Setting - footer
        footer_var_name = f"{self.var_prefix}_{setting_str}_footer"
        footer_var_info = self._create_settings_var_info(
            Settings.REPORT_FOOTER, footer_var_name
        )
        self._var_infos[footer_var_name] = footer_var_info

        # Setting - disclaimer
        disclaimer_var_name = f"{self.var_prefix}_{setting_str}_disclaimer"
        disclaimer_var_info = self._create_settings_var_info(
            Settings.REPORT_DISLAIMER, disclaimer_var_name
        )
        self._var_infos[disclaimer_var_name] = disclaimer_var_info

        # Setting - license
        license_var_name = f"{self.var_prefix}_{setting_str}_license"
        license_var_info = self._create_settings_var_info(
            Settings.REPORT_LICENSE, license_var_name
        )
        self._var_infos[license_var_name] = license_var_info

        # Setting - base directory
        base_dir_var_name = f"{self.var_prefix}_{setting_str}_base_dir"
        base_dir_var_info = self._create_settings_var_info(
            Settings.BASE_DIR, base_dir_var_name
        )
        self._var_infos[base_dir_var_name] = base_dir_var_info

        # Scenario
        init_msg = tr("Scenario name will be inserted here")
        scenario_var_info = _CplusVariableInfo(
            f"{self.var_prefix}_scenario_name", f"[{init_msg}]", "", ""
        )
        self._var_infos[scenario_var_info.name] = scenario_var_info

        # Implementation model variables
        self._create_implementation_models_var_infos()

    def _create_implementation_models_var_infos(self):
        """Add variable info objects for implementation models."""
        imp_models = settings_manager.get_all_implementation_models()
        for im_model in imp_models:
            normalized_name = im_model.name.replace(" ", "_").lower()
            im_model_name = f"model_{normalized_name}"
            # Implementation model name only
            im_var_info = _CplusVariableInfo(
                f"{self.var_prefix}_{im_model_name}", f"{im_model.name}", "", ""
            )
            self._var_infos[im_var_info.name] = im_var_info

            # Implementation model with NCS pathway names
            ncs_pathway_tr = tr("NCS pathway")
            with_tr = tr("with")
            init_value = create_bulleted_text(
                im_model.name, [f"{ncs_pathway_tr} 1", f"{ncs_pathway_tr} 2", "..."]
            )
            im_ncs_var_info = _CplusVariableInfo(
                f"{self.var_prefix}_{im_model_name}_{with_tr}_ncs", init_value, "", ""
            )
            self._var_infos[im_ncs_var_info.name] = im_ncs_var_info


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

    return f"{main_text}\n- {bulleted_items}"
