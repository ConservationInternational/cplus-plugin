# -*- coding: utf-8 -*-
"""
Unit test for report manager.
"""
import os
from unittest import TestCase

from qgis.core import QgsFeedback

from qgis.PyQt import QtCore

from cplus_plugin.conf import (
    settings_manager,
    Settings,
)
from cplus_plugin.lib.reports.manager import ReportManager

from model_data_for_testing import get_test_scenario_result
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestReportManager(TestCase):
    """Tests for the report manager."""

    def failed_submit_without_base_dir(self):
        """Assert a failed job submit if the BASE_DIR has not been set."""
        rpm = ReportManager()
        scenario_result = get_test_scenario_result()
        report_submit = rpm.generate(scenario_result, QgsFeedback())
        self.assertFalse(report_submit.status)

    def successful_submit_when_base_dir_set(self):
        """Assert a successful job submit when the BASE_DIR has been set."""
        rpm = ReportManager()
        base_dir = os.path.normpath(f"{QtCore.QDir.homePath()}/cplus_base")
        settings_manager.set_value(Settings.BASE_DIR, str(base_dir))
        scenario_result = get_test_scenario_result()
        report_submit = rpm.generate(scenario_result, QgsFeedback())
        self.assertTrue(report_submit.status)
