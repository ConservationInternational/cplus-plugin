# -*- coding: utf-8 -*-

"""Helper functions for supporting model management."""

from dataclasses import field, fields
import typing
import uuid

from .base import (
    BaseModelComponent,
    BaseModelComponentType,
    ImplementationModel,
    LayerModelComponent,
    LayerModelComponentType,
    LayerType,
    NcsPathway,
    SpatialExtent,
)
from ..definitions.constants import (
    CARBON_COEFFICIENT_ATTRIBUTE,
    CARBON_PATHS_ATTRIBUTE,
    FILL_STYLE_ATTRIBUTE,
    NAME_ATTRIBUTE,
    DESCRIPTION_ATTRIBUTE,
    LAYER_TYPE_ATTRIBUTE,
    PATH_ATTRIBUTE,
    PRIORITY_LAYERS_SEGMENT,
    USER_DEFINED_ATTRIBUTE,
    UUID_ATTRIBUTE,
)
from ..definitions.defaults import DEFAULT_CRS_ID

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
)


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
        UUID_ATTRIBUTE: model_uuid,
        NAME_ATTRIBUTE: model_component.name,
        DESCRIPTION_ATTRIBUTE: model_component.description,
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
        uuid.UUID(source_dict[UUID_ATTRIBUTE]),
        source_dict[NAME_ATTRIBUTE],
        source_dict[DESCRIPTION_ATTRIBUTE],
    )


