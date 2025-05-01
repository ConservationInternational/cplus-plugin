# -*- coding: utf-8 -*-
"""
Functions for providing model test data.
"""
import os
import typing
from uuid import UUID

from qgis.core import QgsRasterLayer

from cplus_plugin.definitions.constants import (
    CARBON_COEFFICIENT_ATTRIBUTE,
    CARBON_PATHS_ATTRIBUTE,
    NAME_ATTRIBUTE,
    DESCRIPTION_ATTRIBUTE,
    LAYER_TYPE_ATTRIBUTE,
    PATH_ATTRIBUTE,
    PATHWAY_TYPE_ATTRIBUTE,
    PRIORITY_LAYERS_SEGMENT,
    USER_DEFINED_ATTRIBUTE,
    UUID_ATTRIBUTE,
)
from cplus_plugin.definitions.defaults import PILOT_AREA_EXTENT
from cplus_plugin.models.base import (
    Activity,
    LayerType,
    NcsPathway,
    NcsPathwayType,
    PriorityLayerType,
    Scenario,
    ScenarioResult,
    SpatialExtent,
)
from cplus_plugin.models.financial import (
    NcsPathwayNpv,
    NcsPathwayNpvCollection,
    NpvParameters,
)
from cplus_plugin.models.report import (
    ActivityColumnMetric,
    MetricColumn,
    MetricConfiguration,
    MetricType,
)


VALID_NCS_UUID_STR = "b5338edf-f3cc-4040-867d-be9651a28b63"
INVALID_NCS_UUID_STR = "4c6b31a1-3ff3-43b2-bfe2-45519a975955"
ACTIVITY_UUID_STR = "01e3a612-118d-4d94-9a5a-09c4b9168288"
ACTIVITY_2_UUID_STR = "1fbfb272-0b8d-409e-8cf6-db9f1f63fce2"
ACTIVITY_3_UUID_STR = "7b5c2ae0-aeea-4006-a3f8-42ee7cd81bcf"
TEST_RASTER_PATH = os.path.join(os.path.dirname(__file__), "tenbytenraster.tif")
SCENARIO_UUID_STR = "6cf5b355-f605-4de5-98b1-64936d473f82"
METRIC_COLUMN_NAME = "Financials"

NCS_UUID_STR_1 = "51f561d1-32eb-4104-9408-d5b66ce6b651"
NCS_UUID_STR_2 = "424e076e-61b7-4116-a5a9-d2a7b4c2574e"
NCS_UUID_STR_3 = "5c42b644-3d21-4081-9206-28e872efca73"

PROTECTED_NCS_UUID_STR_1 = "2ac8de1d-2181-4f84-83b5-fbe6e600a3ab"
PROTECTED_NCS_UUID_STR_2 = "f9c7b0a2-dc35-4d40-aa1f-c871f06e7da7"

NCS_PATHWAY_1_NPV = 40410.23

PWL_UUID_STR = "1f894ea8-32b4-4cac-9b7a-d313db51f816"


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
        pathway_type=NcsPathwayType.MANAGE,
        priority_layers=[],
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


def get_ncs_pathways(use_projected=False) -> typing.List[NcsPathway]:
    """Returns a list of NCS pathways with some containing carbon layers.

    :param use_projected: True to return projected NCS layers else the
    geographic ones.
    :type use_projected: bool

    :returns: List of NCS pathways.
    :rtype: list
    """
    pathway_layer_directory = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "pathways", "layers"
    )

    carbon_directory = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "carbon", "layers"
    )

    carbon_layer_path = os.path.join(carbon_directory, "carbon_layer_1.tif")

    filenames = []

    for i in range(1, 4):
        base_name = "test_pathway"
        if use_projected:
            base_name = f"{base_name}_projected"

        filenames.append(f"{base_name}_{i!s}.tif")

    pathway_layer_path1 = os.path.join(pathway_layer_directory, filenames[0])
    pathway_layer_path2 = os.path.join(pathway_layer_directory, filenames[1])
    pathway_layer_path3 = os.path.join(pathway_layer_directory, filenames[2])

    ncs_pathway1 = NcsPathway(
        UUID(NCS_UUID_STR_1),
        "NCS One",
        "Description for NCS one",
        pathway_layer_path1,
        LayerType.RASTER,
        True,
        carbon_paths=[carbon_layer_path],
    )

    ncs_pathway2 = NcsPathway(
        UUID(NCS_UUID_STR_2),
        "NCS Two",
        "Description for NCS two",
        pathway_layer_path2,
        LayerType.RASTER,
        True,
    )

    ncs_pathway3 = NcsPathway(
        UUID(NCS_UUID_STR_2),
        "NCS Three",
        "Description for NCS three",
        pathway_layer_path3,
        LayerType.RASTER,
        True,
        carbon_paths=[carbon_layer_path],
    )

    return [ncs_pathway1, ncs_pathway2, ncs_pathway3]


