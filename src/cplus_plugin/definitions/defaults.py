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
USER_DOCUMENTATION_SITE = "https://kartoza.github.io/cplus-plugin/user/cplus_ui_guide"
ABOUT_DOCUMENTATION_SITE = "https://kartoza.github.io/cplus-plugin/about/ci"
REPORT_DOCUMENTATION = (
    "https://kartoza.github.io/cplus-plugin/user/cplus_ui_guide/#report-generating"
)

OPTIONS_TITLE = "CPLUS"  # Title in the QGIS settings
ICON_PATH = ":/plugins/cplus_plugin/icon.svg"
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

QGIS_GDAL_PROVIDER = "gdal"

DEFAULT_LOGO_PATH = (
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/logos/ci_logo.png"
)


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


# Path just contains the file name and is relative to {download_folder}/ncs_pathways
DEFAULT_NCS_PATHWAYS = [
    {
        "uuid": "b187f92f-b85b-45c4-9179-447f7ea114e3",
        "name": "Agroforestry",
        "description": "Provides additional carbon sequestration in agricultural "
        "systems by strategically planting trees in croplands.",
        "path": "Final_Agroforestry_Priority_norm.tif",
        "layer_type": 0,
    },
    {
        "uuid": "bd381140-64f0-43d0-be6c-50120dd6c174",
        "name": "Animal Management",
        "description": "Provides additional soil carbon sequestration, reduces "
        "methane emissions from ruminants, and improves feed "
        "efficiency.",
        "path": "Final_Animal_Management_Priority_norm.tif",
        "layer_type": 0,
    },
    {
        "uuid": "fc36dd06-aea3-4067-9626-2d73916d79b0",
        "name": "Avoided Deforestation",
        "description": "Avoids carbon emissions by preventing forest "
        "conversion in areas with a high risk of deforestation. "
        "Forest is defined as indigenous forest regions with "
        "tree density exceeding 75% with a canopy over 6m.",
        "path": "Final_Avoided_Indigenous_Forest_priority_norm.tif",
        "layer_type": 0,
    },
    {
        "uuid": "f7084946-6617-4c5d-97e8-de21059ca0d2",
        "name": "Avoided Grassland Conversion",
        "description": "Avoids carbon emissions by preventing the conversion "
        "of grasslands in areas with a high risk of grassland "
        "loss. Grassland is defined as regions with vegetation "
        "density less than 10%.",
        "path": "Final_Avoided_Grassland_priority_norm.tif",
        "layer_type": 0,
    },
    {
        "uuid": "00db44cf-a2e7-428a-86bb-0afedb9719ec",
        "name": "Avoided Savanna Woodland Conversion",
        "description": "Avoids carbon emissions by preventing the conversion "
        "of open woodland in areas with a high risk of open "
        "woodland loss. Savanna woodland is defined as savanna "
        "regions with open woodlands (vegetation density less than "
        "35% and a tree canopy greater than 2.5m) and natural "
        "wooded lands (vegetation density greater than 35% and a "
        "tree canopy between 2.5m and 6m). ",
        "path": "Final_Avoided_OpenWoodland_NaturalWoodedland_priority_norm.tif",
        "layer_type": 0,
    },
    {
        "uuid": "5475dd4a-5efc-4fb4-ae90-68ff4102591e",
        "name": "Fire Management",
        "description": "Provides additional sequestration and avoids carbon "
        "emissions by increasing resilience to catastrophic fire.",
        "path": "Final_Fire_Management_Priority_norm.tif",
        "layer_type": 0,
    },
    {
        "uuid": "bede344c-9317-4c3f-801c-3117cc76be2c",
        "name": "Restoration - Forest",
        "description": "Provides additional carbon sequestration by converting "
        "non-forest into forest in areas where forests are the "
        "native cover type. This pathway excludes afforestation, "
        "where native non-forest areas are converted to forest. "
        "Forest is defined as indigenous forest regions with "
        "tree density exceeding 75% with a canopy over 6m.",
        "path": "Final_Forest_Restoration_priority_norm.tif",
        "layer_type": 0,
    },
    {
        "uuid": "384863e3-08d1-453b-ac5f-94ad6a6aa1fd",
        "name": "Restoration - Savanna",
        "description": "Sequesters carbon through the restoration of native "
        "grassland and open woodland habitat. This pathway excludes "
        "the opportunity to convert non-native savanna regions to "
        "savannas. Savanna in this context contains grasslands "
        "(vegetation density less than 10%), open woodlands "
        "(vegetation density less than 35% and a tree canopy "
        "greater than 2.5m), and natural wooded lands (vegetation "
        "density greater than 75% and a tree canopy between 2.5m "
        "and 6m). ",
        "path": "Final_Sananna_Restoration_priority_norm.tif",
        "layer_type": 0,
    },
    {
        "uuid": "71de0448-46c4-4163-a124-3d88cdcbba42",
        "name": "Woody Encroachment Control",
        "description": "Gradual woody plant encroachment into non-forest biomes "
        "has important negative consequences for ecosystem "
        "functioning, carbon balances, and economies.",
        "path": "Final_woody_encroachment_norm.tif",
        "layer_type": 0,
    },
]

