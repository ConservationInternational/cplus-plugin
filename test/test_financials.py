# -*- coding: utf-8 -*-
"""
Unit tests for financial NPV computations.
"""

import os
import typing
import unittest
from unittest import TestCase

from processing.core.Processing import Processing

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
    QgsRasterLayer,
)

from cplus_plugin.conf import settings_manager, Settings
from cplus_plugin.gui.qgis_cplus_main import QgisCplusMain
from cplus_plugin.lib.financials import (
    calculate_activity_npv,
    compute_discount_value,
    create_npv_pwls,
)
from cplus_plugin.utils import FileUtils

from model_data_for_testing import (
    ACTIVITY_UUID_STR,
    get_activity,
    get_ncs_pathway_npv_collection,
    get_ncs_pathways,
    NCS_PATHWAY_1_NPV,
    NCS_UUID_STR_1,
)
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class ConsoleFeedBack(QgsProcessingFeedback):
    """Logs error information in the standard output device."""

    _errors = []

    def reportError(self, error, fatalError=False):
        print(error)
        self._errors.append(error)


class TestFinancialNpv(TestCase):
    """Tests for financial NPV computations."""

    def setUp(self) -> None:
        Processing.initialize()

        # Required when calculating NPV for pathways in an activity
        settings_manager.save_activity(get_activity())

        # We need to save at least one NCS pathway when
        # retrieving the NPV collection
        settings_manager.save_ncs_pathway(get_ncs_pathways()[0])

    def tearDown(self):
        settings_manager.remove_activity(ACTIVITY_UUID_STR)
        settings_manager.remove_ncs_pathway(NCS_UUID_STR_1)

    def test_get_ncs_pathway_npv_in_collection(self):
        """Test getting the NCS pathway NPV in the NPV collection."""
        npv_collection = get_ncs_pathway_npv_collection()
        pathway_npv = npv_collection.activity_npv(NCS_UUID_STR_1)

        self.assertIsNotNone(pathway_npv)

    def test_discount_rate_calculation(self):
        """Test the computation of the discount rate."""
        discount_rate = compute_discount_value(70000, 48000, 3, 7.0)

        self.assertEqual(round(discount_rate, 2), 19215.65)

    def test_npv_min_max_calculation(self):
        """Test the computation of min/max NPV values in the collection."""
        npv_collection = get_ncs_pathway_npv_collection()
        npv_collection.update_computed_normalization_range()

        self.assertEqual(round(npv_collection.minimum_value, 2), 38767.05)
        self.assertEqual(round(npv_collection.maximum_value, 2), 102307.69)

    def test_npv_normalization_status(self):
        """Test the status of NPV normalization."""
        npv_collection = get_ncs_pathway_npv_collection()
        npv_collection.update_computed_normalization_range()
        normalization_status = npv_collection.normalize_npvs()

        self.assertTrue(normalization_status)

    def test_npv_normalization_value(self):
        """Test the status of NPV normalization."""
        npv_collection = get_ncs_pathway_npv_collection()
        npv_collection.update_computed_normalization_range()
        _ = npv_collection.normalize_npvs()

        ncs_pathway_npv_1 = npv_collection.activity_npv(NCS_UUID_STR_1)
        normalized_npv = round(ncs_pathway_npv_1.params.normalized_npv, 4)
        self.assertEqual(normalized_npv, 0.0259)

    @classmethod
    def _run_npv_pwl_creation(cls, on_finish_func: typing.Callable):
        """Executes function for creating the NPV PWL then runs the user-defined
        call back function once the NPV PWL processing function has successfully
        finished.
        """
        npv_collection = get_ncs_pathway_npv_collection()
        npv_collection.update_computed_normalization_range()
        _ = npv_collection.normalize_npvs()

        npv_processing_context = QgsProcessingContext()
        npv_feedback = ConsoleFeedBack()
        npv_multi_step_feedback = QgsProcessingMultiStepFeedback(
            len(npv_collection.mappings), npv_feedback
        )

        ncs_pathway = get_ncs_pathways(use_projected=True)[0]
        reference_layer = ncs_pathway.to_map_layer()
        reference_crs = reference_layer.crs()
        reference_pixel_size = reference_layer.rasterUnitsPerPixelX()
        reference_extent = reference_layer.extent()
        reference_extent_str = (
            f"{reference_extent.xMinimum()!s},"
            f"{reference_extent.xMaximum()!s},"
            f"{reference_extent.yMinimum()!s},"
            f"{reference_extent.yMaximum()!s}"
        )

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        settings_base_dir = settings_manager.get_value(Settings.BASE_DIR)
        if settings_base_dir != base_dir:
            settings_manager.set_value(Settings.BASE_DIR, base_dir)
        FileUtils.create_pwls_dir(base_dir)

        create_npv_pwls(
            npv_collection,
            npv_processing_context,
            npv_multi_step_feedback,
            npv_feedback,
            reference_crs.authid(),
            reference_pixel_size,
            reference_extent_str,
            on_finish_func,
        )

    def test_create_npv_pwl(self):
        """Test the creation of an NPV PWL raster layer."""

        pwl_layer_path = None

        def on_pwl_layer_created(pathway_npv, pwl_path, algorithm, context, feedback):
            nonlocal pwl_layer_path
            assert pwl_path
            pwl_layer_path = pwl_path

        self._run_npv_pwl_creation(on_pwl_layer_created)

        pwl_exists = os.path.exists(pwl_layer_path)
        pwl_npv_layer = QgsRasterLayer(pwl_layer_path, "Test NPV PWL")

        self.assertTrue(pwl_exists, msg="NPV PWL layer does not exist.")
        self.assertTrue(pwl_npv_layer.isValid(), msg="NPV PWL raster is not valid.")

    def test_npv_pwl_model_creation(self):
        """Test the creation and saving of an NPV PWL data model."""

        main_dock_widget = QgisCplusMain(IFACE, PARENT)

        test_pathway_npv = None

        def proxy_npv_pwl_created(pathway_npv, pwl_path, algorithm, context, feedback):
            nonlocal test_pathway_npv
            nonlocal main_dock_widget
            assert pathway_npv
            if test_pathway_npv is None:
                test_pathway_npv = pathway_npv

            main_dock_widget.on_npv_pwl_created(
                pathway_npv, pwl_path, algorithm, context, feedback
            )

        self._run_npv_pwl_creation(proxy_npv_pwl_created)

        npv_pwl = settings_manager.find_layer_by_name(test_pathway_npv.base_name)

        self.assertIsNotNone(
            npv_pwl, msg="NPV PWL data model was not saved in the settings."
        )

    def test_invalid_ncs_pathway_npv_calculation(self):
        """Test the result of a calculating the NPV of an activity which
        does not exist.
        """
        npv = calculate_activity_npv("4aa9d682-24b5-4014-ab16-f60c0936c39b", 250)

        self.assertEqual(npv, -1.0)

    def test_valid_ncs_pathway_npv_calculation(self):
        """Test the result of a calculating the NPV of an NCS
        pathway which has been defined in the NCS pathway NPV
        collection.
        """
        # Map test pathway to test activity
        activity = settings_manager.get_activity(ACTIVITY_UUID_STR)
        self.assertIsNotNone(activity)

        pathway = settings_manager.get_ncs_pathway(NCS_UUID_STR_1)

        activity.add_ncs_pathway(pathway)
        settings_manager.update_activity(activity)

        npv_collection = get_ncs_pathway_npv_collection()
        npv_collection.update_computed_normalization_range()
        _ = npv_collection.normalize_npvs()

        settings_manager.save_npv_collection(npv_collection)

        area = 2000

        computed_npv = calculate_activity_npv(ACTIVITY_UUID_STR, area)
        reference_npv = NCS_PATHWAY_1_NPV * area

        self.assertEqual(computed_npv, reference_npv)
