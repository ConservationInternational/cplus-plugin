# -*- coding: utf-8 -*-
"""
Provides variables and functions for custom activity metrics.
"""

import typing

from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextGenerator,
    QgsExpressionContextScope,
    QgsExpressionContextUtils,
    QgsExpressionNodeFunction,
    QgsProject,
    QgsScopedExpressionFunction,
)

from ...conf import settings_manager
from ...definitions.defaults import (
    BASE_PLUGIN_NAME,
    MANAGE_CARBON_IMPACT_EXPRESSION_DESCRIPTION,
    MEAN_BASED_IRRECOVERABLE_CARBON_EXPRESSION_DESCRIPTION,
    NATUREBASE_CARBON_IMPACT_EXPRESSION_DESCRIPTION,
    NPV_EXPRESSION_DESCRIPTION,
    PWL_IMPACT_EXPRESSION_DESCRIPTION,
    PROTECT_CARBON_IMPACT_EXPRESSION_DESCRIPTION,
    RESTORE_CARBON_IMPACT_EXPRESSION_DESCRIPTION,
)
from ..carbon import (
    CarbonImpactProtectCalculator,
    CarbonImpactManageCalculator,
    CarbonImpactRestoreCalculator,
    IrrecoverableCarbonCalculator,
)
from ..financials import calculate_activity_npv
from ...models.report import ActivityContextInfo, MetricEvalResult
from ...utils import calculate_raster_area, function_help_to_html, log, tr

# Collection of metric expression functions
METRICS_LIBRARY = []

# Variables
VAR_ACTIVITY_AREA = "cplus_activity_area"
VAR_ACTIVITY_NAME = "cplus_activity_name"
VAR_ACTIVITY_ID = "cplus_activity_id"
VAR_ACTIVITY_NATUREBASE_CARBON_IMPACT = "cplus_activity_naturebase_carbon_impact"

# Function names
FUNC_MEAN_BASED_IC = "irrecoverable_carbon_by_mean"
FUNC_ACTIVITY_NPV = "activity_npv"
FUNC_PWL_IMPACT = "pwl_impact"
FUNC_CARBON_IMPACT_PROTECT = "carbon_impact_protect"
FUNC_CARBON_IMPACT_MANAGE = "carbon_impact_manage"
FUNC_CARBON_IMPACT_RESTORE = "carbon_impact_restore"


class ActivityIrrecoverableCarbonFunction(QgsScopedExpressionFunction):
    """Calculates the total irrecoverable carbon of an activity using the
    means-based reference carbon layer."""

    def __init__(self):
        help_html = function_help_to_html(
            FUNC_MEAN_BASED_IC,
            tr(MEAN_BASED_IRRECOVERABLE_CARBON_EXPRESSION_DESCRIPTION),
            examples=[(f"{FUNC_MEAN_BASED_IC}()", "42,500")],
        )
        super().__init__(
            FUNC_MEAN_BASED_IC, 0, BASE_PLUGIN_NAME, help_html, isContextual=True
        )

    def func(
        self,
        values: typing.List[typing.Any],
        context: QgsExpressionContext,
        parent: QgsExpression,
        node: QgsExpressionNodeFunction,
    ) -> typing.Any:
        """Returns the result of evaluating the function.

        :param values: List of values passed to the function
        :type values: typing.Iterable[typing.Any]

        :param context: Context expression is being evaluated against
        :type context: QgsExpressionContext

        :param parent: Parent expression
        :type parent: QgsExpression

        :param node: Expression node
        :type node: QgsExpressionNodeFunction

        :returns: The result of the function.
        :rtype: typing.Any
        """
        if not context.hasVariable(VAR_ACTIVITY_ID):
            return -1.0

        activity_id = context.variable(VAR_ACTIVITY_ID)
        irrecoverable_carbon_calculator = IrrecoverableCarbonCalculator(activity_id)

        return irrecoverable_carbon_calculator.run()

    def clone(self) -> "ActivityIrrecoverableCarbonFunction":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: ActivityIrrecoverableCarbonFunction
        """
        return ActivityIrrecoverableCarbonFunction()


class ActivityNpvFunction(QgsScopedExpressionFunction):
    """Calculates the financial NPV of an activity by extracting the
    individual NPV values of the pathways in the activity.
    """

    def __init__(self):
        help_html = function_help_to_html(
            FUNC_ACTIVITY_NPV,
            tr(NPV_EXPRESSION_DESCRIPTION),
            examples=[(f"{FUNC_ACTIVITY_NPV}()", "125,800")],
        )
        super().__init__(
            FUNC_ACTIVITY_NPV, 0, BASE_PLUGIN_NAME, help_html, isContextual=True
        )

    def func(
        self,
        values: typing.List[typing.Any],
        context: QgsExpressionContext,
        parent: QgsExpression,
        node: QgsExpressionNodeFunction,
    ) -> typing.Any:
        """Returns the result of evaluating the function.

        :param values: List of values passed to the function
        :type values: typing.Iterable[typing.Any]

        :param context: Context expression is being evaluated against
        :type context: QgsExpressionContext

        :param parent: Parent expression
        :type parent: QgsExpression

        :param node: Expression node
        :type node: QgsExpressionNodeFunction

        :returns: The result of the function.
        :rtype: typing.Any
        """
        if not context.hasVariable(VAR_ACTIVITY_ID) or not context.hasVariable(
            VAR_ACTIVITY_AREA
        ):
            return -1.0

        activity_id = context.variable(VAR_ACTIVITY_ID)
        activity_area = context.variable(VAR_ACTIVITY_AREA)

        if not isinstance(activity_area, (float, int)):
            return -1.0

        return calculate_activity_npv(activity_id, activity_area)

    def clone(self) -> "ActivityNpvFunction":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: ActivityNpvFunction
        """
        return ActivityNpvFunction()


