# -*- coding: utf-8 -*-
"""
    Definitions for all defaults settings
"""

PILOT_AREA_EXTENT = {
    "type": "Polygon",
    "coordinates": [-23.960197335, 32.069186664, -25.201606226, 30.743498637],
}

DOCUMENTATION_SITE = "https://kartoza.github.io/cplus-plugin"

OPTIONS_TITLE = "CPLUS"  # Title in the QGIS settings
ICON_PATH = ":/plugins/cplus_plugin/icon.svg"

# Path just contains the file name and is relative to {download_folder}/ncs_pathways
# TODO: Insert file names for each NCS pathway configuration
DEFAULT_NCS_PATHWAYS = [
    {
        "uuid": "bd381140-64f0-43d0-be6c-50120dd6c174",
        "name": "Animal Management",
        "description": "Placeholder text for animal management",
        "path": "",
        "layer_type": 0,
    },
    {
        "uuid": "fc36dd06-aea3-4067-9626-2d73916d79b0",
        "name": "Avoided Deforestation",
        "description": "Placeholder text for avoided deforestation",
        "path": "",
        "layer_type": 0,
    },
    {
        "uuid": "f7084946-6617-4c5d-97e8-de21059ca0d2",
        "name": "Avoided Grassland Conversion",
        "description": "Placeholder text for avoided grassland conversion",
        "path": "",
        "layer_type": 0,
    },
    {
        "uuid": "00db44cf-a2e7-428a-86bb-0afedb9719ec",
        "name": "Avoided Open Woodland Conversion",
        "description": "Placeholder text for avoided open woodland conversion",
        "path": "",
        "layer_type": 0,
    },
    {
        "uuid": "bede344c-9317-4c3f-801c-3117cc76be2c",
        "name": "Forest Restoration",
        "description": "Placeholder text for forest restoration",
        "path": "",
        "layer_type": 0,
    },
    {
        "uuid": "5475dd4a-5efc-4fb4-ae90-68ff4102591e",
        "name": "Grassland Fire Management",
        "description": "Placeholder text for grassland fire management",
        "path": "",
        "layer_type": 0,
    },
    {
        "uuid": "384863e3-08d1-453b-ac5f-94ad6a6aa1fd",
        "name": "Grassland Restoration",
        "description": "Placeholder text for grassland restoration",
        "path": "",
        "layer_type": 0,
    },
    {
        "uuid": "71de0448-46c4-4163-a124-3d88cdcbba42",
        "name": "Woody Encroachment Control",
        "description": "Placeholder text for woody encroachment control",
        "path": "",
        "layer_type": 0,
    },
]

DEFAULT_IMPLEMENTATION_MODELS = [
    {
        "uuid": "a0b8fd2d-1259-4141-9ad6-d4369cf0dfd4",
        "name": "Herding for Health",
        "description": "Placeholder text for herding for health",
    },
    {
        "uuid": "1c8db48b-717b-451b-a644-3af1bee984ea",
        "name": "Eat Fresh",
        "description": "Placeholder text for eat fresh",
    },
    {
        "uuid": "de9597b2-f082-4299-9620-1da3bad8ab62",
        "name": "Charcoal Naturally",
        "description": "Placeholder text for charcoal naturally",
    },
]
