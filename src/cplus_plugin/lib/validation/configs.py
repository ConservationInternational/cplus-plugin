# -*- coding: utf-8 -*-
"""
Configurations for validation rules.
"""

from ...models.validation import RuleConfiguration, ValidationCategory
from ...utils import tr


# CRS validation
crs_validation_config = RuleConfiguration(
    ValidationCategory.ERROR,
    tr("Must have the same CRS"),
    "CRS Check",
    tr("Use the warp tool to reproject the datasets"),
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


# Spatial resolution validation for NCS carbon layers,
# which is less strict and hence, is tagged as a warning
carbon_resolution_validation_config = RuleConfiguration(
    ValidationCategory.WARNING,
    tr("Should have the same spatial resolution"),
    "Carbon Resolution Check",
    tr("Use the warp tool to resize the raster cells"),
)


# NoData validation check
no_data_validation_config = RuleConfiguration(
    ValidationCategory.ERROR,
    tr("NoData value must be -9999"),
    "NoData Value Check",
    tr("Use the 'Fill nodata' or 'Translate' tool to change the nodata value"),
)