class ActivityPwlImpactFunction(QgsScopedExpressionFunction):
    """Calculates the PWL impact an activity."""

    def __init__(self):
        arg_name = "custom_impact"
        example_intro = (
            f"For an activity with an area of 20,000 ha, "
            f"{FUNC_PWL_IMPACT}(1.5) will return"
        )
        help_html = function_help_to_html(
            FUNC_PWL_IMPACT,
            tr(PWL_IMPACT_EXPRESSION_DESCRIPTION),
            [
                (
                    arg_name,
                    tr(
                        "An integer or float representing the "
                        "number of jobs created per hectare."
                    ),
                    False,
                )
            ],
            [(tr(example_intro), "30,000")],
        )
        super().__init__(
            FUNC_PWL_IMPACT, 1, BASE_PLUGIN_NAME, help_html, isContextual=True
        )

    def func(
        self,
        values: typing.List[typing.Any],
        context: QgsExpressionContext,
        parent: QgsExpression,
        node: QgsExpressionNodeFunction,
    ) -> typing.Any:
        """Returns the result of evaluating the function.

        :param values: List of values passed to the function
        :type values: typing.Iterable[typing.Any]

        :param context: Context expression is being evaluated against
        :type context: QgsExpressionContext

        :param parent: Parent expression
        :type parent: QgsExpression

        :param node: Expression node
        :type node: QgsExpressionNodeFunction

        :returns: The result of the function.
        :rtype: typing.Any
        """
        if len(values) == 0:
            return -1.0

        if not context.hasVariable(VAR_ACTIVITY_ID) or not context.hasVariable(
            VAR_ACTIVITY_AREA
        ):
            return -1.0

        activity_id = context.variable(VAR_ACTIVITY_ID)
        num_jobs = values[0]

        if not isinstance(num_jobs, (float, int)):
            return -1.0

        return calculate_activity_pwl_impact(activity_id, num_jobs)

    def clone(self) -> "ActivityPwlImpactFunction":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: ActivityPwlImpactFunction
        """
        return ActivityPwlImpactFunction()


class ActivityProtectCarbonImpactFunction(QgsScopedExpressionFunction):
    """Calculates the carbon impact of protect NCS pathways
    in an activity using the reference biomass layer.
    """

    def __init__(self):
        help_html = function_help_to_html(
            FUNC_CARBON_IMPACT_PROTECT,
            tr(PROTECT_CARBON_IMPACT_EXPRESSION_DESCRIPTION),
            examples=[(f"{FUNC_CARBON_IMPACT_PROTECT}()", "12,800")],
        )
        super().__init__(
            FUNC_CARBON_IMPACT_PROTECT,
            0,
            BASE_PLUGIN_NAME,
            help_html,
            isContextual=True,
        )

    def func(
        self,
        values: typing.List[typing.Any],
        context: QgsExpressionContext,
        parent: QgsExpression,
        node: QgsExpressionNodeFunction,
    ) -> typing.Any:
        """Returns the result of evaluating the function.

        :param values: List of values passed to the function
        :type values: typing.Iterable[typing.Any]

        :param context: Context expression is being evaluated against
        :type context: QgsExpressionContext

        :param parent: Parent expression
        :type parent: QgsExpression

        :param node: Expression node
        :type node: QgsExpressionNodeFunction

        :returns: The result of the function.
        :rtype: typing.Any
        """
        if not context.hasVariable(VAR_ACTIVITY_ID):
            return -1.0

        activity_id = context.variable(VAR_ACTIVITY_ID)
        protect_carbon_calculator = CarbonImpactProtectCalculator(activity_id)

        return protect_carbon_calculator.run()

    def clone(self) -> "ActivityProtectCarbonImpactFunction":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: ActivityProtectCarbonImpactFunction
        """
        return ActivityProtectCarbonImpactFunction()


