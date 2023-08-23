# -*- coding: utf-8 -*-
"""
    Definitions for all defaults settings
"""

import os

PILOT_AREA_EXTENT = {
    "type": "Polygon",
    "coordinates": [30.743498637, 32.069186664, -25.201606226, -23.960197335],
}

DEFAULT_CRS_ID = 4326

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

STYLES_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/styles/"
LAYER_STYLES = {
    "scenario_result": STYLES_PATH + "0_default_scenario_style.qml",
    "normal": {
        "Agroforestry": STYLES_PATH + "normal/" + "1_agroforesty_style.qml",
        "Alien Plant Removal": STYLES_PATH
        + "normal/"
        + "2_alien_plant_removal_style.qml",
        "Applied Nucleation": STYLES_PATH
        + "normal/"
        + "3_applied_nucleation_style.qml",
        "Assisted Natural Regeneration": STYLES_PATH
        + "normal/"
        + "4_assisted_natural_regen_style.qml",
        "Avoided Deforestation and Degradation": STYLES_PATH
        + "normal/"
        + "5_avoided_deforestation_style.qml",
        "Avoided Wetland Conversion/Restoration": STYLES_PATH
        + "normal/"
        + "6_wetland_impacts_style.qml",
        "Bioproducts": STYLES_PATH + "normal/" + "7_bioproducts_style.qml",
        "Bush Thinning": STYLES_PATH + "normal/" + "8_bush_thinning_style.qml",
        "Direct Tree Seeding": STYLES_PATH + "normal/" + "9_tree_seedling_style.qml",
        "Livestock Market Access": STYLES_PATH
        + "normal/"
        + "10_livestock_market_style.qml",
        "Livestock Rangeland Management": STYLES_PATH
        + "normal/"
        + "11_livestock_rangeland_style.qml",
        "Natural Woodland Livestock Management": STYLES_PATH
        + "normal/"
        + "12_woodland_livestock_style.qml",
        "Sustainable Crop Farming & Aquaponics": STYLES_PATH
        + "normal/"
        + "13_crop_farming_style.qml",
    },
    "carbon": {
        "Agroforestry": STYLES_PATH + "carbon/" + "1_agroforesty_style.qml",
        "Alien Plant Removal": STYLES_PATH
        + "carbon/"
        + "2_alien_plant_removal_style.qml",
        "Applied Nucleation": STYLES_PATH
        + "carbon/"
        + "3_applied_nucleation_style.qml",
        "Assisted Natural Regeneration": STYLES_PATH
        + "carbon/"
        + "4_assisted_natural_regen_style.qml",
        "Avoided Deforestation and Degradation": STYLES_PATH
        + "carbon/"
        + "5_avoided_deforestation_style.qml",
        "Avoided Wetland Conversion/Restoration": STYLES_PATH
        + "carbon/"
        + "6_wetland_impacts_style.qml",
        "Bioproducts": STYLES_PATH + "carbon/" + "7_bioproducts_style.qml",
        "Bush Thinning": STYLES_PATH + "carbon/" + "8_bush_thinning_style.qml",
        "Direct Tree Seeding": STYLES_PATH + "carbon/" + "9_tree_seedling_style.qml",
        "Livestock Market Access": STYLES_PATH
        + "carbon/"
        + "10_livestock_market_style.qml",
        "Livestock Rangeland Management": STYLES_PATH
        + "11_livestock_rangeland_style.qml",
        "Natural Woodland Livestock Management": STYLES_PATH
        + "carbon/"
        + "12_woodland_livestock_style.qml",
        "Sustainable Crop Farming & Aquaponics": STYLES_PATH
        + "carbon/"
        + "13_crop_farming_style.qml",
    },
}

