# -*- coding: utf-8 -*-
"""
Registers custom report variables for layout design
and handles report generation.
"""
import typing
import uuid

from qgis.PyQt import QtCore

from qgis.core import QgsApplication, QgsPrintLayout, QgsTask

from ...models.base import Scenario, SpatialExtent
from ...models.report import ReportContext, ReportResult
from ...utils import FileUtils, tr

from .generator import ReportGeneratorTask
from .variables import LayoutVariableRegister


class ReportManager(QtCore.QObject):
    """Registers custom report variables for
    layout design and handles report generation.
    """

    generate_started = QtCore.pyqtSignal(str)
    generate_completed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._variable_register = LayoutVariableRegister()
        self.report_name = tr("Scenario Analysis Report")

        # Task id (value) indexed by scenario id (key)
        self._report_tasks = {}
        # Report results (value) indexed by scenario id (key)
        self._report_results = {}
        self.tm = QgsApplication.instance().taskManager()
        self.tm.statusChanged.connect(self.on_task_status_changed)

    @property
    def variable_register(self) -> LayoutVariableRegister:
        """Get the instance of the variable register used
        for the management of variables.

        :returns: The register for managing variables in
        report layout scope.
        :rtype: LayoutVariableRegister
        """
        return self._variable_register

    def register_variables(self, layout: QgsPrintLayout):
        """Registers custom variables and their corresponding
        initial values in the layout.

        :param layout: Layout object where the custom
        variables will be registered.
        :type layout: QgsPrintLayout
        """
        self._variable_register.register_variables(layout)

    def scenario_by_task_id(self, task_id: int) -> str:
        """Gets the scenario identifier for the report generation t
        ask with the given ID.

        :param task_id: ID of the task whose corresponding scenario
        is to be retrieved.
        :type task_id: int

        :returns: Scenario identifier whose report is being generated
        by a process with the given task id or an empty string if
        there was no match.
        :rtype: str
        """
        scenario_ids = [
            sid for sid, tid in self._report_tasks.items() if tid == task_id
        ]
        if len(scenario_ids) == 0:
            return ""

        return scenario_ids[0]

    def on_task_status_changed(self, task_id: int, status: QgsTask.TaskStatus):
        """Slot raised when the status of a task has changed.

        This function will emit when the report generation task has started
        or when it has completed successfully or terminated due to an error.

        :param task_id: ID of the task.
        :type task_id: int

        :param status: New task status.
        :type status: QgsTask.TaskStatus
        """
        scenario_id = self.scenario_by_task_id(task_id)

        # Not related to CPLUS report or task
        if not scenario_id:
            return

        if status == QgsTask.TaskStatus.Running:
            self.generate_started.emit(scenario_id)

        elif status == QgsTask.TaskStatus.Complete:
            # Get result
            task = self.tm.task(task_id)
            result = task.result
            if result is not None:
                self._report_results[scenario_id] = result

            # Remove task
            self.remove_scenario_task(scenario_id)

            self.generate_completed.emit(scenario_id)

    def remove_scenario_task(self, scenario_id: str) -> bool:
        """Remove report task associated with the given scenario.

        :param scenario_id: Identified of the scenario whose report
        generation process is to be removed.
        :type scenario_id: str

        :returns: True if the task has been successfully removed
        else False if there is no associated task for the given
        scenario.
        :rtype: bool
        """
        if scenario_id not in self._report_tasks:
            return False

        task_id = self._report_tasks[scenario_id]
        task = self.tm.task(task_id)
        if task is None:
            return False

        if (
            task.status() != QgsTask.TaskStatus.Complete
            or task.status() != QgsTask.TaskStatus.Terminated
        ):
            task.cancel()

        _ = self._report_tasks.pop(scenario_id)

        return True

    def generate(self) -> bool:
        """Initiates the report generation process using information
        resulting from the scenario analysis.

        :returns: True if the report generation process was successfully
        submitted else False if a running process is re-submitted.
        :rtype: bool
        """
        # TODO: Code below needs to be refactored based on how the
        #  results of the output are packaged.
        template_path = FileUtils.report_template_path()
        scenario = Scenario(
            uuid.uuid4(),
            "Test Scenario",
            "This is a temporary scenario object for testing report production.",
            SpatialExtent([-23.960197335, 32.069186664, -25.201606226, 30.743498637]),
        )

        ctx = ReportContext(template_path, scenario, self.report_name)

        scenario_id = str(ctx.scenario.uuid)
        if scenario_id in self._report_tasks:
            return False

        msg_tr = tr("Generating report for")
        description = f"{msg_tr} {ctx.scenario.name}"
        report_task = ReportGeneratorTask(description, ctx)
        task_id = self.tm.addTask(report_task)

        self._report_tasks[scenario_id] = task_id

        return True

    def report_result(self, scenario_id: str) -> typing.Union[ReportResult, None]:
        """Gets the report result for the scenario with the given ID.

        :param scenario_id: Identifier of the scenario whose report is to
        be retrieved.
        :type scenario_id: str

        :returns: Result of the report generation process. Caller needs to
        check if the process was successful or there was an error by checking
        the status of the `success` attribute. For scenarios that had not
        been submitted for report generation, a None object will be
        returned.
        :rtype: ReportResult
        """
        if scenario_id not in self._report_results:
            return None

        return self._report_results[scenario_id]

    def open_layout_designer(self, result: ReportResult) -> bool:
        """Opens the analysis report in the layout designer. The
        layout needs to exist in the currently loaded project.

        :param result: Result object from the report generation
        process.
        :type result: ReportResult

        :returns: True if the layout was successfully loaded, else
        False if the result from the generation process was False
        or if the layout does not exist in the current project.
        :rtype: bool
        """
        pass

    def view_pdf(self, result: ReportResult) -> bool:
        """Opens the analysis in the host's default PDF viewer.

        :param result: Result object from the report generation
        process.
        :type result: ReportResult

        :returns: True if the PDF was successfully loaded, else
        False if the result from the generation process was False.
        :rtype: bool
        """
        pass


report_manager = ReportManager()
