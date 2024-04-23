# -*- coding: utf-8 -*-
"""
Unit tests for data validation module.
"""

from unittest import TestCase

from cplus_plugin.lib.validation.configs import (
    crs_validation_config,
    no_data_validation_config,
    raster_validation_config,
)
from cplus_plugin.lib.validation.feedback import ValidationFeedback
from cplus_plugin.lib.validation.manager import ValidationManager
from cplus_plugin.lib.validation.validators import DataValidator, RasterValidator
from cplus_plugin.models.validation import RuleInfo, RuleType

from model_data_for_testing import get_ncs_pathways


class TestDataValidation(TestCase):
    """Tests for data validation module."""

    def test_raster_validator(self):
        """Test if the input NCS datasets are raster layers."""
        ncs_pathways = get_ncs_pathways()
        rule_info = RuleInfo(RuleType.DATA_TYPE, raster_validation_config.rule_name)
        feedback = ValidationFeedback()
        feedback.current_rule = rule_info
        raster_validator = DataValidator.create_rule_validator(
            RuleType.DATA_TYPE, raster_validation_config, feedback
        )
        raster_validator.model_components = ncs_pathways

        _ = raster_validator.run()
        self.assertTrue(raster_validator.result.success)

    def test_crs_validator(self):
        """Test if the input NCS datasets have the same CRS."""
        ncs_pathways = get_ncs_pathways()
        rule_info = RuleInfo(RuleType.CRS, crs_validation_config.rule_name)
        feedback = ValidationFeedback()
        feedback.current_rule = rule_info
        crs_validator = DataValidator.create_rule_validator(
            RuleType.CRS, crs_validation_config, feedback
        )
        crs_validator.model_components = ncs_pathways

        _ = crs_validator.run()
        self.assertTrue(crs_validator.result.success)

    def test_no_data_validator(self):
        """Test if the input NCS datasets have the NoData value as -9999."""
        ncs_pathways = get_ncs_pathways()
        rule_info = RuleInfo(RuleType.CRS, no_data_validation_config.rule_name)
        feedback = ValidationFeedback()
        feedback.current_rule = rule_info
        no_data_validator = DataValidator.create_rule_validator(
            RuleType.NO_DATA_VALUE, no_data_validation_config, feedback
        )
        no_data_validator.model_components = ncs_pathways

        _ = no_data_validator.run()
        self.assertTrue(no_data_validator.result.success)
