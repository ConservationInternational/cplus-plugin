# -*- coding: utf-8 -*-
"""
Configurations for validation rules.
"""

from ...models.validation import RuleConfiguration, ValidationCategory
from ...utils import tr


# Same CRS validation
crs_validation_config = RuleConfiguration(
    ValidationCategory.ERROR,
    tr("Must have the same CRS"),
    "Same CRS Check",
    tr("Use the warp tool to reproject the datasets to the same CRS"),
)


# CRS type validation
projected_crs_validation_config = RuleConfiguration(
    ValidationCategory.ERROR,
    tr("Must have a projected CRS type"),
    "CRS Type Check",
    tr("Use the warp tool to reproject the datasets to a projected CRS"),
)


# Data type validation
raster_validation_config = RuleConfiguration(
    ValidationCategory.ERROR,
    tr("Must be of raster data type"),
    "Raster Check",
    tr("Ensure all datasets are of raster data type"),
)


# Spatial resolution validation
resolution_validation_config = RuleConfiguration(
    ValidationCategory.ERROR,
    tr("Must have the same spatial resolution"),
    "Resolution Check",
    tr("Use the warp tool to resize the raster cells"),
)


# NoData validation check
no_data_validation_config = RuleConfiguration(
    ValidationCategory.ERROR,
    tr("NoData value must be -9999"),
    "NoData Value Check",
    tr("Use the 'Fill nodata' or 'Translate' tool to change the NoData value"),
)