LAYER_STYLES_WEIGHTED = {
    "normal": {
        "Agroforestry": STYLES_PATH + "normal/" + "1_agroforesty_style.qml",
        "Alien_Plant_Removal": STYLES_PATH
        + "normal/"
        + "2_alien_plant_removal_style.qml",
        "Applied_Nucleation": STYLES_PATH
        + "normal/"
        + "3_applied_nucleation_style.qml",
        "Assisted_Natural_Regeneration": STYLES_PATH
        + "normal/"
        + "4_assisted_natural_regen_style.qml",
        "Avoided_Deforestation_and_Degradation": STYLES_PATH
        + "normal/"
        + "5_avoided_deforestation_style.qml",
        "Avoided_Wetland_Conversion_Restoration": STYLES_PATH
        + "normal/"
        + "6_wetland_impacts_style.qml",
        "Bioproducts": STYLES_PATH + "normal/" + "7_bioproducts_style.qml",
        "Bush_Thinning": STYLES_PATH + "normal/" + "8_bush_thinning_style.qml",
        "Direct_Tree_Seeding": STYLES_PATH + "normal/" + "9_tree_seedling_style.qml",
        "Livestock_Market_Access": STYLES_PATH
        + "normal/"
        + "10_livestock_market_style.qml",
        "Livestock_Rangeland_Management": STYLES_PATH
        + "normal/"
        + "11_livestock_rangeland_style.qml",
        "Natural_Woodland_Livestock_Management": STYLES_PATH
        + "normal/"
        + "12_woodland_livestock_style.qml",
        "Sustainable_Crop_Farming_&_Aquaponics": STYLES_PATH
        + "normal/"
        + "13_crop_farming_style.qml",
    },
    "carbon": {
        "Agroforestry": STYLES_PATH + "carbon/" + "1_agroforesty_style.qml",
        "Alien_Plant_Removal": STYLES_PATH
        + "carbon/"
        + "2_alien_plant_removal_style.qml",
        "Applied_Nucleation": STYLES_PATH
        + "carbon/"
        + "3_applied_nucleation_style.qml",
        "Assisted_Natural_Regeneration": STYLES_PATH
        + "carbon/"
        + "4_assisted_natural_regen_style.qml",
        "Avoided_Deforestation_and_Degradation": STYLES_PATH
        + "carbon/"
        + "5_avoided_deforestation_style.qml",
        "Avoided_Wetland_Conversion_Restoration": STYLES_PATH
        + "carbon/"
        + "6_wetland_impacts_style.qml",
        "Bioproducts": STYLES_PATH + "carbon/" + "7_bioproducts_style.qml",
        "Bush_Thinning": STYLES_PATH + "carbon/" + "8_bush_thinning_style.qml",
        "Direct_Tree_Seeding": STYLES_PATH + "carbon/" + "9_tree_seedling_style.qml",
        "Livestock_Market_Access": STYLES_PATH
        + "carbon/"
        + "10_livestock_market_style.qml",
        "Livestock_Rangeland_Management": STYLES_PATH
        + "11_livestock_rangeland_style.qml",
        "Natural_Woodland_Livestock_Management": STYLES_PATH
        + "carbon/"
        + "12_woodland_livestock_style.qml",
        "Sustainable_Crop_Farming_&_Aquaponics": STYLES_PATH
        + "carbon/"
        + "13_crop_farming_style.qml",
    },
}

QGIS_GDAL_PROVIDER = "gdal"

DEFAULT_LOGO_PATH = (
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/logos/ci_logo.png"
)
CPLUS_LOGO_PATH = str(
    os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        + "/logos/cplus_logo.svg"
    )
)
CI_LOGO_PATH = str(
    os.path.normpath(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        + "/logos/ci_logo.svg"
    )
)

# Default template file name
TEMPLATE_NAME = "main.qpt"

# Minimum sizes (in mm) for repeat items in the template
MINIMUM_ITEM_WIDTH = 100
MINIMUM_ITEM_HEIGHT = 100

# Report font
REPORT_FONT_NAME = "Ubuntu"

# IDs for the given tables in the report template
IMPLEMENTATION_MODEL_AREA_TABLE_ID = "implementation_model_area_table"
PRIORITY_GROUP_WEIGHT_TABLE_ID = "assigned_weights_table"


