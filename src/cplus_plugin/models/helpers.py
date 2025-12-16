# -*- coding: utf-8 -*-

"""Helper functions for supporting model management."""
import sys
from dataclasses import asdict, fields
import typing
import uuid

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRasterLayer,
    QgsReadWriteContext,
    QgsRectangle,
)

from qgis.PyQt import QtCore

from .base import (
    BaseModelComponent,
    BaseModelComponentType,
    Activity,
    LayerModelComponent,
    LayerModelComponentType,
    LayerType,
    ModelComponentType,
    NcsPathway,
    NcsPathwayType,
    ResultInfo,
    ScenarioResult,
    SpatialExtent,
)
from ..definitions.constants import (
    ABSOLUTE_ATTRIBUTE,
    ABSOLUTE_NPV_ATTRIBUTE,
    ACTIVITY_IDENTIFIER_PROPERTY,
    ACTIVITY_METRICS_PROPERTY,
    ALIGNMENT_ATTRIBUTE,
    ALLOWABLE_MIN_ATTRIBUTE,
    ALLOWABLE_MAX_ATTRIBUTE,
    AUTO_CALCULATED_ATTRIBUTE,
    BASE_NAME_ATTRIBUTE,
    COMPONENT_UUID_ATTRIBUTE,
    COMPONENT_ID_ATTRIBUTE,
    COMPONENT_TYPE_ATTRIBUTE,
    COMPONENTS_ATTRIBUTE,
    COMPUTED_ATTRIBUTE,
    CURRENT_PROFILE_PROPERTY,
    DISCOUNT_ATTRIBUTE,
    DISPLAY_NAME_ATTRIBUTE,
    DESCRIPTION_ATTRIBUTE,
    ENABLED_ATTRIBUTE,
    EXPRESSION_ATTRIBUTE,
    HEADER_ATTRIBUTE,
    ID_ATTRIBUTE,
    INPUT_RANGE_ATTRIBUTE,
    LAST_UPDATED_ATTRIBUTE,
    LAST_UPDATED_DATE_ATTRIBUTE,
    LAYER_TYPE_ATTRIBUTE,
    MANUAL_NPV_ATTRIBUTE,
    MASK_PATHS_SEGMENT,
    METRIC_CONFIGURATION_PROPERTY,
    METRIC_IDENTIFIER_PROPERTY,
    METRIC_TYPE_ATTRIBUTE,
    NPV_MAPPINGS_ATTRIBUTE,
    MAX_VALUE_ATTRIBUTE,
    MIN_VALUE_ATTRIBUTE,
    METRIC_COLUMNS_PROPERTY,
    MULTI_ACTIVITY_IDENTIFIER_PROPERTY,
    NAME_ATTRIBUTE,
    NCS_PATHWAY_IDENTIFIER_PROPERTY,
    NORMALIZED_NPV_ATTRIBUTE,
    NUMBER_FORMATTER_ENABLED_ATTRIBUTE,
    NUMBER_FORMATTER_ID_ATTRIBUTE,
    NUMBER_FORMATTER_PROPS_ATTRIBUTE,
    PATH_ATTRIBUTE,
    PATHWAY_TYPE_ATTRIBUTE,
    PATHWAY_TYPE_OPTIONS_ATTRIBUTE,
    PATHWAY_SUITABILITY_INDEX_ATTRIBUTE,
    PIXEL_VALUE_ATTRIBUTE,
    PRIORITY_LAYERS_SEGMENT,
    PROFILES_ATTRIBUTE,
    RASTER_COLLECTION_ATTRIBUTE,
    REMOVE_EXISTING_ATTRIBUTE,
    RESULT_COLLECTION_ATTRIBUTE,
    STYLE_ATTRIBUTE,
    USER_DEFINED_ATTRIBUTE,
    UUID_ATTRIBUTE,
    YEARS_ATTRIBUTE,
    YEARLY_RATES_ATTRIBUTE,
    SKIP_RASTER_ATTRIBUTE,
    VALUE_INFO_ATTRIBUTE,
    NORMALIZED_ATTRIBUTE,
    MIN_VALUE_ATTRIBUTE_KEY,
    MAX_VALUE_ATTRIBUTE_KEY,
    PREFIX_ATTRIBUTE,
    SUFFIX_ATTRIBUTE,
)
from ..definitions.defaults import DEFAULT_CRS_ID, QGIS_GDAL_PROVIDER
from .financial import ActivityNpv, ActivityNpvCollection, NpvParameters
from .report import (
    ActivityColumnMetric,
    MetricColumn,
    MetricConfiguration,
    MetricConfigurationProfile,
    MetricProfileCollection,
    MetricType,
)
from .constant_raster import (
    ConstantRasterCollection,
    ConstantRasterComponent,
    ConstantRasterInfo,
    ConstantRasterMetadata,
    InputRange,
)
from .base import ModelComponentType

