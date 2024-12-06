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
    QgsProject,
    QgsScopedExpressionFunction,
)

from ...definitions.defaults import BASE_PLUGIN_NAME
from ...models.report import ActivityContextInfo, MetricEvalResult
from ...utils import function_help_to_html, log, tr

# Collection of metric expression functions
METRICS_LIBRARY = []

# Variables
VAR_ACTIVITY_AREA = "cplus_activity_area"
VAR_ACTIVITY_NAME = "cplus_activity_name"
VAR_ACTIVITY_ID = "cplus_activity_id"


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

    return expression_scope


def register_metric_functions():
    """Register our custom functions with the expression engine."""
    # Add expression functions to be registered here

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