class ActivityManageCarbonImpactFunction(QgsScopedExpressionFunction):
    """Calculates the carbon impact of manage NCS pathways in an activity."""

    def __init__(self):
        help_html = function_help_to_html(
            FUNC_CARBON_IMPACT_MANAGE,
            tr(MANAGE_CARBON_IMPACT_EXPRESSION_DESCRIPTION),
            examples=[(f"{FUNC_CARBON_IMPACT_MANAGE}()", "4,500")],
        )
        super().__init__(
            FUNC_CARBON_IMPACT_MANAGE, 0, BASE_PLUGIN_NAME, help_html, isContextual=True
        )

    def func(
        self,
        values: typing.List[typing.Any],
        context: QgsExpressionContext,
        parent: QgsExpression,
        node: QgsExpressionNodeFunction,
    ) -> typing.Any:
        """Returns the result of evaluating the function.

        :param values: List of values passed to the function
        :type values: typing.Iterable[typing.Any]

        :param context: Context expression is being evaluated against
        :type context: QgsExpressionContext

        :param parent: Parent expression
        :type parent: QgsExpression

        :param node: Expression node
        :type node: QgsExpressionNodeFunction

        :returns: The result of the function.
        :rtype: typing.Any
        """
        if not context.hasVariable(VAR_ACTIVITY_ID):
            return -1.0

        activity_id = context.variable(VAR_ACTIVITY_ID)
        manage_carbon_calculator = CarbonImpactManageCalculator(activity_id)

        return manage_carbon_calculator.run()

    def clone(self) -> "ActivityManageCarbonImpactFunction":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: ActivityManageCarbonImpactFunction
        """
        return ActivityManageCarbonImpactFunction()


class ActivityRestoreCarbonImpactFunction(QgsScopedExpressionFunction):
    """Calculates the carbon impact of restore NCS pathways in an activity."""

    def __init__(self):
        help_html = function_help_to_html(
            FUNC_CARBON_IMPACT_RESTORE,
            tr(RESTORE_CARBON_IMPACT_EXPRESSION_DESCRIPTION),
            examples=[(f"{FUNC_CARBON_IMPACT_RESTORE}()", "4,500")],
        )
        super().__init__(
            FUNC_CARBON_IMPACT_RESTORE,
            0,
            BASE_PLUGIN_NAME,
            help_html,
            isContextual=True,
        )

    def func(
        self,
        values: typing.List[typing.Any],
        context: QgsExpressionContext,
        parent: QgsExpression,
        node: QgsExpressionNodeFunction,
    ) -> typing.Any:
        """Returns the result of evaluating the function.

        :param values: List of values passed to the function
        :type values: typing.Iterable[typing.Any]

        :param context: Context expression is being evaluated against
        :type context: QgsExpressionContext

        :param parent: Parent expression
        :type parent: QgsExpression

        :param node: Expression node
        :type node: QgsExpressionNodeFunction

        :returns: The result of the function.
        :rtype: typing.Any
        """
        if not context.hasVariable(VAR_ACTIVITY_ID):
            return -1.0

        activity_id = context.variable(VAR_ACTIVITY_ID)
        restore_carbon_calculator = CarbonImpactRestoreCalculator(activity_id)

        return restore_carbon_calculator.run()

    def clone(self) -> "ActivityRestoreCarbonImpactFunction":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: ActivityRestoreCarbonImpactFunction
        """
        return ActivityRestoreCarbonImpactFunction()