def create_layer_component(
    source_dict,
    model_cls: typing.Callable[
        [uuid.UUID, str, str, str, LayerType, bool], LayerModelComponentType
    ],
) -> typing.Union[LayerModelComponent, None]:
    """Factory method for creating a layer model component using
    attribute values defined in a dictionary.

    :param source_dict: Dictionary containing property values.
    :type source_dict: dict

    :param model_cls: Callable class that will be created based on the
    input argument values from the dictionary.
    :type model_cls: LayerModelComponent

    :returns: Layer model component object with property values set
    from the dictionary.
    :rtype: LayerModelComponent
    """
    if UUID_ATTRIBUTE not in source_dict:
        return None

    source_uuid = source_dict[UUID_ATTRIBUTE]
    if isinstance(source_uuid, str):
        source_uuid = uuid.UUID(source_uuid)

    kwargs = {}
    if PATH_ATTRIBUTE in source_dict:
        kwargs[PATH_ATTRIBUTE] = source_dict[PATH_ATTRIBUTE]

    if LAYER_TYPE_ATTRIBUTE in source_dict:
        kwargs[LAYER_TYPE_ATTRIBUTE] = LayerType(int(source_dict[LAYER_TYPE_ATTRIBUTE]))

    if USER_DEFINED_ATTRIBUTE in source_dict:
        kwargs[USER_DEFINED_ATTRIBUTE] = bool(source_dict[USER_DEFINED_ATTRIBUTE])

    return model_cls(
        source_uuid,
        source_dict[NAME_ATTRIBUTE],
        source_dict[DESCRIPTION_ATTRIBUTE],
        **kwargs
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
    ncs = create_layer_component(source_dict, NcsPathway)

    # We are checking because of the various iterations of the attributes
    # in the NcsPathway class where some of these attributes might
    # be missing.
    if CARBON_PATHS_ATTRIBUTE in source_dict:
        ncs.carbon_paths = source_dict[CARBON_PATHS_ATTRIBUTE]

    carbon_coefficient_attr = CARBON_COEFFICIENT_ATTRIBUTE
    if carbon_coefficient_attr in source_dict:
        ncs.carbon_coefficient = source_dict[CARBON_COEFFICIENT_ATTRIBUTE]

    return ncs


def create_implementation_model(source_dict) -> typing.Union[ImplementationModel, None]:
    """Factory method for creating an implementation model using
    attribute values defined in a dictionary.

    :param source_dict: Dictionary containing property values.
    :type source_dict: dict

    :returns: Implementation model with property values set
    from the dictionary.
    :rtype: ImplementationModel
    """
    implementation_model = create_layer_component(source_dict, ImplementationModel)
    if PRIORITY_LAYERS_SEGMENT in source_dict.keys():
        implementation_model.priority_layers = source_dict[PRIORITY_LAYERS_SEGMENT]

    # Set style
    if FILL_STYLE_ATTRIBUTE in source_dict.keys():
        implementation_model.fill_style = source_dict[FILL_STYLE_ATTRIBUTE]

    return implementation_model


def layer_component_to_dict(
    layer_component: LayerModelComponentType, uuid_to_str=True
) -> dict:
    """Creates a dictionary containing attribute
    name-value pairs from a layer model component object.

    :param layer_component: Source layer model component object whose
    values are to be mapped to the corresponding
    attribute names.
    :type layer_component: LayerModelComponent

    :param uuid_to_str: Set True to convert the UUID to a
    string equivalent, else False. Some serialization engines
    such as JSON are unable to handle UUID objects hence the need
    to convert to string.
    :type uuid_to_str: bool

    :returns: Returns a dictionary item containing attribute
    name-value pairs.
    :rtype: dict
    """
    base_attrs = model_component_to_dict(layer_component, uuid_to_str)
    base_attrs[PATH_ATTRIBUTE] = layer_component.path
    base_attrs[LAYER_TYPE_ATTRIBUTE] = int(layer_component.layer_type)
    base_attrs[USER_DEFINED_ATTRIBUTE] = layer_component.user_defined

    return base_attrs


def ncs_pathway_to_dict(ncs_pathway: NcsPathway, uuid_to_str=True) -> dict:
    """Creates a dictionary containing attribute
    name-value pairs from an NCS pathway object.

    This function has been retained for legacy support.

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
    base_ncs_dict = layer_component_to_dict(ncs_pathway, uuid_to_str)
    base_ncs_dict[CARBON_PATHS_ATTRIBUTE] = ncs_pathway.carbon_paths
    base_ncs_dict[CARBON_COEFFICIENT_ATTRIBUTE] = ncs_pathway.carbon_coefficient

    return base_ncs_dict


def clone_layer_component(
    layer_component: LayerModelComponent,
    model_cls: typing.Callable[[uuid.UUID, str, str], LayerModelComponentType],
) -> typing.Union[LayerModelComponent, None]:
    """Clones a layer-based model component.

    :param layer_component: Layer-based model component to clone.
    :type layer_component: LayerModelComponent

    :param model_cls: Callable class that will be created based on the
    input argument values from the dictionary.
    :type model_cls: LayerModelComponent

    :returns: A new instance of the cloned model component. It
    will return None if the input is not a layer-based model
    component.
    :rtype: LayerModelComponent
    """
    if not isinstance(layer_component, LayerModelComponent):
        return None

    cloned_component = model_cls(
        layer_component.uuid, layer_component.name, layer_component.description
    )

    for f in fields(layer_component):
        attr_val = getattr(layer_component, f.name)
        setattr(cloned_component, f.name, attr_val)

    return cloned_component


def clone_ncs_pathway(ncs: NcsPathway) -> NcsPathway:
    """Creates a deep copy of the given NCS pathway.

    :param ncs: NCS pathway to clone.
    :type ncs: NcsPathway

    :returns: A deep copy of the original NCS pathway object.
    :rtype: NcsPathway
    """
    return clone_layer_component(ncs, NcsPathway)


def clone_implementation_model(
    implementation_model: ImplementationModel,
) -> ImplementationModel:
    """Creates a deep copy of the given implementation model.

    :param implementation_model: Implementation model to clone.
    :type implementation_model: ImplementationModel

    :returns: A deep copy of the original implementation model object.
    :rtype: ImplementationModel
    """
    imp_model = clone_layer_component(implementation_model, ImplementationModel)
    if imp_model is None:
        return None

    pathways = implementation_model.pathways
    cloned_pathways = []
    for p in pathways:
        cloned_ncs = clone_ncs_pathway(p)
        if cloned_ncs is not None:
            cloned_pathways.append(cloned_ncs)

    imp_model.pathways = cloned_pathways

    return imp_model


def copy_layer_component_attributes(
    target: LayerModelComponent, source: LayerModelComponent
) -> LayerModelComponent:
    """Copies the attribute values of source to target. The uuid
    attribute value is not copied as well as the layer attribute.
    However, for the latter, the path is copied.

    :param target: Target object whose attribute values will be updated.
    :type target: LayerModelComponent

    :param source: Source object whose attribute values will be copied to
    the target.
    :type source: LayerModelComponent

    :returns: Target object containing the updated attribute values apart
    for the uuid whose value will not change.
    :rtype: LayerModelComponent
    """
    if not isinstance(target, LayerModelComponent) or not isinstance(
        source, LayerModelComponent
    ):
        raise TypeError(
            "Source or target objects are not of type 'LayerModelComponent'"
        )

    for f in fields(source):
        # Exclude uuid
        if f.name == UUID_ATTRIBUTE:
            continue
        attr_val = getattr(source, f.name)
        setattr(target, f.name, attr_val)

    # Force layer to be set/updated
    target.update_layer_type()

    return target


def extent_to_qgs_rectangle(
    spatial_extent: SpatialExtent,
) -> typing.Union[QgsRectangle, None]:
    """Returns a QgsRectangle object from the SpatialExtent object.

    If the SpatialExtent is invalid (i.e. less than four items) then it
    will return None.

    :param spatial_extent: Spatial extent data model that defines the
    scenario bounds.
    :type spatial_extent: SpatialExtent

    :returns: QGIS rectangle defining the bounds for the scenario.
    :rtype: QgsRectangle
    """
    if len(spatial_extent.bbox) < 4:
        return None

    return QgsRectangle(
        spatial_extent.bbox[0],
        spatial_extent.bbox[2],
        spatial_extent.bbox[1],
        spatial_extent.bbox[3],
    )


def extent_to_project_crs_extent(
    spatial_extent: SpatialExtent, project: QgsProject = None
) -> typing.Union[QgsRectangle, None]:
    """Transforms SpatialExtent model to an QGIS extent based
    on the CRS of the given project.

    :param spatial_extent: Spatial extent data model that defines the
    scenario bounds.
    :type spatial_extent: SpatialExtent

    :param project: Project whose CRS will be used to determine
    the values of the output extent.
    :type project: QgsProject

    :returns: Output extent in the project's CRS. If the input extent
    is invalid, this function will return None.
    :rtype: QgsRectangle
    """
    input_rect = extent_to_qgs_rectangle(spatial_extent)
    if input_rect is None:
        return None

    default_crs = QgsCoordinateReferenceSystem.fromEpsgId(DEFAULT_CRS_ID)
    if not default_crs.isValid():
        return None

    if project is None:
        project = QgsProject.instance()

    target_crs = project.crs()
    if default_crs == target_crs:
        # No need for transformation
        return input_rect

    coordinate_xform = QgsCoordinateTransform(default_crs, project.crs(), project)
    return coordinate_xform.transformBoundingBox(input_rect)