PRIORITY_LAYERS = [
    {
        "uuid": "c931282f-db2d-4644-9786-6720b3ab206a",
        "name": "social_int_clip_norm",
        "description": "Placeholder text for social_int_clip_norm",
        "selected": True,
        "path": "social_int_clip_norm.tif",
    },
    {
        "uuid": "f5687ced-af18-4cfc-9bc3-8006e40420b6",
        "name": "social_int_clip_norm_inverse",
        "description": "Placeholder text for social_int_clip_norm_inverse",
        "selected": False,
        "path": "social_int_clip_norm_inverse.tif",
    },
    {
        "uuid": "fef3c7e4-0cdf-477f-823b-a99da42f931e",
        "name": "cccombo_clip_norm_inverse",
        "description": "Placeholder text for cccombo_clip_norm_inverse",
        "selected": False,
        "path": "cccombo_clip_norm_inverse.tif",
    },
    {
        "uuid": "fce41934-5196-45d5-80bd-96423ff0e74e",
        "name": "cccombo_clip_norm",
        "description": "Placeholder text for cccombo_clip_norm",
        "selected": False,
        "path": "cccombo_clip_norm.tif",
    },
    {
        "uuid": "88c1c7dd-c5d1-420c-a71c-a5c595c1c5be",
        "name": "ei_all_gknp_clip_norm",
        "description": "Placeholder text for ei_all_gknp_clip_norm",
        "selected": False,
        "path": "ei_all_gknp_clip_norm.tif",
    },
    {
        "uuid": "9ab8c67a-5642-4a09-a777-bd94acfae9d1",
        "name": "biocombine_clip_norm",
        "description": "Placeholder text for biocombine_clip_norm",
        "selected": False,
        "path": "biocombine_clip_norm.tif",
    },
    {
        "uuid": "2f76304a-bb73-442c-9c02-ff9945389a20",
        "name": "Policy",
        "description": "Placeholder text for Policy",
        "selected": False,
        "path": "Policy.tif",
    },
    {
        "uuid": "fee0b421-805b-4bd9-a629-06586a760405",
        "name": "Herding_4_Health_years",
        "description": "Placeholder text for Herding_4_Health_years",
        "selected": False,
        "path": "Herding_4_Health_years.tif",
    },
    {
        "uuid": "3c155210-ccd8-404b-bbe8-b1433d6158a2",
        "name": "Alien_Plant_Removal_years_re",
        "description": "Placeholder text for Alien_Plant_Removal_years_re",
        "selected": False,
        "path": "Alien_Plant_Removal_years_re.tif",
    },
    {
        "uuid": "fb92cac1-7744-4b11-8238-4e1da97650e0",
        "name": "Wattle_Naturally_years_re",
        "description": "Placeholder text for Wattle_Naturally_years_re",
        "selected": False,
        "path": "Wattle_Naturally_years_re.tif",
    },
    {
        "uuid": "e1a801c5-7f77-4746-be34-0138b62ff25c",
        "name": "Bush_Thinning_years_re",
        "description": "Placeholder text for Bush_Thinning_years_re",
        "selected": False,
        "path": "Bush_Thinning_years_re.tif",
    },
    {
        "uuid": "6f7c1494-f73e-4e5e-8411-59676f9fa6e1",
        "name": "Eat_Fresh_years",
        "description": "Placeholder text for Eat_Fresh_years",
        "selected": False,
        "path": "Eat_Fresh_years.tif",
    },
    {
        "uuid": "85cd441e-fa3d-46e4-add9-973ba58f8bd4",
        "name": "Assisted_Nat_Regen_years",
        "description": "Placeholder text for Assisted_Nat_Regen_years",
        "selected": False,
        "path": "Assisted_Nat_Regen_years.tif",
    },
    {
        "uuid": "38a33633-9198-4b55-a424-135a4d522973",
        "name": "Herding_4_Health_carbonimpact_re",
        "description": "Placeholder text for Herding_4_Health_carbonimpact_re",
        "selected": False,
        "path": "Herding_4_Health_carbonimpact_re.tif",
    },
    {
        "uuid": "9f6c8b8f-0648-44ca-b943-58fab043f559",
        "name": "Alien_Plant_Removal_carbonimpact_re",
        "description": "Placeholder text for Alien_Plant_Removal_carbonimpact_re",
        "selected": False,
        "path": "Alien_Plant_Removal_carbonimpact_re.tif",
    },
    {
        "uuid": "478b0729-a507-4729-b1e4-b2bea7e161fd",
        "name": "Bush_Thinning_carbonimpact",
        "description": "Placeholder text for Bush_Thinning_carbonimpact",
        "selected": False,
        "path": "Bush_Thinning_carbonimpact.tif",
    },
    {
        "uuid": "9e5cff3f-73e7-4734-b76a-2a9f0536fa27",
        "name": "Wattle_Naturally_carbonimpact_re",
        "description": "Placeholder text for Wattle_Naturally_carbonimpact_re",
        "selected": False,
        "path": "Wattle_Naturally_carbonimpact_re.tif",
    },
    {
        "uuid": "151668e7-8ffb-4766-9534-09949ab0356b",
        "name": "Eat_Fresh_carbonimpact_re",
        "description": "Placeholder text for Eat_Fresh_carbonimpact_re",
        "selected": False,
        "path": "Eat_Fresh_carbonimpact_re.tif",
    },
    {
        "uuid": "5e41f4fa-3d7f-41aa-bee7-b9e9d08b56db",
        "name": "Assisted_Nat_Regen_carbonimpact",
        "description": "Placeholder text for Assisted_Nat_Regen_carbonimpact",
        "selected": False,
        "path": "Assisted_Nat_Regen_carbonimpact.tif",
    },
    {
        "uuid": "88dc8ff3-e61f-4a48-8f9b-5791efb6603f",
        "name": "Herding_4_Health_NPV_re",
        "description": "Placeholder text for Herding_4_Health_NPV_re",
        "selected": False,
        "path": "Herding_4_Health_NPV_re.tif",
    },
    {
        "uuid": "5f329f53-31ff-4039-b0ec-a8d174a50866",
        "name": "Bush_Thinning_NPV_re",
        "description": "Placeholder text for Bush_Thinning_NPV_re",
        "selected": False,
        "path": "Bush_Thinning_NPV_re.tif",
    },
    {
        "uuid": "c5b1b81e-e1ae-41ec-adeb-7388f7597156",
        "name": "Wattle_Naturally_NPV",
        "description": "Placeholder text for Wattle_Naturally_NPV",
        "selected": False,
        "path": "Wattle_Naturally_NPV.tif",
    },
    {
        "uuid": "ed1ee71b-e7db-4599-97a9-a97c941a615f",
        "name": "Eat_Fresh_NPV",
        "description": "Placeholder text for Eat_Fresh_NPV",
        "selected": False,
        "path": "Eat_Fresh_NPV.tif",
    },
    {
        "uuid": "307df1f4-206b-4f70-8db4-6505948e2a4e",
        "name": "Eat_Fresh_mtrends",
        "description": "Placeholder text for Eat_Fresh_mtrends",
        "selected": False,
        "path": "Eat_Fresh_mtrends.tif",
    },
    {
        "uuid": "86c3dfc5-58d7-4ebd-a851-3b65a6bf5edd",
        "name": "Assisted_Nat_Regen_NPV_re",
        "description": "Placeholder text for Assisted_Nat_Regen_NPV_re",
        "selected": False,
        "path": "Assisted_Nat_Regen_NPV_re.tif",
    },
    {
        "uuid": "a1bfff8e-fb87-4bca-97fa-a984d9bde712",
        "name": "Herding_4_Health_mtrends_re",
        "description": "Placeholder text for Herding_4_Health_mtrends_re",
        "selected": False,
        "path": "Herding_4_Health_mtrends_re.tif",
    },
    {
        "uuid": "ff66420e-d5ff-4869-97d9-021cc90d7a1a",
        "name": "Assisted_Nat_Regen_carbonimpact",
        "description": "Placeholder text for Assisted_Nat_Regen_carbonimpact",
        "selected": False,
        "path": "Assisted_Nat_Regen_carbonimpact.tif",
    },
    {
        "uuid": "9291a5d9-d1cd-44c2-8fc3-2b3b20f80572",
        "name": "Alien_Plant_Removal_mtrends_re",
        "description": "Placeholder text for Alien_Plant_Removal_mtrends_re",
        "selected": False,
        "path": "Alien_Plant_Removal_mtrends_re.tif",
    },
    {
        "uuid": "5bcebbe2-7035-4d81-9817-0b4db8aa63e2",
        "name": "Bush_Thinning_mtrends_re",
        "description": "Placeholder text for Bush_Thinning_mtrends_re",
        "selected": False,
        "path": "Bush_Thinning_mtrends_re.tif",
    },
    {
        "uuid": "3872be6d-f791-41f7-b031-b85173e41d5e",
        "name": "Wattle_Naturally_mtrends_re",
        "description": "Placeholder text for Wattle_Naturally_mtrends_re",
        "selected": False,
        "path": "Wattle_Naturally_mtrends_re.tif",
    },
    {
        "uuid": "620d5d7d-c452-498f-b848-b206a76891cd",
        "name": "Assisted_Nat_Regen_mtrends_re",
        "description": "Placeholder text for Assisted_Nat_Regen_mtrends_re",
        "selected": False,
        "path": "Assisted_Nat_Regen_mtrends_re.tif",
    },
]


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


