# -*- coding: utf-8 -*-
"""
Definitions for application constants.
"""


NCS_PATHWAY_SEGMENT = "ncs_pathways"
NCS_CARBON_SEGMENT = "ncs_carbon"
PRIORITY_LAYERS_SEGMENT = "priority_layers"
NPV_PRIORITY_LAYERS_SEGMENT = "npv"

# Naming for outputs sub-folder relative to base directory
OUTPUTS_SEGMENT = "outputs"

ACTIVITY_GROUP_LAYER_NAME = "Activity Maps"
ACTIVITY_WEIGHTED_GROUP_NAME = "Weighted Activity Maps"
NCS_PATHWAYS_GROUP_LAYER_NAME = "NCS Pathways Maps"

# Attribute names
CARBON_COEFFICIENT_ATTRIBUTE = "carbon_coefficient"
CARBON_PATHS_ATTRIBUTE = "carbon_paths"
COLOR_RAMP_PROPERTIES_ATTRIBUTE = "color_ramp"
COLOR_RAMP_TYPE_ATTRIBUTE = "ramp_type"
DESCRIPTION_ATTRIBUTE = "description"
ACTIVITY_LAYER_STYLE_ATTRIBUTE = "activity_layer"
ACTIVITY_SCENARIO_STYLE_ATTRIBUTE = "scenario_layer"
LAYER_TYPE_ATTRIBUTE = "layer_type"
NAME_ATTRIBUTE = "name"
PATH_ATTRIBUTE = "path"
PATHWAYS_ATTRIBUTE = "pathways"
PIXEL_VALUE_ATTRIBUTE = "style_pixel_value"
STYLE_ATTRIBUTE = "style"
USER_DEFINED_ATTRIBUTE = "user_defined"
UUID_ATTRIBUTE = "uuid"
YEARS_ATTRIBUTE = "years"
DISCOUNT_ATTRIBUTE = "discount"
ABSOLUTE_NPV_ATTRIBUTE = "absolute_npv"
NORMALIZED_NPV_ATTRIBUTE = "normalized_npv"
YEARLY_RATES_ATTRIBUTE = "yearly_rates"
ENABLED_ATTRIBUTE = "enabled"
MIN_VALUE_ATTRIBUTE = "minimum_value"
MAX_VALUE_ATTRIBUTE = "maximum_value"
COMPUTED_ATTRIBUTE = "use_computed"
NPV_MAPPINGS_ATTRIBUTE = "mappings"
REMOVE_EXISTING_ATTRIBUTE = "remove_existing"

ACTIVITY_IDENTIFIER_PROPERTY = "activity_identifier"
NPV_COLLECTION_PROPERTY = "npv_collection"

# Option / settings keys
CPLUS_OPTIONS_KEY = "cplus_main"
LOG_OPTIONS_KEY = "cplus_log"
REPORTS_OPTIONS_KEY = "cplus_report"

# Headers for financial NPV computation
YEAR_HEADER = "Year"
TOTAL_PROJECTED_COSTS_HEADER = "Projected Total Costs/ha (US$)"
TOTAL_PROJECTED_REVENUES_HEADER = "Projected Total Revenues/ha (US$)"
DISCOUNTED_VALUE_HEADER = "Discounted Value (US$)"
MAX_YEARS = 99

NO_DATA_VALUE = -9999
