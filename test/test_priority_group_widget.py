# coding=utf-8
"""Test priority group widget."""

import unittest

from cplus_plugin.test.utilities_for_testing import get_qgis_app

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()
from cplus_plugin.gui.priority_group_widget import PriorityGroupWidget

from data.priority_weighting_layers import PRIORITY_GROUPS


class TestPriorityGroupWidget(unittest.TestCase):
    """Test priority group widget"""

    def test_setup_priority_group_widget(self):
        """Test setup for priority group widget."""

        for group in PRIORITY_GROUPS:
            priority_widget = PriorityGroupWidget(group)
            group_la = priority_widget.widgets()[0]
            group_slider = priority_widget.widgets()[1]
            group_spin_box = priority_widget.widgets()[2]

            self.assertEqual(group_la.text(), group.get("name"))
            self.assertEqual(group_slider.value(), 0)
            self.assertEqual(group_spin_box.value(), 0)

            # Test changing values by changing the group.

            group["name"] = "Test"
            group["value"] = 5
            priority_widget.set_group(group)

            self.assertEqual(group_la.text(), "Test")
            self.assertEqual(group_slider.value(), 5)
            self.assertEqual(group_spin_box.value(), 5)

            # Setting group value greater than 5, the group slider
            # and group spin box should default to 5.
            group["value"] = 10
            priority_widget.set_group(group)

            self.assertEqual(group_slider.value(), 5)
            self.assertEqual(group_spin_box.value(), 5)

            # Test changing widget values using its component widgets
            group_la.setText("Second Test")
            group_slider.setValue(3)

            self.assertEqual(group_la.text(), "Second Test")
            self.assertEqual(group_slider.value(), 3)
            self.assertEqual(group_spin_box.value(), 3)
