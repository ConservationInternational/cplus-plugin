# -*- coding: utf-8 -*-
"""
Provides variables and functions for custom activity metrics.
"""

import inspect
import string
import traceback
import typing

from qgis.PyQt.QtCore import QCoreApplication

from qgis.core import (
    Qgis,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionFunction,
    QgsExpressionContextScope,
    QgsExpressionContextUtils,
    QgsExpressionNodeFunction,
    QgsFeatureRequest,
    QgsMessageLog,
    QgsProject,
    QgsScopedExpressionFunction,
)

from ...definitions.defaults import BASE_PLUGIN_NAME
from ...models.report import ActivityContextInfo
from ...utils import FileUtils, function_help_to_html, log, open_documentation, tr

# Collection of metric expression functions
METRICS_LIBRARY = []

# Variables
VAR_ACTIVITY_AREA = "cplus_activity_area"
VAR_ACTIVITY_NAME = "cplus_activity_name"

# Function names
FUNC_ACTIVITY_NPV = "activity_npv"


class ActivityNpvFunction(QgsScopedExpressionFunction):
    """Calculates the financial NPV of an activity."""

    def __init__(self):
        help_html = function_help_to_html(
            FUNC_ACTIVITY_NPV,
            tr(
                "Calculates the financial NPV of the current "
                "activity. This takes the area of the current activity and "
                "multiplies it by the NPV calculated via the NPV "
                "PWL Manager. If the NPV is not defined then the "
                "function will return -1. "
            ),
            [],
            [(f"{FUNC_ACTIVITY_NPV}()", "125,000")],
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
        return 42

    def clone(self) -> "ActivityNpvFunction":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: ActivityNpvFunction
        """
        return ActivityNpvFunction()


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
            description=tr("The total area of the activity being evaluated."),
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

    # Add functions
    expression_scope.addFunction(
        FUNC_ACTIVITY_NPV, metric_function_by_name(FUNC_ACTIVITY_NPV)
    )

    return expression_scope


def register_metric_functions():
    """Register our custom functions with the expression engine."""
    # Activity NPV
    activity_npv_function = ActivityNpvFunction()
    METRICS_LIBRARY.append(activity_npv_function)

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

    return metric_expression_context


def evaluate_activity_metric(
    context: QgsExpressionContext, activity_info: ActivityContextInfo, expression: str
) -> typing.Union[float, str]:
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

    :param expression: Expression to be evaluated.
    :type expression: str

    :returns: The result of the activity's metric calculation.
    :rtype: typing.Union[float, str]
    """
    return -1
