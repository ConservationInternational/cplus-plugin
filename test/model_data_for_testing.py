# -*- coding: utf-8 -*-
"""
Functions for providing model test data.
"""
import os
import uuid
from uuid import UUID

from cplus_plugin.models.base import ImplementationModel, LayerType, NcsPathway


VALID_NCS_UUID_STR = "b5338edf-f3cc-4040-867d-be9651a28b63"
INVALID_NCS_UUID_STR = "4c6b31a1-3ff3-43b2-bfe2-45519a975955"
IMPLEMENTATION_MODEL_UUID_STR = "01e3a612-118d-4d94-9a5a-09c4b9168288"


def get_valid_ncs_pathway() -> NcsPathway:
    """Creates a valid NCS pathway object."""
    path = os.path.join(os.path.dirname(__file__), "tenbytenraster.tif")

    return NcsPathway(
        UUID(VALID_NCS_UUID_STR),
        "Valid NCS Pathway",
        "Description for valid NCS",
        path,
        LayerType.RASTER,
    )


def get_invalid_ncs_pathway() -> NcsPathway:
    """Creates an invalid NCS pathway object i.e. path not set."""
    return NcsPathway(
        UUID(INVALID_NCS_UUID_STR),
        "Invalid NCS Pathway",
        "Description for invalid NCS",
        "",
    )


def get_implementation_model() -> ImplementationModel:
    """Creates a test ImplementationModel object."""
    return ImplementationModel(
        UUID(IMPLEMENTATION_MODEL_UUID_STR),
        "Test Implementation Model",
        "Description for test implementation model",
    )
