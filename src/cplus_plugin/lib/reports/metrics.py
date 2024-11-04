# -*- coding: utf-8 -*-
"""
Provides variables and functions for custom activity metrics.
"""

import inspect
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
        # coefficient = float(values[1])

        return 42

    def clone(self) -> "DummyFinancialComputation":
        """Gets a clone of this function.

        :returns: A clone of this function.
        :rtype: DummyFinancialComputation
        """
        return DummyFinancialComputation()


class TestExpressionFunction(QgsExpressionFunction):
    """Python expression function"""

    def __init__(
        self,
        name,
        group,
        helptext="",
        usesgeometry=False,
        referenced_columns=None,
        handlesnull=False,
        params_as_list=False,
    ):
        # Call the parent constructor
        QgsExpressionFunction.__init__(self, name, 0, group, helptext)
        if referenced_columns is None:
            referenced_columns = [QgsFeatureRequest.ALL_ATTRIBUTES]
        self.params_as_list = params_as_list
        self.usesgeometry = usesgeometry
        self.referenced_columns = referenced_columns
        self.handlesnull = handlesnull

    def usesGeometry(self, node):
        return self.usesgeometry

    def referencedColumns(self, node):
        return self.referenced_columns

    def handlesNull(self):
        return self.handlesnull

    def isContextual(self):
        return True

    def func(self, values, context, parent, node):
        feature = None
        if context:
            feature = context.feature()

        try:
            # Inspect the inner function signature to get the list of parameters
            parameters = inspect.signature(self.function).parameters
            kwvalues = {}

            # Handle special parameters
            # those will not be inserted in the arguments list
            # if they are present in the function signature
            if "context" in parameters:
                kwvalues["context"] = context
            if "feature" in parameters:
                kwvalues["feature"] = feature
            if "parent" in parameters:
                kwvalues["parent"] = parent

            # In this context, values is a list of the parameters passed to the expression.
            # If self.params_as_list is True, values is passed as is to the inner function.
            if self.params_as_list:
                return self.function(values, **kwvalues)
            # Otherwise (default), the parameters are expanded
            return self.function(*values, **kwvalues)

        except Exception as ex:
            tb = traceback.format_exception(None, ex, ex.__traceback__)
            formatted_traceback = "".join(tb)
            formatted_exception = f"{ex}:<pre>{formatted_traceback}</pre>"
            parent.setEvalErrorString(formatted_exception)
            return None


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
    # expression_scope.addFunction(FUNC_FINANCIAL_DUMMY, DummyFinancialComputation())

    return expression_scope


def register_metric_functions():
    """Register our custom functions with the expression engine."""
    # QgsExpression.registerFunction(DummyFinancialComputation())

    register = True
    name = FUNC_FINANCIAL_DUMMY
    if register and QgsExpression.isFunctionName(name):
        if not QgsExpression.unregisterFunction(name):
            msgtitle = QCoreApplication.translate("UserExpressions", "User expressions")
            msg = QCoreApplication.translate(
                "UserExpressions",
                "The user expression {0} already exists and could not be unregistered.",
            ).format(name)
            QgsMessageLog.logMessage(msg + "\n", msgtitle, Qgis.MessageLevel.Warning)

    group = "CPLUS"
    helptext = ""
    usesgeometry = False
    referenced_columns = [QgsFeatureRequest.ALL_ATTRIBUTES]
    handlesnull = False
    f = TestExpressionFunction(
        name, group, helptext, usesgeometry, referenced_columns, handlesnull, False
    )
    QgsExpression.registerFunction(f, True)

    functions = QgsExpression.Functions()
    idx = QgsExpression.functionIndex(name)
    func = functions[idx]
    log(f"Name: {func.name()}")
    log(f"Groups: {str(func.groups())}")
    # log(f"Help: {func.helpText()}")

    func_prev = functions[idx - 2]
    log(f"Name: {func_prev.name()}")
    log(f"Groups: {str(func_prev.groups())}")
    # log(f"Help: {func_prev.helpText()}")


def unregister_metric_functions():
    """Unregister the custom metric functions from the expression
    engine.
    """
    QgsExpression.unregisterFunction(FUNC_FINANCIAL_DUMMY)


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