from ..utils import (
    log,
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
        **kwargs,
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
    if PATHWAY_TYPE_ATTRIBUTE in source_dict:
        ncs.pathway_type = NcsPathwayType.from_int(source_dict[PATHWAY_TYPE_ATTRIBUTE])
    else:
        # Assign undefined
        ncs.pathway_type = NcsPathwayType.UNDEFINED

    if PRIORITY_LAYERS_SEGMENT in source_dict.keys():
        ncs.priority_layers = source_dict[PRIORITY_LAYERS_SEGMENT]

    if PATHWAY_TYPE_OPTIONS_ATTRIBUTE in source_dict:
        ncs.type_options = source_dict[PATHWAY_TYPE_OPTIONS_ATTRIBUTE]

    if PATHWAY_SUITABILITY_INDEX_ATTRIBUTE in source_dict:
        ncs.suitability_index = source_dict[PATHWAY_SUITABILITY_INDEX_ATTRIBUTE]

    return ncs


def create_activity(source_dict) -> typing.Union[Activity, None]:
    """Factory method for creating an activity using
    attribute values defined in a dictionary.

    :param source_dict: Dictionary containing property values.
    :type source_dict: dict

    :returns: activity with property values set
    from the dictionary.
    :rtype: Activity
    """
    activity = create_layer_component(source_dict, Activity)

    if MASK_PATHS_SEGMENT in source_dict.keys():
        activity.mask_paths = source_dict[MASK_PATHS_SEGMENT]

    # Set style
    if STYLE_ATTRIBUTE in source_dict.keys():
        activity.layer_styles = source_dict[STYLE_ATTRIBUTE]

    # Set styling pixel value
    if PIXEL_VALUE_ATTRIBUTE in source_dict.keys():
        activity.style_pixel_value = source_dict[PIXEL_VALUE_ATTRIBUTE]

    return activity


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
    try:
        base_attrs[LAYER_TYPE_ATTRIBUTE] = int(layer_component.layer_type)
    except TypeError:
        if base_attrs["path"].endswith(".tif"):
            base_attrs[LAYER_TYPE_ATTRIBUTE] = 0
        elif base_attrs["path"].endswith(".shp"):
            base_attrs[LAYER_TYPE_ATTRIBUTE] = 1
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
    base_ncs_dict[PATHWAY_TYPE_ATTRIBUTE] = ncs_pathway.pathway_type
    base_ncs_dict[PRIORITY_LAYERS_SEGMENT] = ncs_pathway.priority_layers
    base_ncs_dict[PATHWAY_TYPE_OPTIONS_ATTRIBUTE] = ncs_pathway.type_options
    base_ncs_dict[PATHWAY_SUITABILITY_INDEX_ATTRIBUTE] = ncs_pathway.suitability_index

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


def clone_activity(
    activity: Activity,
) -> Activity:
    """Creates a deep copy of the given activity.

    :param activity: activity to clone.
    :type activity: Activity

    :returns: A deep copy of the original activity object.
    :rtype: Activity
    """
    activity = clone_layer_component(activity, Activity)
    if activity is None:
        return None

    pathways = activity.pathways
    cloned_pathways = []
    for p in pathways:
        cloned_ncs = clone_ncs_pathway(p)
        if cloned_ncs is not None:
            cloned_pathways.append(cloned_ncs)

    activity.pathways = cloned_pathways

    return activity


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


def extent_to_url_param(rect_extent: QgsRectangle) -> str:
    """Converts the bounding box in a QgsRectangle object to the equivalent
    param for use in a URL. 'bbox' is appended as a prefix in the URL query
    part.

    :param rect_extent: Spatial extent that defines the AOI.
    :type rect_extent: QgsRectangle

    :returns: String representing the param defining the extents of the AOI.
    If the extent is empty, it will return an empty string.
    :rtype: str
    """
    if rect_extent.isEmpty():
        return ""

    url_query = QtCore.QUrlQuery()
    url_query.addQueryItem(
        "bbox",
        f"{rect_extent.xMinimum()!s},{rect_extent.yMinimum()!s},{rect_extent.xMaximum()!s},{rect_extent.yMaximum()!s}",
    )

    return url_query.toString()


def extent_to_project_crs_extent(
    spatial_extent: SpatialExtent,
    project: QgsProject = None,
    source_crs: QgsCoordinateReferenceSystem = None,
) -> typing.Union[QgsRectangle, None]:
    """Transforms SpatialExtent model to an QGIS extent based
    on the CRS of the given project.

    :param spatial_extent: Spatial extent data model that defines the
    scenario bounds.
    :type spatial_extent: SpatialExtent

    :param project: Project whose CRS will be used to determine
    the values of the output extent.
    :type project: QgsProject

    :param source_crs: Specify a source CRS to use for the transformation
    otherwise it will revert to the default which is WGS84.
    :type source_crs: QgsCoordinateReferenceSystem

    :returns: Output extent in the project's CRS. If the input extent
    is invalid, this function will return None.
    :rtype: QgsRectangle
    """
    input_rect = extent_to_qgs_rectangle(spatial_extent)
    if input_rect is None:
        return None

    default_crs = source_crs or QgsCoordinateReferenceSystem.fromEpsgId(DEFAULT_CRS_ID)
    if not default_crs.isValid():
        return None

    if project is None:
        project = QgsProject.instance()

    target_crs = project.crs()
    if default_crs == target_crs:
        # No need for transformation
        return input_rect

    try:
        coordinate_xform = QgsCoordinateTransform(default_crs, project.crs(), project)
        return coordinate_xform.transformBoundingBox(input_rect)
    except Exception as e:
        log(f"{e}, using the default input extent.")

    return input_rect


def layer_from_scenario_result(
    result: ScenarioResult,
) -> typing.Optional[QgsRasterLayer]:
    """Gets the scenario output layer from the results of the
    analysis.

    :returns: Raster layer corresponding to the output scenario
    path or None if the file does not exist or if the raster layer
    is invalid.
    :rtype: QgsRasterLayer
    """
    layer_file = result.analysis_output.get("OUTPUT")

    layer = QgsRasterLayer(layer_file, result.scenario.name, QGIS_GDAL_PROVIDER)
    if not layer.isValid():
        return None

    return layer


def metric_column_to_dict(metric_column: MetricColumn) -> dict:
    """Converts a metric column object to a dictionary representation.

    :param metric_column: Metric column to be serialized to a dictionary.
    :type metric_column: MetricColumn

    :returns: A dictionary containing attribute values of a metric column.
    :rtype: dict
    """
    formatter_props = metric_column.number_formatter.configuration(
        QgsReadWriteContext()
    )
    formatter_id = metric_column.number_formatter.id()
    if formatter_id == "default":
        formatter_props = {}

    return {
        NAME_ATTRIBUTE: metric_column.name,
        HEADER_ATTRIBUTE: metric_column.header,
        EXPRESSION_ATTRIBUTE: metric_column.expression,
        ALIGNMENT_ATTRIBUTE: metric_column.alignment,
        AUTO_CALCULATED_ATTRIBUTE: metric_column.auto_calculated,
        NUMBER_FORMATTER_ENABLED_ATTRIBUTE: metric_column.format_as_number,
        NUMBER_FORMATTER_ID_ATTRIBUTE: formatter_id,
        NUMBER_FORMATTER_PROPS_ATTRIBUTE: formatter_props,
    }


def create_metric_column(metric_column_dict: dict) -> typing.Optional[MetricColumn]:
    """Creates a metric column from the equivalent dictionary representation.

    :param metric_column_dict: Dictionary containing information for deserializing
    the dict to a metric column.
    :type metric_column_dict: dict

    :returns: Metric column object or None if the deserialization failed.
    :rtype: MetricColumn
    """
    number_formatter = QgsApplication.numericFormatRegistry().create(
        metric_column_dict[NUMBER_FORMATTER_ID_ATTRIBUTE],
        metric_column_dict[NUMBER_FORMATTER_PROPS_ATTRIBUTE],
        QgsReadWriteContext(),
    )

    return MetricColumn(
        metric_column_dict[NAME_ATTRIBUTE],
        metric_column_dict[HEADER_ATTRIBUTE],
        metric_column_dict[EXPRESSION_ATTRIBUTE],
        metric_column_dict[ALIGNMENT_ATTRIBUTE],
        metric_column_dict[AUTO_CALCULATED_ATTRIBUTE],
        metric_column_dict[NUMBER_FORMATTER_ENABLED_ATTRIBUTE],
        number_formatter,
    )


def activity_metric_to_dict(activity_metric: ActivityColumnMetric) -> dict:
    """Converts an activity column metric to a dictionary representation.

    :param activity_metric: Activity column metric to be serialized to a dictionary.
    :type activity_metric: ActivityColumnMetric

    :returns: A dictionary containing attribute values of an
    activity column metric.
    :rtype: dict
    """
    return {
        ACTIVITY_IDENTIFIER_PROPERTY: str(activity_metric.activity.uuid),
        METRIC_IDENTIFIER_PROPERTY: activity_metric.metric_column.name,
        METRIC_TYPE_ATTRIBUTE: activity_metric.metric_type.value,
        EXPRESSION_ATTRIBUTE: activity_metric.expression,
    }


def create_activity_metric(
    activity_metric_dict: dict, activity: Activity, metric_column: MetricColumn
) -> typing.Optional[ActivityColumnMetric]:
    """Creates a metric column from the equivalent dictionary representation.

    :param activity_metric_dict: Dictionary containing information for deserializing
    the dict to a metric column.
    :type activity_metric_dict: dict

    :param activity: Referenced activity matching the saved UUID.
    :type activity: str

    :param metric_column: Referenced metric column matching the saved name.
    :type metric_column: MetricColumn

    :returns: Metric column object or None if the deserialization failed.
    :rtype: MetricColumn
    """
    return ActivityColumnMetric(
        activity,
        metric_column,
        MetricType.from_int(activity_metric_dict[METRIC_TYPE_ATTRIBUTE]),
        activity_metric_dict[EXPRESSION_ATTRIBUTE],
    )


def metric_configuration_to_dict(metric_configuration: MetricConfiguration) -> dict:
    """Serializes a metric configuration to dict.

    :param metric_configuration: Metric configuration to tbe serialized.
    :type metric_configuration: MetricConfiguration

    :returns: A dictionary representing a metric configuration.
    :rtype: dict
    """
    metric_config_dict = {}

    metric_column_dicts = [
        metric_column_to_dict(mc) for mc in metric_configuration.metric_columns
    ]
    metric_config_dict[METRIC_COLUMNS_PROPERTY] = metric_column_dicts

    activity_column_metrics = []
    for activity_columns in metric_configuration.activity_metrics:
        column_metrics = []
        for activity_column_metric in activity_columns:
            column_metrics.append(activity_metric_to_dict(activity_column_metric))
        activity_column_metrics.append(column_metrics)

    metric_config_dict[ACTIVITY_METRICS_PROPERTY] = activity_column_metrics

    activity_identifiers = [
        str(activity.uuid) for activity in metric_configuration.activities
    ]
    metric_config_dict[MULTI_ACTIVITY_IDENTIFIER_PROPERTY] = activity_identifiers

    return metric_config_dict


def create_metric_configuration(
    metric_configuration_dict: dict, referenced_activities: typing.List[Activity]
) -> typing.Optional[MetricConfiguration]:
    """Creates a metric configuration from the equivalent dictionary representation.

    :param metric_configuration_dict: Dictionary containing information for deserializing
    a metric configuration object.
    :type metric_configuration_dict: dict

    :param referenced_activities: Activities which will be used to extract those
    referenced in the metric configuration.
    :type referenced_activities: typing.List[Activity]

    :returns: Metric configuration object or None if the deserialization failed.
    :rtype: MetricConfiguration
    """
    if len(metric_configuration_dict) == 0:
        return None

    metric_column_dicts = metric_configuration_dict[METRIC_COLUMNS_PROPERTY]
    metric_columns = [create_metric_column(mc_dict) for mc_dict in metric_column_dicts]

    indexed_metric_columns = {mc.name: mc for mc in metric_columns}
    indexed_activities = {
        str(activity.uuid): activity for activity in referenced_activities
    }

    activity_column_metrics = []
    activity_column_metric_dicts = metric_configuration_dict[ACTIVITY_METRICS_PROPERTY]
    for activity_row_dict in activity_column_metric_dicts:
        if len(activity_row_dict) == 0:
            continue

        # Check if the activity exists
        activity_id = activity_row_dict[0][ACTIVITY_IDENTIFIER_PROPERTY]
        if activity_id not in indexed_activities:
            # Most likely the activity in the metric config has been deleted
            continue

        activity_row_metrics = []
        for activity_metric_dict in activity_row_dict:
            name = activity_metric_dict[METRIC_IDENTIFIER_PROPERTY]
            activity = indexed_activities[activity_id]
            metric_column = indexed_metric_columns[name]

            activity_row_metrics.append(
                create_activity_metric(activity_metric_dict, activity, metric_column)
            )

        activity_column_metrics.append(activity_row_metrics)

    return MetricConfiguration(metric_columns, activity_column_metrics)


def metric_configuration_profile_to_dict(
    metric_config_profile: MetricConfigurationProfile,
) -> dict:
    """Serializes a metric configuration profile to a dictionary.

    :param metric_config_profile: Metric configuration profile to be
    serialized.
    :type metric_config_profile: MetricConfigurationProfile

    :returns: A dictionary representing a metric configuration profile.
    :rtype: dict
    """
    return {
        NAME_ATTRIBUTE: metric_config_profile.name,
        METRIC_CONFIGURATION_PROPERTY: metric_configuration_to_dict(
            metric_config_profile.config
        ),
    }


def create_metric_configuration_profile(
    metric_configuration_profile_dict: dict,
    referenced_activities: typing.List[Activity],
) -> typing.Optional[MetricConfigurationProfile]:
    """Creates a metric configuration profile from the equivalent
    dictionary representation.

    :param metric_configuration_profile_dict: Dictionary
    containing information for deserializing a metric
    configuration profile.
    :type metric_configuration_profile_dict: dict

    :param referenced_activities: Activities which will be used
    to extract those referenced in the metric configuration
    profile.
    :type referenced_activities: typing.List[Activity]

    :returns: Metric configuration profile
    object or None if the deserialization failed.
    :rtype: MetricConfiguration
    """
    if not metric_configuration_profile_dict:
        return None

    if NAME_ATTRIBUTE not in metric_configuration_profile_dict:
        return None

    if METRIC_CONFIGURATION_PROPERTY not in metric_configuration_profile_dict:
        return None

    name = metric_configuration_profile_dict[NAME_ATTRIBUTE]
    config = create_metric_configuration(
        metric_configuration_profile_dict[METRIC_CONFIGURATION_PROPERTY],
        referenced_activities,
    )

    if config is None:
        return None

    return MetricConfigurationProfile(name, config)


def clone_metric_configuration_profile(
    metric_config_profile: MetricConfigurationProfile,
    referenced_activities: typing.List[Activity],
) -> typing.Optional[MetricConfigurationProfile]:
    """Creates a deep copy version of the specified
    metric configuration profile.

    :param metric_config_profile: Metric configuration profile to be cloned.
    :type metric_config_profile: MetricConfigurationProfile

    :param referenced_activities: Activities which will be used
    to extract those referenced in the metric configuration
    profile.
    :type referenced_activities: typing.List[Activity]

    :returns: Cloned metric configuration profile or None if the
    input metric configuration profile was invalid.
    :rtype: MetricConfigurationProfile
    """
    if not metric_config_profile.is_valid():
        return None

    metric_profile_config_dict = metric_configuration_profile_to_dict(
        metric_config_profile
    )
    if not metric_profile_config_dict:
        return None

    return create_metric_configuration_profile(
        metric_profile_config_dict, referenced_activities
    )


def metric_profile_collection_to_dict(
    metric_profile_collection: MetricProfileCollection,
) -> dict:
    """Serializes a metric configuration profile to a dictionary.

    :param metric_profile_collection: Metric profile collection to be
    serialized.
    :type metric_profile_collection: MetricProfileCollection

    :returns: A dictionary representing a metric profile collection.
    :rtype: dict
    """
    return {
        CURRENT_PROFILE_PROPERTY: metric_profile_collection.current_profile,
        PROFILES_ATTRIBUTE: [
            metric_configuration_profile_to_dict(mp)
            for mp in metric_profile_collection.profiles
        ],
    }


def create_metrics_profile_collection(
    metric_profile_collection_dict, referenced_activities: typing.List[Activity]
) -> typing.Optional[MetricProfileCollection]:
    """Deserializes a metric profile collection from the equivalent
    dictionary representation.

    :param metric_profile_collection_dict: Dictionary containing
    information about the profile collection.
    :type metric_profile_collection_dict: dict

    :param referenced_activities: Activities which will be used
    to extract those referenced in the metric configuration
    objects that correspond to the respective profiles.
    :type referenced_activities: typing.List[Activity]

    :returns: Metric profile configuration object or None if
    the deserialization failed.
    :rtype: MetricProfileCollection
    """
    if not metric_profile_collection_dict:
        return None

    if PROFILES_ATTRIBUTE not in metric_profile_collection_dict:
        return None

    current_profile_id = metric_profile_collection_dict.get(
        CURRENT_PROFILE_PROPERTY, ""
    )
    metric_profiles = []
    for profile_dict in metric_profile_collection_dict[PROFILES_ATTRIBUTE]:
        profile = create_metric_configuration_profile(
            profile_dict, referenced_activities
        )
        if profile is None:
            continue
        metric_profiles.append(profile)

    return MetricProfileCollection(current_profile_id, metric_profiles)


def result_info_to_dict(result_info: ResultInfo) -> dict:
    """Serializes a ResultInfo object to a dictionary.

    The result collection should contain simple types that can be
    decoded to string by the `json` library.

    :param result_info: Result info object to serialize.
    :type result_info: ResultInfo

    :returns: A dictionary representation of the ResultInfo object.
    :rtype: dict
    """
    return {
        RESULT_COLLECTION_ATTRIBUTE: result_info.result_collection,
        LAST_UPDATED_DATE_ATTRIBUTE: result_info.updated_date,
    }


def create_result_info(result_info_dict: dict) -> typing.Optional[ResultInfo]:
    """Creates a ResultInfo object from the dictionary representation.

    :param result_info_dict: Representation of ResultInfo object.
    :type result_info_dict: dict

    :returns: A representation of the result info or None if
    there is missing information in the dictionary.
    :rtype: ResultInfo
    """
    args = []
    if RESULT_COLLECTION_ATTRIBUTE in result_info_dict:
        args.append(result_info_dict.get(RESULT_COLLECTION_ATTRIBUTE))

    if LAST_UPDATED_DATE_ATTRIBUTE in result_info_dict:
        args.append(result_info_dict.get(LAST_UPDATED_DATE_ATTRIBUTE))

    if len(args) < 2:
        return None

    return ResultInfo(*args)


def constant_raster_collection_to_dict(
    collection: "ConstantRasterCollection",
) -> dict:
    """Serializes a ConstantRasterCollection object into a dictionary.

    :param collection: Constant raster collection object
    :type collection: ConstantRasterCollection

    :returns: Dictionary representation of the collection
    :rtype: dict
    """
    if collection is None:
        return {}

    return {
        MIN_VALUE_ATTRIBUTE_KEY: collection.min_value,
        MAX_VALUE_ATTRIBUTE_KEY: collection.max_value,
        COMPONENT_TYPE_ATTRIBUTE: (
            collection.component_type.value if collection.component_type else None
        ),
        ALLOWABLE_MIN_ATTRIBUTE: collection.allowable_min,
        ALLOWABLE_MAX_ATTRIBUTE: collection.allowable_max,
        SKIP_RASTER_ATTRIBUTE: collection.skip_raster,
        LAST_UPDATED_ATTRIBUTE: collection.last_updated,
        COMPONENTS_ATTRIBUTE: [
            constant_raster_component_to_dict(c) for c in collection.components
        ],
    }


def constant_raster_collection_from_dict(
    collection_dict: dict, model_components: typing.List[LayerModelComponent]
) -> typing.Optional["ConstantRasterCollection"]:
    """Creates a ConstantRasterCollection object from a dictionary.

    :param collection_dict: Dictionary containing the collection data
    :type collection_dict: dict

    :param model_components: List of LayerModelComponent objects (NcsPathway or Activity)
    :type model_components: typing.List[LayerModelComponent]

    :returns: Constant raster collection object or None if deserialization failed
    :rtype: ConstantRasterCollection
    """
    if not collection_dict:
        return None

    # Create a lookup function for component access
    component_lookup_dict = {str(comp.uuid): comp for comp in model_components}

    def component_lookup(uuid_str: str) -> typing.Optional[LayerModelComponent]:
        return component_lookup_dict.get(uuid_str)

    # Deserialize components using helper function
    components = [
        create_constant_raster_component(comp_dict, component_lookup)
        for comp_dict in collection_dict.get(COMPONENTS_ATTRIBUTE, [])
    ]

    # Parse component_type if present
    component_type = None
    component_type_str = collection_dict.get(COMPONENT_TYPE_ATTRIBUTE)
    if component_type_str:
        component_type = ModelComponentType.from_string(component_type_str)

    return ConstantRasterCollection(
        min_value=collection_dict.get(MIN_VALUE_ATTRIBUTE_KEY, 0.0),
        max_value=collection_dict.get(MAX_VALUE_ATTRIBUTE_KEY, 1.0),
        component_type=component_type,
        components=components,
        skip_raster=collection_dict.get(SKIP_RASTER_ATTRIBUTE, False),
        allowable_max=collection_dict.get(ALLOWABLE_MAX_ATTRIBUTE, sys.float_info.max),
        allowable_min=collection_dict.get(ALLOWABLE_MIN_ATTRIBUTE, 0.0),
        last_updated=collection_dict.get(LAST_UPDATED_ATTRIBUTE, ""),
    )


def constant_raster_info_to_dict(constant_raster_info: ConstantRasterInfo) -> dict:
    """Creates a dictionary containing attribute name-value pairs
    from a ConstantRasterInfo object.

    :param constant_raster_info: ConstantRasterInfo instance to serialize
    :type constant_raster_info: ConstantRasterInfo

    :returns: Dictionary with normalized and absolute values
    :rtype: dict
    """
    return {
        NORMALIZED_ATTRIBUTE: constant_raster_info.normalized,
        ABSOLUTE_ATTRIBUTE: constant_raster_info.absolute,
    }


def create_constant_raster_info(source_dict: dict) -> ConstantRasterInfo:
    """Factory method for creating a ConstantRasterInfo object from dictionary.

    :param source_dict: Dictionary containing property values
    :type source_dict: dict

    :returns: ConstantRasterInfo instance with values from dictionary
    :rtype: ConstantRasterInfo
    """
    return ConstantRasterInfo(
        normalized=float(source_dict.get(NORMALIZED_ATTRIBUTE, 0.0)),
        absolute=float(source_dict.get(ABSOLUTE_ATTRIBUTE, 0.0)),
    )


def constant_raster_component_to_dict(
    constant_raster_component: ConstantRasterComponent,
) -> dict:
    """Creates a dictionary containing attribute name-value pairs
    from a ConstantRasterComponent object.

    :param constant_raster_component: ConstantRasterComponent instance to serialize
    :type constant_raster_component: ConstantRasterComponent

    :returns: Dictionary representation of the component
    :rtype: dict
    """
    return {
        VALUE_INFO_ATTRIBUTE: constant_raster_info_to_dict(
            constant_raster_component.value_info
        )
        if constant_raster_component.value_info
        else {},
        COMPONENT_UUID_ATTRIBUTE: str(constant_raster_component.component.uuid)
        if constant_raster_component.component
        else "",
        PREFIX_ATTRIBUTE: constant_raster_component.prefix,
        BASE_NAME_ATTRIBUTE: constant_raster_component.base_name,
        SUFFIX_ATTRIBUTE: constant_raster_component.suffix,
        PATH_ATTRIBUTE: constant_raster_component.path,
        SKIP_RASTER_ATTRIBUTE: constant_raster_component.skip_raster,
        ENABLED_ATTRIBUTE: constant_raster_component.enabled,
        COMPONENT_ID_ATTRIBUTE: constant_raster_component.component_id,
        COMPONENT_TYPE_ATTRIBUTE: (
            constant_raster_component.component_type.value
            if constant_raster_component.component_type
            else ModelComponentType.UNKNOWN.value
        ),
    }


def create_constant_raster_component(
    source_dict: dict,
    component_lookup: typing.Callable[[str], LayerModelComponent] = None,
) -> ConstantRasterComponent:
    """Factory method for creating a ConstantRasterComponent from dictionary.

    :param source_dict: Dictionary containing property values
    :type source_dict: dict

    :param component_lookup: Function to retrieve LayerModelComponent by UUID
    :type component_lookup: Callable

    :returns: ConstantRasterComponent instance with values from dictionary
    :rtype: ConstantRasterComponent
    """
    component = None
    component_uuid = source_dict.get(COMPONENT_UUID_ATTRIBUTE)
    if component_uuid and component_lookup:
        component = component_lookup(component_uuid)

    value_info_data = source_dict.get(VALUE_INFO_ATTRIBUTE, {})
    value_info = (
        create_constant_raster_info(value_info_data)
        if value_info_data
        else ConstantRasterInfo()
    )

    return ConstantRasterComponent(
        value_info=value_info,
        component=component,
        prefix=source_dict.get(PREFIX_ATTRIBUTE, ""),
        base_name=source_dict.get(BASE_NAME_ATTRIBUTE, ""),
        suffix=source_dict.get(SUFFIX_ATTRIBUTE, ""),
        path=source_dict.get(PATH_ATTRIBUTE, ""),
        skip_raster=bool(source_dict.get(SKIP_RASTER_ATTRIBUTE, False)),
        enabled=bool(source_dict.get(ENABLED_ATTRIBUTE, True)),
    )


def constant_raster_metadata_to_dict(
    metadata: ConstantRasterMetadata, collection_serializer: typing.Callable = None
) -> dict:
    """Creates a dictionary containing attribute name-value pairs
    from a ConstantRasterMetadata object.

    :param metadata: ConstantRasterMetadata instance to serialize
    :type metadata: ConstantRasterMetadata

    :param collection_serializer: Callable for serializing. If not specified,
    an empty dictionary will be used.
    :type collection_serializer: typing.Callable

    :returns: Dictionary representation of the metadata
    :rtype: dict
    """

    collection_dict = (
        collection_serializer(metadata.raster_collection)
        if collection_serializer
        else {}
    )

    return {
        ID_ATTRIBUTE: metadata.id,
        DISPLAY_NAME_ATTRIBUTE: metadata.display_name,
        RASTER_COLLECTION_ATTRIBUTE: collection_dict,
        COMPONENT_TYPE_ATTRIBUTE: (
            metadata.component_type.value if metadata.component_type else None
        ),
        INPUT_RANGE_ATTRIBUTE: list(metadata.input_range),
        USER_DEFINED_ATTRIBUTE: metadata.user_defined,
    }


def constant_raster_metadata_from_dict(
    metadata_dict,
    collection_deserializer: typing.Callable = None,
    activities: typing.List[Activity] = None,
) -> typing.Optional[ConstantRasterMetadata]:
    """Creates a constant raster metadata object from the dictionary
    representation.

    :param metadata_dict: Dictionary representation of the metadata object.
    :type metadata_dict: dict

    :param collection_deserializer: Callable for deserializing. If not specified,
    the raster collection will be None.
    :type collection_deserializer: typing.Callable

    :param activities: List of activities to lookup and link to constant raster component.
    :type activities: typing.List[Activity]

    :returns: Constant raster metadata object or None if the dictionary is empty.
    :rtype: ConstantRasterMetadata
    """
    if not metadata_dict:
        return None

    kwargs = {}

    if ID_ATTRIBUTE in metadata_dict:
        kwargs[ID_ATTRIBUTE] = metadata_dict[ID_ATTRIBUTE]

    if DISPLAY_NAME_ATTRIBUTE in metadata_dict:
        kwargs[DISPLAY_NAME_ATTRIBUTE] = metadata_dict[DISPLAY_NAME_ATTRIBUTE]

    if USER_DEFINED_ATTRIBUTE in metadata_dict:
        kwargs[USER_DEFINED_ATTRIBUTE] = metadata_dict[USER_DEFINED_ATTRIBUTE]

    if COMPONENT_TYPE_ATTRIBUTE in metadata_dict:
        kwargs[COMPONENT_TYPE_ATTRIBUTE] = ModelComponentType.from_string(
            metadata_dict[COMPONENT_TYPE_ATTRIBUTE]
        )

    if INPUT_RANGE_ATTRIBUTE in metadata_dict:
        input_range = metadata_dict[INPUT_RANGE_ATTRIBUTE]
        kwargs[INPUT_RANGE_ATTRIBUTE] = InputRange(input_range[0], input_range[1])

    raster_collection = None
    if RASTER_COLLECTION_ATTRIBUTE in metadata_dict and collection_deserializer:
        raster_collection = collection_deserializer(
            metadata_dict[RASTER_COLLECTION_ATTRIBUTE], activities
        )
    kwargs[RASTER_COLLECTION_ATTRIBUTE] = raster_collection

    return ConstantRasterMetadata(**kwargs)


def activity_npv_to_dict(activity_npv: ActivityNpv) -> dict:
    """Converts an ActivityNpv object to a dictionary representation.

    :returns: A dictionary containing attribute name-value pairs.
    :rtype: dict
    """
    # NPV parameters
    npv_params_dict = constant_raster_info_to_dict(activity_npv.value_info)
    npv_params_dict[YEARS_ATTRIBUTE] = activity_npv.params.years
    npv_params_dict[DISCOUNT_ATTRIBUTE] = activity_npv.params.discount
    npv_params_dict[YEARLY_RATES_ATTRIBUTE] = activity_npv.params.yearly_rates
    npv_params_dict[MANUAL_NPV_ATTRIBUTE] = activity_npv.params.manual_npv

    # Activity NPV
    raster_component_dict = constant_raster_component_to_dict(activity_npv)

    # Replace value info
    raster_component_dict[VALUE_INFO_ATTRIBUTE] = npv_params_dict

    return raster_component_dict


def create_activity_npv(activity_npv_dict: dict) -> typing.Optional[ActivityNpv]:
    """Creates an ActivityNpv object from the equivalent dictionary
    representation.

    Please note that the `activity` attribute will be
    `None` hence, will have to be set manually by extracting the
    corresponding `Activity` from the activity UUID.

    :param activity_npv_dict: Dictionary containing information for deserializing
    the ActivityNpv object.
    :type activity_npv_dict: dict

    :returns: ActivityNpv deserialized from the dictionary representation.
    :rtype: ActivityNpv
    """
    kwargs = {}
    npv_params = None
    if VALUE_INFO_ATTRIBUTE in activity_npv_dict:
        npv_params_dict = activity_npv_dict[VALUE_INFO_ATTRIBUTE]
        if YEARS_ATTRIBUTE in npv_params_dict:
            kwargs[YEARS_ATTRIBUTE] = npv_params_dict[YEARS_ATTRIBUTE]

        if DISCOUNT_ATTRIBUTE in npv_params_dict:
            kwargs[DISCOUNT_ATTRIBUTE] = npv_params_dict[DISCOUNT_ATTRIBUTE]

        if ABSOLUTE_NPV_ATTRIBUTE in npv_params_dict:
            kwargs[ABSOLUTE_NPV_ATTRIBUTE] = npv_params_dict[ABSOLUTE_NPV_ATTRIBUTE]

        if NORMALIZED_NPV_ATTRIBUTE in npv_params_dict:
            kwargs[NORMALIZED_NPV_ATTRIBUTE] = npv_params_dict[NORMALIZED_NPV_ATTRIBUTE]

        if MANUAL_NPV_ATTRIBUTE in npv_params_dict:
            kwargs[MANUAL_NPV_ATTRIBUTE] = npv_params_dict[MANUAL_NPV_ATTRIBUTE]

        if YEARLY_RATES_ATTRIBUTE in npv_params_dict:
            kwargs[YEARLY_RATES_ATTRIBUTE] = npv_params_dict[YEARLY_RATES_ATTRIBUTE]

        npv_params = NpvParameters(**kwargs)

    constant_raster_component = create_constant_raster_component(activity_npv_dict)
    npv_kwargs = asdict(constant_raster_component)
    npv_kwargs[VALUE_INFO_ATTRIBUTE] = npv_params

    return ActivityNpv(**npv_kwargs)


def activity_npv_collection_to_dict(
    activity_collection: ActivityNpvCollection,
) -> dict:
    """Converts the activity NPV collection object to the
    dictionary representation.

    :param activity_collection: Activity collection to serialize to a
    dictionary.
    :type activity_collection: ActivityNpvCollection

    :returns: A dictionary containing the attribute name-value pairs
    of an activity NPV collection object
    :rtype: dict
    """
    if activity_collection is None:
        return {}

    activity_collection_dict = constant_raster_collection_to_dict(activity_collection)
    mapping_dict = list(map(activity_npv_to_dict, activity_collection.mappings))
    activity_collection_dict[COMPONENTS_ATTRIBUTE] = mapping_dict

    return activity_collection_dict


def create_activity_npv_collection(
    activity_collection_dict: dict, reference_activities: typing.List[Activity] = None
) -> typing.Optional[ActivityNpvCollection]:
    """Creates an activity NPV collection object from the corresponding
    dictionary representation.

    :param activity_collection_dict: Dictionary representation containing
    information of an activity NPV collection object.
    :type activity_collection_dict: dict

    :param reference_activities: Optional list of activities that will be
    used to lookup  when deserializing the ActivityNpv objects.
    :type reference_activities: list

    :returns: Activity NPV collection object from the dictionary
    representation or None if the source dictionary is invalid.
    :rtype: ActivityNpvCollection
    """
    if not activity_collection_dict:
        return None

    ref_activities_by_uuid = {
        str(activity.uuid): activity for activity in reference_activities
    }

    raster_collection = constant_raster_collection_from_dict(
        activity_collection_dict, reference_activities
    )
    kwargs = asdict(raster_collection)

    if COMPONENTS_ATTRIBUTE in activity_collection_dict:
        mappings_dict = activity_collection_dict[COMPONENTS_ATTRIBUTE]
        npv_mappings = []
        for md in mappings_dict:
            activity_npv = create_activity_npv(md)
            if activity_npv is None:
                continue

            # Get the corresponding activity from the unique
            # identifier
            if COMPONENT_ID_ATTRIBUTE in md:
                activity_id = md[COMPONENT_ID_ATTRIBUTE]
                if activity_id in ref_activities_by_uuid:
                    activity = ref_activities_by_uuid[activity_id]
                    activity_npv.activity = activity
                    npv_mappings.append(activity_npv)

        kwargs[COMPONENTS_ATTRIBUTE] = npv_mappings

    return ActivityNpvCollection(**kwargs)
