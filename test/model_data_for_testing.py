# -*- coding: utf-8 -*-
"""
Functions for providing model test data.
"""
import os
from uuid import UUID

from qgis.core import QgsRasterLayer

from cplus_plugin.models.base import ImplementationModel, LayerType, NcsPathway


VALID_NCS_UUID_STR = "b5338edf-f3cc-4040-867d-be9651a28b63"
INVALID_NCS_UUID_STR = "4c6b31a1-3ff3-43b2-bfe2-45519a975955"
IMPLEMENTATION_MODEL_UUID_STR = "01e3a612-118d-4d94-9a5a-09c4b9168288"
TEST_RASTER_PATH = os.path.join(os.path.dirname(__file__), "tenbytenraster.tif")


def get_valid_ncs_pathway() -> NcsPathway:
    """Creates a valid NCS pathway object."""
    return NcsPathway(
        UUID(VALID_NCS_UUID_STR),
        "Valid NCS Pathway",
        "Description for valid NCS",
        TEST_RASTER_PATH,
        LayerType.RASTER,
        True,
        carbon_paths=[],
    )


def get_invalid_ncs_pathway() -> NcsPathway:
    """Creates an invalid NCS pathway object i.e. path not set."""
    return NcsPathway(
        UUID(INVALID_NCS_UUID_STR),
        "Invalid NCS Pathway",
        "Description for invalid NCS",
        "",
    )


def get_ncs_pathway_with_valid_carbon() -> NcsPathway:
    """Creates a valid NCS pathway object with a valid carbon layer."""
    return NcsPathway(
        UUID(VALID_NCS_UUID_STR),
        "Valid NCS Pathway",
        "Description for valid NCS",
        TEST_RASTER_PATH,
        LayerType.RASTER,
        True,
        carbon_paths=[TEST_RASTER_PATH],
    )


def get_ncs_pathway_with_invalid_carbon() -> NcsPathway:
    """Creates an NCS pathway object with an invalid carbon layer."""
    return NcsPathway(
        UUID(VALID_NCS_UUID_STR),
        "Invalid NCS Pathway",
        "Description for invalid NCS",
        TEST_RASTER_PATH,
        LayerType.RASTER,
        True,
        carbon_paths=["tenbytenraster"],
    )


def get_implementation_model() -> ImplementationModel:
    """Creates a test ImplementationModel object."""
    return ImplementationModel(
        UUID(IMPLEMENTATION_MODEL_UUID_STR),
        "Test Implementation Model",
        "Description for test implementation model",
        TEST_RASTER_PATH,
        LayerType.RASTER,
        True,
    )


def get_test_layer() -> QgsRasterLayer:
    """Returns the test raster layer."""
    return QgsRasterLayer(TEST_RASTER_PATH, "Test Layer")


NCS_PATHWAY_DICT = {
    "uuid": UUID(VALID_NCS_UUID_STR),
    "name": "Valid NCS Pathway",
    "description": "Description for valid NCS",
    "path": TEST_RASTER_PATH,
    "layer_type": 0,
    "user_defined": True,
    "carbon_paths": [],
}