def create_metrics_expression_scope() -> QgsExpressionContextScope:
    """Creates the expression context scope for activity metrics.

    The initial variable values will be arbitrary and will only be
    updated just prior to the evaluation of the expression in a
    separate function.

    :returns: The expression scope for activity metrics.
    :rtype: QgsExpressionContextScope
    """
    expression_scope = QgsExpressionContextScope(BASE_PLUGIN_NAME)

    # Activity area
    expression_scope.addVariable(
        QgsExpressionContextScope.StaticVariable(
            VAR_ACTIVITY_AREA,
            1,
            description=tr(
                "The total area, in hectares, of the activity being evaluated."
            ),
        )
    )

    # Activity name
    expression_scope.addVariable(
        QgsExpressionContextScope.StaticVariable(
            VAR_ACTIVITY_NAME,
            "",
            description=tr("The name of the activity being evaluated."),
        )
    )

    # Activity total naturebase data carbon impact
    expression_scope.addVariable(
        QgsExpressionContextScope.StaticVariable(
            VAR_ACTIVITY_NATUREBASE_CARBON_IMPACT,
            -1,
            description=tr(NATUREBASE_CARBON_IMPACT_EXPRESSION_DESCRIPTION),
        )
    )

    # Add functions
    expression_scope.addFunction(FUNC_PWL_IMPACT, ActivityPwlImpactFunction())
    expression_scope.addFunction(FUNC_ACTIVITY_NPV, ActivityNpvFunction())
    expression_scope.addFunction(
        FUNC_MEAN_BASED_IC, ActivityIrrecoverableCarbonFunction()
    )
    expression_scope.addFunction(
        FUNC_CARBON_IMPACT_PROTECT, ActivityProtectCarbonImpactFunction()
    )
    expression_scope.addFunction(
        FUNC_CARBON_IMPACT_MANAGE, ActivityManageCarbonImpactFunction()
    )
    expression_scope.addFunction(
        FUNC_CARBON_IMPACT_RESTORE, ActivityRestoreCarbonImpactFunction()
    )

    return expression_scope


def register_metric_functions():
    """Register our custom functions with the expression engine."""
    # Irrecoverable carbon
    mean_based_irrecoverable_carbon_function = ActivityIrrecoverableCarbonFunction()
    METRICS_LIBRARY.append(mean_based_irrecoverable_carbon_function)

    # Activity NPV
    activity_npv_function = ActivityNpvFunction()
    METRICS_LIBRARY.append(activity_npv_function)

    # PWL impact
    activity_pwl_impact_function = ActivityPwlImpactFunction()
    METRICS_LIBRARY.append(activity_pwl_impact_function)

    # Protect carbon impact
    protect_carbon_function = ActivityProtectCarbonImpactFunction()
    METRICS_LIBRARY.append(protect_carbon_function)

    # Manage carbon impact
    manage_carbon_function = ActivityManageCarbonImpactFunction()
    METRICS_LIBRARY.append(manage_carbon_function)

    # Restore carbon impact
    restore_carbon_function = ActivityRestoreCarbonImpactFunction()
    METRICS_LIBRARY.append(restore_carbon_function)

    for func in METRICS_LIBRARY:
        QgsExpression.registerFunction(func)


def unregister_metric_functions():
    """Unregister the custom metric functions from the expression
    engine.
    """
    func_names = [func.name() for func in METRICS_LIBRARY]

    for fn in func_names:
        QgsExpression.unregisterFunction(fn)


def metric_function_by_name(name: str) -> typing.Optional[QgsScopedExpressionFunction]:
    """Gets a metric function in the library based on the name.

    :returns: Corresponding function in the metrics library
    or None if not found.
    :rtype: QgsScopedExpressionFunction
    """
    matching_func = [func for func in METRICS_LIBRARY if func.name() == name]

    return matching_func[0] if len(matching_func) > 0 else None


