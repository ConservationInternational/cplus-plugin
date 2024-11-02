# -*- coding: utf-8 -*-
"""
Provides variables and functions for custom activity metrics.
"""

import typing

from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionFunction,
    QgsExpressionContextScope,
    QgsExpressionContextUtils,
    QgsExpressionNodeFunction,
    QgsProject,
    QgsScopedExpressionFunction,
)

from ...definitions.defaults import BASE_PLUGIN_NAME
from ...utils import FileUtils, function_help_to_html, log, open_documentation, tr


VAR_ACTIVITY_AREA = "cplus_activity_area"
VAR_ACTIVITY_NAME = "cplus_activity_name"
FUNC_FINANCIAL_DUMMY = "dummy_financial_viability"


class DummyFinancialComputation(QgsScopedExpressionFunction):
    """Dummy function to set up the metrics framework. Will be removed."""

    def __init__(self):
        params = [
            QgsExpressionFunction.Parameter("area"),
            QgsExpressionFunction.Parameter("inflation_coefficient"),
        ]

        help_html = function_help_to_html(
            FUNC_FINANCIAL_DUMMY,
            tr("Calculates the sum of the two parameters value1 and value2."),
            [
                ("float", "Current inflation rate", False),
                ("float", "Base lending rate", True),
            ],
            [
                (f"{FUNC_FINANCIAL_DUMMY}(4.3, 11.2)", "56.7"),
                (f"{FUNC_FINANCIAL_DUMMY}(8.5, 27.9)", "34.1"),
            ],
        )
        super().__init__(
            FUNC_FINANCIAL_DUMMY, params, BASE_PLUGIN_NAME, helpText=help_html
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
        area = int(values[0])
        coefficient = float(values[1])

        return area * coefficient

    def clone(self) -> "DummyFinancialComputation":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: DummyFinancialComputation
        """
        return DummyFinancialComputation()


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
    expression_scope.addFunction(FUNC_FINANCIAL_DUMMY, DummyFinancialComputation())

    return expression_scope


def create_metrics_expression_context(
    project: QgsProject = None,
) -> QgsExpressionContext:
    """Gets the expression context to use in the initial set up (e.g.
    expression builder) or computation stage of activity metrics.

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

    builder_expression_context = QgsExpressionContext()

    builder_expression_context.appendScope(QgsExpressionContextUtils.globalScope())
    builder_expression_context.appendScope(
        QgsExpressionContextUtils.projectScope(project)
    )
    builder_expression_context.appendScope(create_metrics_expression_scope())

    return builder_expression_context
