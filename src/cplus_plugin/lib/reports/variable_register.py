# -*- coding: utf-8 -*-
"""
Manages custom variable data for report design and generation.
"""
import typing
from dataclasses import dataclass

from ...conf import Settings, settings_manager


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
        # Setting - organization
        org_var_name = f"{self.var_prefix}_organization"
        org_var_info = self._create_settings_var_info(
            Settings.REPORT_ORGANIZATION, org_var_name
        )
        self._var_infos[org_var_name] = org_var_info

        # Setting - email
        email_var_name = f"{self.var_prefix}_email"
        email_var_info = self._create_settings_var_info(
            Settings.REPORT_CONTACT_EMAIL, email_var_name
        )
        self._var_infos[email_var_name] = email_var_info

        # Setting - website
        web_var_name = f"{self.var_prefix}_website"
        web_var_info = self._create_settings_var_info(
            Settings.REPORT_WEBSITE, web_var_name
        )
        self._var_infos[web_var_name] = web_var_info

        # Setting - logo
        logo_var_name = f"{self.var_prefix}_logo"
        logo_var_info = self._create_settings_var_info(
            Settings.REPORT_LOGO_DIR, logo_var_name
        )
        self._var_infos[logo_var_name] = logo_var_info

        # Setting - footer
        footer_var_name = f"{self.var_prefix}_footer"
        footer_var_info = self._create_settings_var_info(
            Settings.REPORT_FOOTER, footer_var_name
        )
        self._var_infos[footer_var_name] = footer_var_info

        # Setting - disclaimer
        disclaimer_var_name = f"{self.var_prefix}_disclaimer"
        disclaimer_var_info = self._create_settings_var_info(
            Settings.REPORT_DISLAIMER, disclaimer_var_name
        )
        self._var_infos[disclaimer_var_name] = disclaimer_var_info

        # Setting - license
        license_var_name = f"{self.var_prefix}_license"
        license_var_info = self._create_settings_var_info(
            Settings.REPORT_LICENSE, license_var_name
        )
        self._var_infos[license_var_name] = license_var_info

        # Setting - base directory
        base_dir_var_name = f"{self.var_prefix}_base_dir"
        base_dir_var_info = self._create_settings_var_info(
            Settings.BASE_DIR, base_dir_var_name
        )
        self._var_infos[base_dir_var_name] = base_dir_var_info