def create_metrics_expression_context(
    project: QgsProject = None,
) -> QgsExpressionContext:
    """Gets the expression context to use in the initial set up (e.g.
    expression builder) as well as computation stage of activity metrics.

    It includes the global and project scopes.

    :param project: The QGIS project whose functions and variables
    will be included in the expression context. If not specified,
    the current project will be used.
    :type project: QgsProject

    :returns: The expression to use in the customization of activity
    metrics.
    :rtype: QgsExpressionContext
    """
    if project is None:
        project = QgsProject.instance()

    metric_expression_context = QgsExpressionContext()

    metric_expression_context.appendScope(QgsExpressionContextUtils.globalScope())
    metric_expression_context.appendScope(
        QgsExpressionContextUtils.projectScope(project)
    )
    metric_expression_context.appendScope(create_metrics_expression_scope())

    # Highlight some key variables
    metric_expression_context.setHighlightedVariables([VAR_ACTIVITY_AREA])

    return metric_expression_context


def evaluate_activity_metric(
    context: QgsExpressionContext,
    activity_info: ActivityContextInfo,
    expression_str: str,
) -> MetricEvalResult:
    """Calculates the metrics for an activity using the information
    in the expression context and for an activity in the info object.

    The context will first be updated with the latest activity information
    in the info object before the expression is evaluated.

    :param context: Expression context containing the global, project
    and metrics scopes respectively.
    :type context: QgsExpressionContext

    :param activity_info: Contains information about an activity whose
    attribute values will be used to evaluate the expression.
    :type activity_info: ActivityContextInfo

    :param expression_str: Expression to be evaluated.
    :type expression_str: str

    :returns: The result of the activity's metric calculation.
    :rtype: MetricEvalResult
    """
    # Update context with activity information
    metrics_scope = context.activeScopeForVariable(VAR_ACTIVITY_AREA)
    if metrics_scope is None:
        return MetricEvalResult(False, None)

    # Update context
    metrics_scope.setVariable(VAR_ACTIVITY_ID, str(activity_info.activity.uuid))
    metrics_scope.setVariable(VAR_ACTIVITY_NAME, activity_info.activity.name)
    metrics_scope.setVariable(VAR_ACTIVITY_AREA, activity_info.area)
    metrics_scope.setVariable(
        VAR_ACTIVITY_NATUREBASE_CARBON_IMPACT, activity_info.total_naturebase_carbon
    )

    expression = QgsExpression(expression_str)
    expression.prepare(context)
    result = expression.evaluate(context)

    if expression.hasEvalError() or expression.hasParserError():
        if expression.hasEvalError():
            exp_error = expression.evalErrorString()
        else:
            exp_error = expression.parserErrorString()

        log(f"Error evaluating activity metric: {exp_error}", info=False)

        return MetricEvalResult(False, None)

    return MetricEvalResult(True, result)


class MetricsExpressionContextGenerator(QgsExpressionContextGenerator):
    """Helper class that generates the metrics expression context for use in
    QGIS objects that expect an expression context generator.
    """

    def createExpressionContext(self) -> QgsExpressionContext:
        """Returns a metrics expression context.

        :returns: Metrics expression context with CPLUS-specific
        functions and variables.
        :rtype: QgsExpressionContext
        """
        return create_metrics_expression_context()


def calculate_activity_pwl_impact(activity_id: str, number_jobs: float) -> float:
    """Calculates the PWL impact an activity.

    It sums up the result of the number of jobs multiplied
    by the area of each NCS pathway that constitutes the
    activity.

    :param activity_id: The ID of the specific activity.
    :type activity_id: str

    :param number_jobs: Number of jobs for the activity.
    :type number_jobs: float

    :returns: Returns the total pwl impact of the activity, or -1.0
    if the activity does not exist or if found, lacks pathways
    or if the area of all pathways could not be computed.
    :rtype: float
    """
    activity = settings_manager.get_activity(activity_id)
    if activity is None or len(activity.pathways) == 0:
        return -1.0

    pathway_areas = []
    for pathway in activity.pathways:
        pathway_layer = pathway.to_map_layer()
        if pathway_layer is None:
            continue

        area = calculate_raster_area(pathway_layer, 1)
        if area == -1.0:
            log(
                f"Could not compute the area for {pathway.name} "
                f"pathway in PWL impact assessment for {activity.name} "
                f"activity.",
                info=False,
            )
            continue

        pathway_areas.append(area)

    if len(pathway_areas) == 0:
        return -1.0

    return float(sum(pathway_areas)) * number_jobs
