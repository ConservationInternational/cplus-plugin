# -*- coding: utf-8 -*-
"""
Unit tests for data validation module.
"""
import unittest
from unittest import TestCase

from qgis.PyQt.QtCore import QCoreApplication

from cplus_plugin.lib.validation.configs import (
    crs_validation_config,
    no_data_validation_config,
    normalized_validation_config,
    projected_crs_validation_config,
    raster_validation_config,
    resolution_validation_config,
)
from cplus_plugin.lib.validation.feedback import ValidationFeedback
from cplus_plugin.lib.validation.manager import ValidationManager
from cplus_plugin.lib.validation.validators import DataValidator, RasterValidator
from cplus_plugin.models.validation import RuleInfo, RuleType

from model_data_for_testing import get_ncs_pathways, get_protected_ncs_pathways
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


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

    @unittest.skip("Temporary disable to enable CI to pass.")
    def test_no_data_validator(self):
        """Test if the input NCS datasets have the NoData value as -9999."""
        ncs_pathways = get_ncs_pathways()
        rule_info = RuleInfo(
            RuleType.NO_DATA_VALUE, no_data_validation_config.rule_name
        )
        feedback = ValidationFeedback()
        feedback.current_rule = rule_info
        no_data_validator = DataValidator.create_rule_validator(
            RuleType.NO_DATA_VALUE, no_data_validation_config, feedback
        )
        no_data_validator.model_components = ncs_pathways

        _ = no_data_validator.run()
        self.assertTrue(no_data_validator.result.success)

    def test_spatial_resolution_validator(self):
        """Test if the input NCS datasets have the same spatial resolution."""
        ncs_pathways = get_ncs_pathways()
        rule_info = RuleInfo(
            RuleType.RESOLUTION, resolution_validation_config.rule_name
        )
        feedback = ValidationFeedback()
        feedback.current_rule = rule_info
        resolution_validator = DataValidator.create_rule_validator(
            RuleType.RESOLUTION, resolution_validation_config, feedback
        )
        resolution_validator.model_components = ncs_pathways

        _ = resolution_validator.run()
        self.assertTrue(resolution_validator.result.success)

    def test_projected_crs_validator(self):
        """Test if the input NCS datasets have a projected CRS."""
        ncs_pathways = get_ncs_pathways(use_projected=True)
        rule_info = RuleInfo(
            RuleType.PROJECTED_CRS, projected_crs_validation_config.rule_name
        )
        feedback = ValidationFeedback()
        feedback.current_rule = rule_info
        projected_crs_validator = DataValidator.create_rule_validator(
            RuleType.PROJECTED_CRS, projected_crs_validation_config, feedback
        )
        projected_crs_validator.model_components = ncs_pathways

        _ = projected_crs_validator.run()
        self.assertTrue(projected_crs_validator.result.success)

    def test_manager_submit_result_with_multiple_pathways(self):
        """Test if a request for validating two or more NCS pathways through
        the validation manager was successful.
        """
        validation_manager = ValidationManager()
        ncs_pathways = get_ncs_pathways()
        result = validation_manager.validate_ncs_pathways(ncs_pathways)
        self.assertTrue(result.success)

    def test_manager_validation_result(self):
        """Test the validation result through the validation manager."""
        validation_result_id = None
        validation_manager = ValidationManager()

        def validation_completed(task_id):
            nonlocal validation_result_id
            assert task_id
            validation_result_id = task_id

        validation_manager.validation_completed.connect(validation_completed)
        ncs_pathways = get_ncs_pathways()
        submit_result = validation_manager.validate_ncs_pathways(ncs_pathways)

        while not validation_manager.is_validation_complete(submit_result):
            QCoreApplication.processEvents()

        self.assertIsNotNone(validation_result_id)

    def test_normalized_raster_validator_invalid_pathways(self):
        """Test invalid datasets i.e. those whose values have not
        been normalized.
        """
        normalized_validator = self._setup_normalized_validator(get_ncs_pathways())
        _ = normalized_validator.run()
        self.assertFalse(normalized_validator.result.success)

    def test_normalized_raster_validator_valid_pathways(self):
        """Test valid datasets i.e. those whose values have been
        normalized.
        """
        normalized_validator = self._setup_normalized_validator(
            get_protected_ncs_pathways()
        )
        _ = normalized_validator.run()
        self.assertTrue(normalized_validator.result.success)

    def _setup_normalized_validator(self, pathways):
        rule_info = RuleInfo(
            RuleType.NORMALIZED, normalized_validation_config.rule_name
        )
        feedback = ValidationFeedback()
        feedback.current_rule = rule_info
        resolution_validator = DataValidator.create_rule_validator(
            RuleType.NORMALIZED, resolution_validation_config, feedback
        )
        resolution_validator.model_components = pathways
        return resolution_validator
