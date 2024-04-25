# -*- coding: utf-8 -*-
"""
Unit tests for data validation module.
"""

from unittest import TestCase

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtTest import QSignalSpy

from cplus_plugin.lib.validation.configs import (
    carbon_resolution_validation_config,
    crs_validation_config,
    no_data_validation_config,
    projected_crs_validation_config,
    raster_validation_config,
    resolution_validation_config,
)
from cplus_plugin.lib.validation.feedback import ValidationFeedback
from cplus_plugin.lib.validation.manager import ValidationManager
from cplus_plugin.lib.validation.validators import DataValidator, RasterValidator
from cplus_plugin.models.validation import RuleInfo, RuleType

from model_data_for_testing import get_ncs_pathways
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

    def test_carbon_resolution_validator(self):
        """Test if the input NCS datasets and corresponding carbon layers
        have the same spatial resolution.
        """
        ncs_pathways = get_ncs_pathways()
        rule_info = RuleInfo(
            RuleType.CARBON_RESOLUTION, carbon_resolution_validation_config.rule_name
        )
        feedback = ValidationFeedback()
        feedback.current_rule = rule_info
        carbon_resolution_validator = DataValidator.create_rule_validator(
            RuleType.CARBON_RESOLUTION, carbon_resolution_validation_config, feedback
        )
        carbon_resolution_validator.model_components = ncs_pathways

        _ = carbon_resolution_validator.run()
        self.assertTrue(carbon_resolution_validator.result.success)

    def test_projected_crs_validator(self):
        """Test if the input NCS datasets have a projected CRS."""
        ncs_pathways = get_ncs_pathways()
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

    def test_manager_submit_result_with_one_pathway(self):
        """Test if a request for validating one NCS pathway, through
        the validation manager, failed.
        """
        validation_manager = ValidationManager()
        ncs_pathways = get_ncs_pathways()
        one_pathway = [ncs_pathways[0]]
        result = validation_manager.validate_ncs_pathways(one_pathway)
        self.assertFalse(result.success)

    def test_manager_validation_result(self):
        """Test the validation result through the validation manager."""
        validation_result = None
        validation_manager = ValidationManager()

        def validation_completed(task_id):
            nonlocal validation_result
            nonlocal validation_manager

            validation_result = validation_manager.ncs_results()[0]

        validation_manager.validation_completed.connect(validation_completed)
        ncs_pathways = get_ncs_pathways()
        submit_result = validation_manager.validate_ncs_pathways(ncs_pathways)

        while not validation_manager.is_validation_complete(submit_result):
            QCoreApplication.processEvents()

        self.assertIsNotNone(validation_result)
