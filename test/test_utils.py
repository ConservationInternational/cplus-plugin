# coding=utf-8
"""Tests for the CPLUS plugin utilities.

"""
import unittest

from cplus_plugin.utils import open_documentation


class CplusPluginUtilTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_open_documentation(self):
        # Checks function for opening img in a browser
        result = open_documentation()

        # TODO work out a web browser for testing this utility
        # at the moment only these checks will pass
        self.assertIsNotNone(result)
        self.assertFalse(result)
