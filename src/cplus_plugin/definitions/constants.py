# -*- coding: utf-8 -*-
"""
Definitions for application constants.
"""


NCS_PATHWAY_SEGMENT = "ncs_pathways"
NCS_CARBON_SEGMENT = "ncs_carbon"
PRIORITY_LAYERS_SEGMENT = "priority_layers"
MASK_PATHS_SEGMENT = "mask_paths"
NPV_PRIORITY_LAYERS_SEGMENT = "npv"
COMPARISON_REPORT_SEGMENT = "comparison_reports"

# Naming for outputs sub-folder relative to base directory
OUTPUTS_SEGMENT = "outputs"

ACTIVITY_GROUP_LAYER_NAME = "Activity Maps"
ACTIVITY_WEIGHTED_GROUP_NAME = "Weighted Activity Maps"
NCS_PATHWAYS_GROUP_LAYER_NAME = "NCS Pathways Maps"
NCS_PATHWAYS_WEIGHTED_GROUP_LAYER_NAME = "Weighted NCS Pathways Maps"

ACTIVITY_NAME = "Activity"

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
PATHWAY_TYPE_ATTRIBUTE = "pathway_type"
PIXEL_VALUE_ATTRIBUTE = "style_pixel_value"
PROFILES_ATTRIBUTE = "profiles"
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
MANUAL_NPV_ATTRIBUTE = "manual_npv"
HEADER_ATTRIBUTE = "header"
EXPRESSION_ATTRIBUTE = "expression"
ALIGNMENT_ATTRIBUTE = "alignment"
AUTO_CALCULATED_ATTRIBUTE = "auto_calculated"
METRIC_TYPE_ATTRIBUTE = "metric_type"
NUMBER_FORMATTER_ENABLED_ATTRIBUTE = "number_formatter_enabled"
NUMBER_FORMATTER_ID_ATTRIBUTE = "number_formatter_type_id"
NUMBER_FORMATTER_PROPS_ATTRIBUTE = "number_formatter_props"

ACTIVITY_IDENTIFIER_PROPERTY = "activity_identifier"
NCS_PATHWAY_IDENTIFIER_PROPERTY = "pathway_identifier"
MULTI_ACTIVITY_IDENTIFIER_PROPERTY = "activity_identifiers"
MULTI_PATHWAY_IDENTIFIER_PROPERTY = "pathway_identifiers"
NPV_COLLECTION_PROPERTY = "npv_collection"
METRIC_IDENTIFIER_PROPERTY = "metric_identifier"
METRIC_COLUMNS_PROPERTY = "metric_columns"
METRIC_CONFIGURATION_PROPERTY = "metric_configuration"
ACTIVITY_METRICS_PROPERTY = "activity_metrics"
METRIC_COLLECTION_PROPERTY = "metrics_collection"
METRIC_PROFILE_PROPERTY = "metrics_profile"
CURRENT_PROFILE_PROPERTY = "current_profile"

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