def get_protected_ncs_pathways() -> typing.List[NcsPathway]:
    """Returns a list of protected NCS pathways.

    :returns: List of protected NCS pathways.
    :rtype: list
    """
    pathway_layer_directory = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "pathways", "layers"
    )

    filenames = []
    for i in range(1, 3):
        base_name = "protected_test_pathway"
        filenames.append(f"{base_name}_{i!s}.tif")

    protected_pathway_layer_path1 = os.path.join(pathway_layer_directory, filenames[0])
    protected_pathway_layer_path2 = os.path.join(pathway_layer_directory, filenames[1])

    protected_ncs_pathway1 = NcsPathway(
        UUID(PROTECTED_NCS_UUID_STR_1),
        "Protected NCS One",
        "Description for Protected NCS one",
        protected_pathway_layer_path1,
        LayerType.RASTER,
        True,
        pathway_type=NcsPathwayType.PROTECT,
    )

    protected_ncs_pathway2 = NcsPathway(
        UUID(PROTECTED_NCS_UUID_STR_2),
        "Protected NCS Two",
        "Description for Protected NCS two",
        protected_pathway_layer_path2,
        LayerType.RASTER,
        True,
        pathway_type=NcsPathwayType.PROTECT,
    )

    return [protected_ncs_pathway1, protected_ncs_pathway2]


def get_reference_irrecoverable_carbon_path() -> str:
    """Gets the path to the test irrecoverable carbon reference dataset."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "carbon",
        "layers",
        "irrecoverable_carbon.tif",
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
        "Test Scenario",
        "Test scenario description",
        sp_extent,
        [get_activity()],
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
    return ScenarioResult(get_test_scenario(), output_layer_name="Test Scenario Layer")


def get_ncs_pathway_npvs() -> typing.List[NcsPathwayNpv]:
    """Returns a collection of NCS pathway NPV mappings."""
    ncs_pathways = get_ncs_pathways()

    npv_params_1 = NpvParameters(3, 2.0)
    npv_params_1.absolute_npv = NCS_PATHWAY_1_NPV
    npv_params_1.yearly_rates = [
        (25000.0, 18000.0, 7000.0),
        (28000.0, 15000.0, 12745.1),
        (35000.0, 13500.0, 20665.13),
    ]
    pathway_npv_1 = NcsPathwayNpv(npv_params_1, True, ncs_pathways[0])

    npv_params_2 = NpvParameters(2, 4.0)
    npv_params_2.absolute_npv = 102307.69
    npv_params_2.yearly_rates = [
        (100000.0, 65000.0, 35000.0),
        (120000.0, 50000.0, 67307.69),
    ]
    pathway_npv_2 = NcsPathwayNpv(npv_params_2, True, ncs_pathways[1])

    npv_params_3 = NpvParameters(3, 7.0)
    npv_params_3.absolute_npv = 38767.05
    npv_params_3.yearly_rates = [
        (64000.0, 58000.0, 6000.0),
        (67500.0, 53000.0, 13551.4),
        (70000.0, 48000.0, 19215.65),
    ]
    pathway_npv_3 = NcsPathwayNpv(npv_params_3, True, ncs_pathways[2])

    return [pathway_npv_1, pathway_npv_2, pathway_npv_3]


def get_ncs_pathway_npv_collection() -> NcsPathwayNpvCollection:
    """Returns an NCS pathway NPV collection for testing."""
    npv_collection = NcsPathwayNpvCollection(0.0, 0.0)

    mappings = get_ncs_pathway_npvs()
    npv_collection.mappings = mappings

    return npv_collection


def get_metric_column() -> MetricColumn:
    """Returns a metric column object for testing."""
    custom_job_metric_column = MetricColumn.create_default_column(
        METRIC_COLUMN_NAME, "Custom Job", "@cplus_activity_area * 2"
    )
    custom_job_metric_column.auto_calculated = False
    custom_job_metric_column.format_as_number = True

    return custom_job_metric_column


def get_metric_configuration() -> MetricConfiguration:
    """Creates a metric configuration object."""
    area_metric_column = MetricColumn.create_default_column(
        "Area", "Area (Ha)", "@cplus_activity_area"
    )
    area_metric_column.auto_calculated = True
    area_metric_column.format_as_number = True

    return MetricConfiguration(
        [
            area_metric_column,
            get_metric_column(),
        ],
        [
            [
                ActivityColumnMetric(
                    get_activity(),
                    area_metric_column,
                    MetricType.COLUMN,
                    "@cplus_activity_area",
                ),
                ActivityColumnMetric(
                    get_activity(),
                    get_metric_column(),
                    MetricType.COLUMN,
                    "activity_npv()",
                ),
            ]
        ],
    )


def get_pwl_test_data_path() -> str:
    """Get the path to the test PWL dataset."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "priority",
        "layers",
        "test_priority_1.tif",
    )


