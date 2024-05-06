# -*- coding: utf-8 -*-
"""
    Definitions for all defaults settings
"""

import os
import json

from pathlib import Path

PILOT_AREA_EXTENT = {
    "type": "Polygon",
    "coordinates": [30.743498637, 32.069186664, -25.201606226, -23.960197335],
}

PLUGIN_MESSAGE_LOG_TAB = "qgis_cplus"
SCENARIO_LOG_FILE_NAME = "processing.log"

QGIS_MESSAGE_LEVEL_DICT = {
    0: "INFO",
    1: "WARNING",
    2: "CRITICAL",
    3: "SUCCESS",
    4: "NOLEVEL",
}

DEFAULT_CRS_ID = 4326

DOCUMENTATION_SITE = "https://conservationinternational.github.io/cplus-plugin"
USER_DOCUMENTATION_SITE = (
    "https://conservationinternational.github.io/cplus-plugin/user/guide"
)
ABOUT_DOCUMENTATION_SITE = (
    "https://conservationinternational.github.io/cplus-plugin/about/ci"
)
REPORT_DOCUMENTATION = "https://conservationinternational.github.io/cplus-plugin/user/guide/#report-generating"

OPTIONS_TITLE = "CPLUS"  # Title in the QGIS settings
GENERAL_OPTIONS_TITLE = "General"
REPORT_OPTIONS_TITLE = "Reporting"
LOG_OPTIONS_TITLE = "Logs"
ICON_PATH = ":/plugins/cplus_plugin/icon.svg"
REPORT_SETTINGS_ICON_PATH = str(
    os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        + "/icons/report_settings.svg"
    )
)
LOG_SETTINGS_ICON_PATH = str(
    os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        + "/icons/log_settings.svg"
    )
)
ICON_PDF = (
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    + "/icons/mActionSaveAsPDF.svg"
)
ICON_LAYOUT = (
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    + "/icons/mActionNewLayout.svg"
)
ICON_REPORT = (
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    + "/icons/mIconReport.svg"
)
ICON_HELP = (
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    + "/icons/mActionHelpContents_green.svg"
)

ADD_LAYER_ICON_PATH = ":/plugins/cplus_plugin/cplus_left_arrow.svg"
REMOVE_LAYER_ICON_PATH = ":/plugins/cplus_plugin/cplus_right_arrow.svg"

SCENARIO_OUTPUT_FILE_NAME = "cplus_scenario_output"
SCENARIO_OUTPUT_LAYER_NAME = "scenario_result"

PILOT_AREA_SCENARIO_SYMBOLOGY = {
    "Agroforestry": {"val": 1, "color": "#d80007"},
    "Alien Plant Removal": {"val": 2, "color": "#6f6f6f"},
    "Applied Nucleation": {"val": 3, "color": "#81c4ff"},
    "Assisted Natural Regeneration": {"val": 4, "color": "#e8ec18"},
    "Avoided Deforestation and Degradation": {"val": 5, "color": "#ff4c84"},
    "Avoided Wetland Conversion/Restoration": {"val": 6, "color": "#1f31d3"},
    "Bioproducts": {"val": 7, "color": "#67593f"},
    "Bush Thinning": {"val": 8, "color": "#30ff01"},
    "Direct Tree Seeding": {"val": 9, "color": "#bd6b70"},
    "Livestock Market Access": {"val": 10, "color": "#6c0009"},
    "Livestock Rangeland Management": {"val": 11, "color": "#ffa500"},
    "Natural Woodland Livestock Management": {"val": 12, "color": "#007018"},
    "Sustainable Crop Farming & Aquaponics": {"val": 13, "color": "#781a8b"},
}

ACTIVITY_COLOUR_RAMPS = {
    "Agroforestry": "Reds",
    "Alien Plant Removal": "Greys",
    "Alien_Plant_Removal": "Greys",
    "Applied Nucleation": "PuBu",
    "Applied_Nucleation": "PuBu",
    "Assisted Natural Regeneration": "YlOrRd",
    "Assisted_Natural_Regeneration": "YlOrRd",
    "Avoided Deforestation and Degradation": "RdPu",
    "Avoided_Deforestation_and_Degradation": "RdPu",
    "Avoided Wetland Conversion/Restoration": "Blues",
    "Avoided_Wetland_Conversion_Restoration": "Blues",
    "Bioproducts": "BrBG",
    "Bush Thinning": "BuGn",
    "Bush_Thinning": "BuGn",
    "Direct Tree Seeding": "PuRd",
    "Direct_Tree_Seeding": "PuRd",
    "Livestock Market Access": "Rocket",
    "Livestock_Market_Access": "Rocket",
    "Livestock Rangeland Management": "YlOrBr",
    "Livestock_Rangeland_Management": "YlOrBr",
    "Natural Woodland Livestock Management": "Greens",
    "Natural_Woodland_Livestock_Management": "Greens",
    "Sustainable Crop Farming & Aquaponics": "Purples",
    "Sustainable_Crop_Farming_&_Aquaponics": "Purples",
}

