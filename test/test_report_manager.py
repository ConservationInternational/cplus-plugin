# -*- coding: utf-8 -*-
"""
Unit test for report manager.
"""

from unittest import TestCase

from qgis.core import QgsFeedback

from cplus_plugin.lib.reports.manager import ReportManager

from model_data_for_testing import get_test_scenario_result
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestReportManager(TestCase):
    """Tests for the report manager."""

    def setUp(self):
        self.rpm = ReportManager()

    def failed_submit_without_base_dir(self):
        """Assert a failed job submit if the BASE_DIR has not been set."""
        scenario_result = get_test_scenario_result()
        report_submit = self.rpm.generate(scenario_result, QgsFeedback())
        self.assertFalse(report_submit.status)
