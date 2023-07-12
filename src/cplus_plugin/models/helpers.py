# -*- coding: utf-8 -*-

"""Helper functions for supporting model management."""

import typing
import uuid

from .base import BaseModelComponent, BaseModelComponentType, NcsPathway, LayerType


def model_component_to_dict(
    model_component: BaseModelComponentType, uuid_to_str=True
) -> dict:
    """Creates a dictionary containing the base attribute
    name-value pairs from a model component object.

    :param model_component: Source model component object whose
    values are to be mapped to the corresponding
    attribute names.
    :type model_component: BaseModelComponent

    :param uuid_to_str: Set True to convert the UUID to a
    string equivalent, else False. Some serialization engines
    such as JSON are unable to handle UUID objects hence the need
    to convert to string.
    :type uuid_to_str: bool

    :returns: Returns a dictionary item containing attribute
    name-value pairs.
    :rtype: dict
    """
    model_uuid = model_component.uuid
    if uuid_to_str:
        model_uuid = str(model_uuid)

    return {
        "uuid": model_uuid,
        "name": model_component.name,
        "description": model_component.description,
    }


def create_model_component(
    source_dict: dict,
    model_cls: typing.Callable[[uuid.UUID, str, str], BaseModelComponentType],
) -> typing.Union[BaseModelComponentType, None]:
    """Factory method for creating and setting attribute values
    for a base model component object.

    :param source_dict: Dictionary containing attribute values.
    :type source_dict: dict

    :param model_cls: Callable class that will be created based on the
    input argument values from the dictionary.
    :type model_cls: BaseModelComponent

    :returns: Base model component object with property values
    derived from the dictionary.
    :rtype: BaseModelComponent
    """
    if not issubclass(model_cls, BaseModelComponent):
        return None

    return model_cls(
        uuid.UUID(source_dict["uuid"]), source_dict["name"], source_dict["description"]
    )


def create_ncs_pathway(source_dict) -> typing.Union[NcsPathway, None]:
    """Factory method for creating an NcsPathway object using
    attribute values defined in a dictionary.

    :param source_dict: Dictionary containing property values.
    :type source_dict: dict

    :returns: NCS pathway object with property values set
    from the dictionary.
    :rtype: NcsPathway
    """
    if "uuid" not in source_dict:
        return None

    source_uuid = source_dict["uuid"]
    if isinstance(source_uuid, str):
        source_uuid = uuid.UUID(source_uuid)

    return NcsPathway(
        source_uuid,
        source_dict["name"],
        source_dict["description"],
        source_dict["path"],
        LayerType(int(source_dict["layer_type"])),
        bool(source_dict["user_defined"]),
    )


def ncs_pathway_to_dict(ncs_pathway: NcsPathway, uuid_to_str=True) -> dict:
    """Creates a dictionary containing attribute
    name-value pairs from an NCS pathway object.

    :param ncs_pathway: Source NCS pathway object whose
    values are to be mapped to the corresponding
    attribute names.
    :type ncs_pathway: NcsPathway

    :param uuid_to_str: Set True to convert the UUID to a
    string equivalent, else False. Some serialization engines
    such as JSON are unable to handle UUID objects hence the need
    to convert to string.
    :type uuid_to_str: bool

    :returns: Returns a dictionary item containing attribute
    name-value pairs.
    :rtype: dict
    """
    base_attrs = model_component_to_dict(ncs_pathway, uuid_to_str)
    base_attrs["path"] = ncs_pathway.path
    base_attrs["layer_type"] = int(ncs_pathway.layer_type)
    base_attrs["user_defined"] = ncs_pathway.user_defined

    return base_attrs