def get_test_pwl() -> dict[str, str]:
    """Creates a PWL object as a dict."""
    return {
        "uuid": PWL_UUID_STR,
        "name": "Test PW",
        "description": "Placeholder text for test PWL",
        "selected": True,
        "path": get_pwl_test_data_path(),
        "groups": [],
        "type": PriorityLayerType.DEFAULT.value,
    }


NCS_PATHWAY_DICT = {
    UUID_ATTRIBUTE: UUID(VALID_NCS_UUID_STR),
    NAME_ATTRIBUTE: "Valid NCS Pathway",
    DESCRIPTION_ATTRIBUTE: "Description for valid NCS",
    PATH_ATTRIBUTE: TEST_RASTER_PATH,
    LAYER_TYPE_ATTRIBUTE: 0,
    USER_DEFINED_ATTRIBUTE: True,
    CARBON_PATHS_ATTRIBUTE: [],
    PATHWAY_TYPE_ATTRIBUTE: 2,
    PRIORITY_LAYERS_SEGMENT: [],
}


METRIC_CONFIGURATION_DICT = {
    "metric_columns": [
        {
            "name": "Area",
            "header": "Area (Ha)",
            "expression": "@cplus_activity_area",
            "alignment": 4,
            "auto_calculated": True,
            "number_formatter_enabled": True,
            "number_formatter_type_id": "basic",
            "number_formatter_props": {
                "decimal_separator": None,
                "decimals": 5,
                "rounding_type": 0,
                "show_plus": False,
                "show_thousand_separator": True,
                "show_trailing_zeros": True,
                "thousand_separator": None,
            },
        },
        {
            "name": METRIC_COLUMN_NAME,
            "header": "Financials",
            "expression": "activity_npv()",
            "alignment": 4,
            "auto_calculated": False,
            "number_formatter_enabled": True,
            "number_formatter_type_id": "basic",
            "number_formatter_props": {
                "decimal_separator": None,
                "decimals": 6,
                "rounding_type": 0,
                "show_plus": False,
                "show_thousand_separator": True,
                "show_trailing_zeros": True,
                "thousand_separator": None,
            },
        },
    ],
    "activity_metrics": [
        [
            {
                "activity_identifier": ACTIVITY_UUID_STR,
                "metric_identifier": "Area",
                "metric_type": 0,
                "expression": "@cplus_activity_area",
            },
            {
                "activity_identifier": ACTIVITY_UUID_STR,
                "metric_identifier": METRIC_COLUMN_NAME,
                "metric_type": 0,
                "expression": "activity_npv()",
            },
        ]
    ],
    "activity_identifiers": [ACTIVITY_UUID_STR],
}