DEFAULT_IMPLEMENTATION_MODELS = [
    {
        "uuid": "a0b8fd2d-1259-4141-9ad6-d4369cf0dfd4",
        "name": "Agroforestry",
        "description": " Agroforestry is an integrated land use "
        "system that combines the cultivation of trees with "
        "agricultural crops and/or livestock. It promotes "
        "sustainable land management, biodiversity conservation, "
        "soil health improvement, and diversified income "
        "sources for farmers.",
    },
    {
        "uuid": "1c8db48b-717b-451b-a644-3af1bee984ea",
        "name": "Alien Plant Removal",
        "description": "This model involves the removal of "
        "invasive alien plant species that "
        "negatively impact native ecosystems. "
        "By eradicating these plants, natural "
        "habitats can be restored, allowing "
        "native flora and fauna to thrive.",
    },
    {
        "uuid": "de9597b2-f082-4299-9620-1da3bad8ab62",
        "name": "Applied Nucleation",
        "description": " Applied nucleation is a technique "
        "that jump-starts the restoration "
        "process by creating focal points "
        "of vegetation growth within degraded "
        'areas. These "nuclei" serve as '
        "centers for biodiversity recovery, "
        "attracting seeds, dispersers, and "
        "other ecological processes, ultimately "
        "leading to the regeneration of the "
        "surrounding landscape.",
    },
    {
        "uuid": "40f04ea6-1f91-4695-830a-7d46f821f5db",
        "name": "Assisted Natural Regeneration",
        "description": " This model focuses on facilitating "
        "the natural regeneration of forests "
        "and degraded lands by removing "
        "barriers (such as alien plants or "
        "hard crusted soils) and providing "
        "support for native plant species to "
        "regrow. It involves activities such "
        "as removing competing vegetation, "
        "protecting young seedlings, and "
        "restoring ecosystem functions.",
    },
    {
        "uuid": "43f96ed8-cd2f-4b91-b6c8-330d3b93bcc1",
        "name": "Avoided Deforestation and Degradation",
        "description": " This model focuses on preventing "
        "the conversion of forested areas "
        "into other land uses and minimizing "
        "degradation of existing forests. It "
        "involves implementing measures to "
        "protect and sustainably manage "
        "forests, preserving their "
        "biodiversity, carbon sequestration "
        "potential, and ecosystem services.",
    },
    {
        "uuid": "c3c5a381-2b9f-4ddc-8a77-708239314fb6",
        "name": "Avoided Wetland Conversion/Restoration",
        "description": " This model aims to prevent the "
        "conversion of wetland ecosystems "
        "into other land uses and, where possible, "
        "restore degraded wetlands. It involves "
        "implementing conservation measures, "
        "such as land-use planning, regulatory "
        "frameworks, and restoration efforts, "
        "to safeguard the ecological functions "
        "and biodiversity of wetland habitats",
    },
    {
        "uuid": "3defbd0e-2b12-4ab2-a7d4-a035152396a7",
        "name": "Bioproducts",
        "description": " The bioproducts model focuses on "
        "utilizing natural resources sustainably "
        "to create value-added products. It "
        "involves the development and production "
        "of renewable and biodegradable materials, "
        "such as biofuels, bio-based chemicals, "
        "and bio-based materials, to reduce "
        "reliance on fossil fuels and promote "
        "a more sustainable economy.",
    },
    {
        "uuid": "22f9e555-0356-4b18-b292-c2d516dcdba5",
        "name": "Bush Thinning",
        "description": "Bush thinning refers to the controlled "
        "removal of excess woody vegetation in "
        "certain ecosystems and using that biomass "
        "to brush pack bare soil areas to promote "
        "regrowth of grass. This practice helps "
        "restore natural balance, prevent "
        "overgrowth, and enhance biodiversity.",
    },
    {
        "uuid": "177f1f27-cace-4f3e-9c3c-ef2cf54fc283",
        "name": "Direct Tree Seeding",
        "description": " This model involves planting tree "
        "seeds directly into the ground, allowing "
        "them to grow and establish without the "
        "need for nursery cultivation. It is a "
        "cost-effective and environmentally "
        "friendly approach to reforestation and "
        "afforestation efforts, promoting forest "
        "restoration and carbon sequestration.",
    },
    {
        "uuid": "d9d00a77-3db1-4390-944e-09b27bcbb981",
        "name": "Livestock Rangeland Management",
        "description": "This model focuses on sustainable "
        "management practices for livestock "
        "grazing on rangelands. It includes "
        "rotational grazing, monitoring of "
        "vegetation health, and implementing "
        "grazing strategies that promote "
        "biodiversity, soil health, and "
        "sustainable land use.",
    },
    {
        "uuid": "4fbfcb1c-bfd7-4305-b216-7a1077a2ccf7",
        "name": "Livestock Market Access",
        "description": " This model aims to improve market "
        "access for livestock producers practicing "
        "sustainable and regenerative farming "
        "methods. It involves creating networks, "
        "certifications, and partnerships that "
        "support the sale of sustainably produced "
        "livestock products, promoting economic "
        "viability and incentivizing environmentally "
        "friendly practices.",
    },
    {
        "uuid": "20491092-e665-4ee7-b92f-b0ed864c7312",
        "name": "Natural Woodland Livestock Management",
        "description": " This model emphasizes the sustainable "
        "management of livestock within natural "
        "woodland environments. It involves "
        "implementing practices that balance "
        "livestock grazing with the protection "
        "and regeneration of native woodlands, "
        "ensuring ecological integrity while "
        "meeting livestock production goals.",
    },
    {
        "uuid": "92054916-e8ea-45a0-992c-b6273d1b75a7",
        "name": "Sustainable Crop Farming & Aquaponics ",
        "description": " This model combines sustainable "
        "crop farming practices such as "
        "agroecology, Permaculture and "
        "aquaponics, a system that integrates "
        "aquaculture (fish farming) with hydroponics "
        "(soil-less crop cultivation). It enables "
        "the production of crops with sustainable "
        "practices in a mutually beneficial and "
        "resource-efficient manner, reducing "
        "water usage and chemical inputs while "
        "maximizing productivity.",
    },
]
