# -*- coding: utf-8 -*-
"""
    Definitions for all defaults settings
"""

import os

PILOT_AREA_EXTENT = {
    "type": "Polygon",
    "coordinates": [-23.960197335, 32.069186664, -25.201606226, 30.743498637],
}

DOCUMENTATION_SITE = "https://kartoza.github.io/cplus-plugin"

PRIORITY_LAYERS = [
    {
        "uuid": "c931282f-db2d-4644-9786-6720b3ab206a",
        "name": "Carbon importance herding for health",
        "description": "Placeholder text for herding for health",
        "selected": True,
    },
    {
        "uuid": "f5687ced-af18-4cfc-9bc3-8006e40420b6",
        "name": "Carbon importance eat fresh",
        "description": "Placeholder text for eat fresh",
        "selected": False,
    },
    {
        "uuid": "fef3c7e4-0cdf-477f-823b-a99da42f931e",
        "name": "Biodiversity herding for health",
        "description": "Placeholder text for herding for health",
        "selected": False,
    },
    {
        "uuid": "fce41934-5196-45d5-80bd-96423ff0e74e",
        "name": "Biodiversity eat fresh",
        "description": "Placeholder text for eat fresh",
        "selected": False,
    },
]


PRIORITY_GROUPS = [
    {
        "uuid": "a4f76e6c-9f83-4a9c-b700-fb1ae04860a4",
        "name": "Carbon importance",
        "description": "Placeholder text for carbon importance",
    },
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

OPTIONS_TITLE = "CPLUS"  # Title in the QGIS settings
ICON_PATH = ":/plugins/cplus_plugin/icon.svg"
DEFAULT_LOGO_PATH = (
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/logos/ci_logo.png"
)

# Path just contains the file name and is relative to {download_folder}/ncs_pathways
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
        "uuid": "3714288d-1b58-4231-b0f6-18adf7f5b037",
        "name": "Wattle naturally",
        "description": "Placeholder text for eat fresh",
    },
    {
        "uuid": "6143ca4c-f7ad-48aa-9bc3-cfeef7acf425",
        "name": "Assisted natural regeneration",
        "description": "Placeholder text for eat fresh",
    },
    {
        "uuid": "b313c098-3b5b-4b09-b04a-53b7bad9b8e0",
        "name": "Alien plant removal",
        "description": "Placeholder text for eat fresh",
    },
    {
        "uuid": "a372af1d-2f10-4e9a-9052-638bf1ca11ec",
        "name": "Bush thinning",
        "description": "Placeholder text for eat fresh",
    },
]

PRIORITY_LAYERS = [
    {
        "uuid": "c931282f-db2d-4644-9786-6720b3ab206a",
        "name": "Carbon importance herding for health",
        "description": "Placeholder text for herding for health",
        "selected": True,
    },
    {
        "uuid": "f5687ced-af18-4cfc-9bc3-8006e40420b6",
        "name": "Carbon importance eat fresh",
        "description": "Placeholder text for eat fresh",
        "selected": False,
    },
    {
        "uuid": "fef3c7e4-0cdf-477f-823b-a99da42f931e",
        "name": "Biodiversity herding for health",
        "description": "Placeholder text for herding for health",
        "selected": False,
    },
    {
        "uuid": "fce41934-5196-45d5-80bd-96423ff0e74e",
        "name": "Biodiversity eat fresh",
        "description": "Placeholder text for eat fresh",
        "selected": False,
    },
]


PRIORITY_GROUPS = [
    {
        "uuid": "a4f76e6c-9f83-4a9c-b700-fb1ae04860a4",
        "name": "Carbon importance",
        "description": "Placeholder text for carbon importance",
    },
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
        "description": "Placeholder text for years of exprience",
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
