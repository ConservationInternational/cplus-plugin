# -*- coding: utf-8 -*-
"""
Functions for providing model test data.
"""
import os
from uuid import UUID

from qgis.core import QgsRasterLayer

from cplus_plugin.definitions.constants import (
    CARBON_COEFFICIENT_ATTRIBUTE,
    CARBON_PATHS_ATTRIBUTE,
    NAME_ATTRIBUTE,
    DESCRIPTION_ATTRIBUTE,
    LAYER_TYPE_ATTRIBUTE,
    PATH_ATTRIBUTE,
    PRIORITY_LAYERS_SEGMENT,
    USER_DEFINED_ATTRIBUTE,
    UUID_ATTRIBUTE,
)
from cplus_plugin.definitions.defaults import PILOT_AREA_EXTENT
from cplus_plugin.models.base import (
    Activity,
    LayerType,
    NcsPathway,
    Scenario,
    ScenarioResult,
    SpatialExtent,
)


VALID_NCS_UUID_STR = "b5338edf-f3cc-4040-867d-be9651a28b63"
INVALID_NCS_UUID_STR = "4c6b31a1-3ff3-43b2-bfe2-45519a975955"
ACTIVITY_UUID_STR = "01e3a612-118d-4d94-9a5a-09c4b9168288"
TEST_RASTER_PATH = os.path.join(os.path.dirname(__file__), "tenbytenraster.tif")
SCENARIO_UUID_STR = "6cf5b355-f605-4de5-98b1-64936d473f82"


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


def get_activity() -> Activity:
    """Creates a test activity object."""
    return Activity(
        UUID(ACTIVITY_UUID_STR),
        "Test Activity",
        "Description for test activity",
        TEST_RASTER_PATH,
        LayerType.RASTER,
        True,
    )


def get_test_layer() -> QgsRasterLayer:
    """Returns the test raster layer."""
    return QgsRasterLayer(TEST_RASTER_PATH, "Test Layer")


def get_test_scenario() -> Scenario:
    """Returns the test Scenario object."""
    extent_list = PILOT_AREA_EXTENT["coordinates"]
    sp_extent = SpatialExtent(
        bbox=[extent_list[3], extent_list[2], extent_list[1], extent_list[0]]
    )
    return Scenario(
        UUID(SCENARIO_UUID_STR),
        "Test Scenario" "Test scenario description",
        sp_extent,
        [get_activity()],
        [
            [
                {
                    "name": "Biodiversity",
                    "value": 50,
                    "description": "Test biodiversity group",
                }
            ]
        ],
    )


def get_test_scenario_result() -> ScenarioResult:
    """Returns a test scenario result object."""
    return ScenarioResult(get_test_scenario())


NCS_PATHWAY_DICT = {
    UUID_ATTRIBUTE: UUID(VALID_NCS_UUID_STR),
    NAME_ATTRIBUTE: "Valid NCS Pathway",
    DESCRIPTION_ATTRIBUTE: "Description for valid NCS",
    PATH_ATTRIBUTE: TEST_RASTER_PATH,
    LAYER_TYPE_ATTRIBUTE: 0,
    USER_DEFINED_ATTRIBUTE: True,
    CARBON_PATHS_ATTRIBUTE: [],
}