# Path just contains the file name and is relative to {download_folder}/ncs_pathways
DEFAULT_NCS_PATHWAYS = [
    {
        "uuid": "b187f92f-b85b-45c4-9179-447f7ea114e3",
        "name": "Agroforestry",
        "description": "Provides additional carbon sequestration in agricultural "
        "systems by strategically planting trees in croplands.",
        "path": "Final_Agroforestry_Priority_norm.tif",
        "layer_type": 0,
        "carbon_paths": ["bou_SOC_carbonsum_norm_inverse_null_con_clip.tif"],
    },
    {
        "uuid": "bd381140-64f0-43d0-be6c-50120dd6c174",
        "name": "Animal Management",
        "description": "Provides additional soil carbon sequestration, reduces "
        "methane emissions from ruminants, and improves feed "
        "efficiency.",
        "path": "Final_Animal_Management_Priority_norm.tif",
        "layer_type": 0,
        "carbon_paths": [
            "bou_SOC_carbonsum_norm_null_con_clip.tif",
            "SOC_trend_30m_4_scaled_clip_norm_inverse_null_con_clip.tif",
        ],
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
        "carbon_paths": ["bou_SOC_carbonsum_norm_null_con_clip.tif"],
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
        "carbon_paths": ["bou_SOC_carbonsum_norm_null_con_clip.tif"],
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
        "tree canopy between 2.5m and 6m).",
        "path": "Final_Avoided_OpenWoodland_NaturalWoodedland_priority_norm.tif",
        "layer_type": 0,
        "carbon_paths": ["bou_SOC_carbonsum_norm_null_con_clip.tif"],
    },
    {
        "uuid": "7228ecae-8759-448d-b7ea-19366f74ee02",
        "name": "Avoided Wetland Conversion",
        "description": "Avoids carbon emissions by preventing the conversion "
        "of wetlands in areas with a high risk of wetland loss. Wetlands "
        "are defined as natural or semi-natural wetlands covered in "
        "permanent or seasonal herbaceous vegetation.",
        "path": "Final_Avoided_Wetland_priority_norm.tif",
        "layer_type": 0,
        "carbon_paths": ["bou_SOC_carbonsum_norm_null_con_clip.tif"],
    },
    {
        "uuid": "5475dd4a-5efc-4fb4-ae90-68ff4102591e",
        "name": "Fire Management",
        "description": "Provides additional sequestration and avoids carbon "
        "emissions by increasing resilience to catastrophic fire.",
        "path": "Final_Fire_Management_Priority_norm.tif",
        "layer_type": 0,
        "carbon_paths": [
            "bou_SOC_carbonsum_norm_null_con_clip.tif",
            "SOC_trend_30m_4_scaled_clip_norm_inverse_null_con_clip.tif",
        ],
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
        "carbon_paths": [
            "bou_SOC_carbonsum_norm_inverse_null_con_clip.tif",
            "SOC_trend_30m_4_scaled_clip_norm_inverse_null_con_clip.tif",
        ],
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
        "and 6m).",
        "path": "Final_Sananna_Restoration_priority_norm.tif",
        "layer_type": 0,
        "carbon_paths": [
            "bou_SOC_carbonsum_norm_inverse_null_con_clip.tif",
            "SOC_trend_30m_4_scaled_clip_norm_inverse_null_con_clip.tif",
        ],
    },
    {
        "uuid": "540470c7-0ed8-48af-8d91-63c15e6d69d7",
        "name": "Restoration - Wetland",
        "description": "Sequesters carbon through the restoration of wetland "
        "habitat. This pathway excludes the opportunity to "
        "convert non-native wetland regions to wetlands. Wetlands "
        "are defined as natural or semi-natural wetlands covered "
        "in permanent or seasonal herbaceous vegetation.",
        "path": "Final_Wetland_Restoration_priority_norm.tif",
        "layer_type": 0,
        "carbon_paths": [
            "bou_SOC_carbonsum_norm_inverse_null_con_clip.tif",
            "SOC_trend_30m_4_scaled_clip_norm_inverse_null_con_clip.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm.tif",
            "cccombo_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
            "Alien_Plant_Removal_years_re.tif",
            "Alien_Plant_Removal_carbonimpact_re.tif",
            "Alien_Plant_Removal_mtrends_re.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm.tif",
            "cccombo_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
        ],
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
        "pwls_paths": [
            "cccombo_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
            "Assisted_Nat_Regen_years.tif",
            "Assisted_Nat_Regen_carbonimpact.tif",
            "Assisted_Nat_Regen_NPV_re.tif",
            "Assisted_Nat_Regen_mtrends_re.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm_inverse.tif",
            "cccombo_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm_inverse.tif",
            "cccombo_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm.tif",
            "cccombo_clip_norm_inverse.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
            "Wattle_Naturally_years_re.tif",
            "Wattle_Naturally_carbonimpact_re.tif",
            "Wattle_Naturally_NPV.tif",
            "Wattle_Naturally_mtrends_re.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm.tif",
            "cccombo_clip_norm_inverse.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
            "Bush_Thinning_years_re.tif",
            "Bush_Thinning_carbonimpact.tif",
            "Bush_Thinning_NPV_re.tif",
            "Bush_Thinning_mtrends_re.tif",
        ],
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
        "pwls_paths": [
            "cccombo_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
            "Herding_4_Health_years.tif",
            "Herding_4_Health_carbonimpact_re.tif",
            "Herding_4_Health_NPV_re.tif",
            "Herding_4_Health_mtrends_re.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
        ],
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
        "pwls_paths": [
            "social_int_clip_norm.tif",
            "cccombo_clip_norm.tif",
            "ei_all_gknp_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
        ],
    },
    {
        "uuid": "92054916-e8ea-45a0-992c-b6273d1b75a7",
        "name": "Sustainable Crop Farming & Aquaponics",
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
        "pwls_paths": [
            "social_int_clip_norm_inverse.tif",
            "cccombo_clip_norm.tif",
            "biocombine_clip_norm.tif",
            "Policy.tif",
            "Eat_Fresh_years.tif",
            "Eat_Fresh_carbonimpact_re.tif",
            "Eat_Fresh_NPV.tif",
            "Eat_Fresh_mtrends.tif",
        ],
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