QGIS_GDAL_PROVIDER = "gdal"

DEFAULT_LOGO_PATH = (
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/icons/ci_logo.png"
)
CPLUS_LOGO_PATH = str(
    os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        + "/icons/cplus_logo.svg"
    )
)
CI_LOGO_PATH = str(
    os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        + "/icons/ci_logo.svg"
    )
)

# Default template file name
TEMPLATE_NAME = "main.qpt"

# Minimum sizes (in mm) for repeat items in the template
MINIMUM_ITEM_WIDTH = 100
MINIMUM_ITEM_HEIGHT = 100

# Report font
REPORT_FONT_NAME = "Ubuntu"

# Activity character limits
MAX_ACTIVITY_NAME_LENGTH = 50
MAX_ACTIVITY_DESCRIPTION_LENGTH = 225

# IDs for the given tables in the report template
ACTIVITY_AREA_TABLE_ID = "activity_area_table"
PRIORITY_GROUP_WEIGHT_TABLE_ID = "assigned_weights_table"

# Initiliazing the plugin default data as found in the data directory
priority_layer_path = (
    Path(__file__).parent.parent.resolve()
    / "data"
    / "default"
    / "priority_weighting_layers.json"
)

with priority_layer_path.open("r") as fh:
    priority_layers_dict = json.load(fh)
PRIORITY_LAYERS = priority_layers_dict["layers"]


pathways_path = (
    Path(__file__).parent.parent.resolve() / "data" / "default" / "ncs_pathways.json"
)

with pathways_path.open("r") as fh:
    pathways_dict = json.load(fh)
# Path just contains the file name and is relative to {download_folder}/ncs_pathways
DEFAULT_NCS_PATHWAYS = pathways_dict["pathways"]


activities_path = (
    Path(__file__).parent.parent.resolve() / "data" / "default" / "activities.json"
)

with activities_path.open("r") as fh:
    models_dict = json.load(fh)

DEFAULT_ACTIVITIES = models_dict["activities"]


PRIORITY_GROUPS = [
    {
        "uuid": "dcfb3214-4877-441c-b3ef-8228ab6dfad3",
        "name": "Biodiversity",
        "description": "Placeholder text for bio diversity",
    },
    {
        "uuid": "8b9fb419-b6b8-40e8-9438-c82901d18cd9",
        "name": "Livelihood",
        "description": "Placeholder text for livelihood",
    },
    {
        "uuid": "21a30a80-eb49-4c5e-aff6-558123688e09",
        "name": "Climate Resilience",
        "description": "Placeholder text for climate resilience ",
    },
    {
        "uuid": "ae1791c3-93fd-4e8a-8bdf-8f5fced11ade",
        "name": "Ecological infrastructure",
        "description": "Placeholder text for ecological infrastructure",
    },
    {
        "uuid": "8cac9e25-98a8-4eae-a257-14a4ef8995d0",
        "name": "Policy",
        "description": "Placeholder text for policy",
    },
    {
        "uuid": "3a66c845-2f9b-482c-b9a9-bcfca8395ad5",
        "name": "Finance - Years Experience",
        "description": "Placeholder text for years of experience",
    },
    {
        "uuid": "c6dbfe09-b05c-4cfc-8fc0-fb63cfe0ceee",
        "name": "Finance - Market Trends",
        "description": "Placeholder text for market trends",
    },
    {
        "uuid": "3038cce0-3470-4b09-bb2a-f82071fe57fd",
        "name": "Finance - Net Present value",
        "description": "Placeholder text for net present value",
    },
    {
        "uuid": "3b2c7421-f879-48ef-a973-2aa3b1390694",
        "name": "Finance - Carbon",
        "description": "Placeholder text for finance carbon",
    },
]

DEFAULT_REPORT_DISCLAIMER = (
    "The boundaries, names, and designations "
    "used in this report do not imply official "
    "endorsement or acceptance by Conservation "
    "International Foundation, or its partner "
    "organizations and contributors."
)
DEFAULT_REPORT_LICENSE = (
    "Creative Commons Attribution 4.0 International " "License (CC BY 4.0)"
)
