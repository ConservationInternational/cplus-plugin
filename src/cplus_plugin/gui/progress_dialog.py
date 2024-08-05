"""Analysis progress dialog file"""

import os
import typing

from qgis.PyQt import (
    uic,
    QtCore,
    QtWidgets,
)
from qgis.PyQt.QtWidgets import QMenu, QAction, QStyle, QProgressBar
from qgis.PyQt.QtGui import QIcon

from ..utils import open_documentation, tr, log
from ..definitions.defaults import (
    ICON_PDF,
    ICON_LAYOUT,
    ICON_REPORT,
    ICON_HELP,
    REPORT_DOCUMENTATION,
)
from ..lib.reports.manager import report_manager, ReportManager
from ..models.report import ReportResult

Ui_DlgProgress, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/analysis_progress_dialog.ui")
)

Ui_DlgOnlineProgress, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/online_analysis_progress_dialog.ui")
)


class ProgressDialog(QtWidgets.QDialog, Ui_DlgProgress):
    """Progress dialog class"""

    analysis_cancelled = QtCore.pyqtSignal()

    def __init__(
        self,
        message=None,
        minimum=0,
        maximum=100,
        main_widget=None,
        parent=None,
        scenario_id=None,
        scenario_name=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.scenario_id = scenario_id
        self.scenario_name = scenario_name

        self.main_widget = main_widget
        self.report_manager = report_manager

        self.analysis_task = None

        # Dialog window flags
        flags = QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowCloseButtonHint
        self.setWindowFlags(flags)

        # Dialog statuses
        self.analysis_running = True

        if message is None:
            self.change_status_message(tr("Starting processing"))
        else:
            self.change_status_message(message)

        if scenario_name:
            self.title.setText(
                f"{self.title.text()} for scenario <b>{self.scenario_name}</b>"
            )

        # Report status
        self.report_running = False

        # Progress bar
        self.progress_bar.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.progress_bar.setMinimum(minimum)
        self.progress_bar.setMaximum(maximum)

        # Report menu
        self.menu = QMenu("&View Report")
        self.btn_view_report.setMenu(self.menu)
        self.btn_view_report.setIcon(QIcon(ICON_REPORT))

        # Menu button to open report in Layout designer
        self.designer_action = QAction(
            QIcon(ICON_LAYOUT), "Layout designer", parent=self
        )
        self.designer_action.triggered.connect(self.view_report_layout_designer)
        self.designer_action.setEnabled(False)
        self.menu.addAction(self.designer_action)

        # Open a PDF version of the report
        self.pdf_action = QAction(QIcon(ICON_PDF), "Open PDF", parent=self)
        self.pdf_action.triggered.connect(self.view_report_pdf)
        self.pdf_action.setEnabled(False)
        self.menu.addAction(self.pdf_action)

        # Open a Help for report_templates
        action = QAction(QIcon(ICON_HELP), "Help", parent=self)
        action.triggered.connect(self.open_report_help)
        action.setEnabled(True)
        self.menu.addAction(action)

        # Connections
        self.btn_cancel.clicked.connect(self.cancel_clicked)

        self.analysis_finished_message = tr("Analysis has finished.")

    def run_dialog(self):
        """Runs/opens the dialog. Sets modal to modeless.
        This will allow the dialog to display and not interfere with other processes.

        """
        self.setModal(False)
        self.show()

    def get_processing_status(self) -> bool:
        """Returns the status of the processing.

        :returns: Status of processing.
        :rtype: bool
        """

        return self.analysis_running

    def get_progress_bar(self) -> QProgressBar:
        """Returns a reference to the Progress bar object.

        :returns: Progress bar
        :rtype: QProgressBar
        """

        return self.progress_bar

    def update_progress_bar(self, value) -> None:
        """Sets the value of the progress bar

        :param value: Value to be set on the progress bar
        :type value: float
        """
        if self.progress_bar:
            try:
                self.progress_bar.setValue(int(value))
            except RuntimeError:
                log(tr("Error setting value to a progress bar"), notify=False)

    def change_status_message(self, message=None) -> None:
        """Updates the status message

        :param message: Message to show on the status bar
        :type message: str
        """

        if message:
            self.lbl_status.setText(message)

    def set_report_complete(self):
        """Enable layout designer and PDF report buttons."""
        self.btn_view_report.setEnabled(True)
        self.designer_action.setEnabled(True)
        self.pdf_action.setEnabled(True)
        self.report_running = False

        self.processing_finished()

    def view_report_pdf(self) -> None:
        """Opens a PDF version of the report"""
        if not self.scenario_id:
            log("Scenario ID has not been set.")
            return

        result = self.report_manager.report_result(self.scenario_id)
        if result is None:
            log("Report result not found.")
        else:
            status = self.report_manager.view_pdf(result)
            if not status:
                log("Unable to open PDF report.")

    def view_report_layout_designer(self) -> None:
        """Opens the report in layout designer"""
        if not self.scenario_id:
            log("Scenario ID has not been set.")
            return

        result = self.report_manager.report_result(self.scenario_id)
        if result is None:
            log("Report result not found.")
        else:
            status = self.report_manager.open_layout_designer(result)
            if not status:
                log("Unable to open layout designer.")

    def open_report_help(self) -> None:
        """Opens the Report guide in a browser"""
        open_documentation(REPORT_DOCUMENTATION)

    def cancel_clicked(self) -> None:
        """User clicked cancel.

        Processing will be stopped, and the UI will be updated to accommodate
        the processing status.
        """
        self.analysis_cancelled.emit()

        self.cancel_reporting()

        if self.analysis_running:
            # If cancelled is clicked
            self.stop_processing()
            try:
                if self.analysis_task:
                    self.analysis_task.processing_cancelled = True
                    self.analysis_task.cancel()
            except RuntimeError as e:
                # The analysis task should have been removed after
                # scenario analyis is done, this is the only way to find
                # out if the analysis has been completed.
                pass
        else:
            # If close has been clicked. In this case processing were already stopped
            super().close()

    def cancel_reporting(self):
        """Cancel the report generation process."""
        if self.report_running:
            self.report_manager.remove_report_task(self.scenario_id)

    def reject(self) -> None:
        """Called when the dialog is closed"""
        self.analysis_cancelled.emit()

        if self.analysis_running:
            # Stops analysis if it is still running
            self.stop_processing()
            try:
                if self.analysis_task:
                    self.analysis_task.processing_cancelled = True
                    self.analysis_task.cancel()
            except RuntimeError as e:
                # The analysis task should have been removed after
                # scenario analyis is done, this is the only way to find
                # out if the analysis has been completed.
                pass
        self.cancel_reporting()

        super().reject()

    def stop_processing(self, hide=False) -> None:
        """The user cancelled the processing."""
        if hide:
            self.change_status_message(tr("Processing has been minimized by the user"))
        else:
            self.change_status_message(tr("Processing has been cancelled by the user"))

        # Stops the processing task
        if self.main_widget:
            self.main_widget.cancel_processing_task()

        self.processing_cancelled()

    def processing_cancelled(self) -> None:
        """Post-steps when processing were cancelled."""

        self.analysis_running = False

        # Change cancel button to the close button status
        self.btn_cancel.setText(tr("Close"))
        self.btn_view_report.setEnabled(False)

    def processing_finished(self) -> None:
        """Post-steps when processing succeeded."""

        self.analysis_running = False
        self.change_status_message(self.analysis_finished_message)

        # Change cancel button to the close button status
        self.btn_cancel.setText(tr("Close"))
        self.btn_view_report.setEnabled(True)
        icon = self.style().standardIcon(QStyle.SP_DialogCloseButton)
        self.btn_cancel.setIcon(icon)


class OnlineProgressDialog(Ui_DlgOnlineProgress, ProgressDialog):
    def __init__(
        self,
        message=None,
        minimum=0,
        maximum=100,
        main_widget=None,
        parent=None,
        scenario_id=None,
        scenario_name=None,
    ):
        super().__init__(
            message, minimum, maximum, main_widget, parent, scenario_id, scenario_name
        )
        # Connections
        self.btn_hide.clicked.connect(self.hide_clicked)

    def hide_clicked(self) -> None:
        """User clicked hide.

        QGIS processing will be stopped, but online processing will be continued.
        """

        self.analysis_task.hide_task = True
        self.analysis_cancelled.emit()
        self.main_widget.view_status_btn.setEnabled(True)
        self.main_widget.processing_type.setEnabled(False)
        self.main_widget.processing_type.setToolTip(
            "Cannot choose online processing due to user having active online processing"
        )

        self.cancel_reporting()

        if self.analysis_running:
            self.analysis_task.hide_task = True
            # If cancelled is clicked
            self.stop_processing(hide=True)
            try:
                if self.analysis_task:
                    self.analysis_task.processing_cancelled = True
                    self.analysis_task.cancel()
            except RuntimeError as e:
                # The analysis task should have been removed after
                # scenario analyis is done, this is the only way to find
                # out if the analysis has been completed.
                pass
        super().close()


class ReportProgressDialog(ProgressDialog):
    """Shows progress for standalone report generation operations."""

    def __init__(self, message, submit_result, parent=None):
        super().__init__(message=message, parent=parent)

        self.analysis_running = False
        self.report_running = True

        self._submit_result = submit_result
        self.setWindowTitle(tr("Report Progress"))
        self.title.setText(tr("Reporting progress"))

        self._task = None
        if submit_result.identifier:
            self._task = self.report_manager.task_by_id(int(submit_result.identifier))

        if self._task is not None:
            self._task.taskCompleted.connect(self.reporting_finished)
            self._task.taskTerminated.connect(self.reporting_error)

        if submit_result.feedback:
            submit_result.feedback.progressChanged.connect(self.update_progress_bar)

    def view_report_pdf(self):
        """Opens a PDF version of the report"""
        if self.report_result is None:
            log("Report result not found.")
            return

        status = self.report_manager.view_pdf(self.report_result)
        if not status:
            log("Unable to open PDF report.")

    def view_report_layout_designer(self):
        """Opens the report in layout designer"""
        if self.report_result is None:
            log("Report result not found.")
            return

        status = self.report_manager.open_layout_designer(self.report_result)
        if not status:
            log("Unable to open layout designer.")

    @property
    def report_result(self) -> typing.Optional[ReportResult]:
        """Gets the report result.

        :returns: The report result based on the submit
        status or None if the task is not found or the
        task is not complete or an error occurred.
        :rtype: ReportResult
        """
        if self._task is None:
            return None

        return self._task.result

    def cancel_reporting(self):
        """Cancel the report generation process."""
        status = self.report_manager.remove_task_by_result(self._submit_result)
        if not status:
            self.report_running = False

    def reporting_finished(self) -> None:
        """Executed when report generation has been successfully completed."""
        self.set_report_complete()

        self.change_status_message(tr("Report generation complete."))

        # Change cancel button to the close button status
        self.btn_cancel.setText(tr("Close"))
        self.btn_view_report.setEnabled(True)
        icon = self.style().standardIcon(QStyle.SP_DialogCloseButton)
        self.btn_cancel.setIcon(icon)

        self.report_running = False

    def reporting_error(self):
        """Executed when a report generation error has occurred."""
        self.change_status_message(
            tr("Error generating report, see logs for more info.")
        )

        # Change cancel button to the close button status
        self.btn_cancel.setText(tr("Close"))
        self.btn_view_report.setEnabled(False)

        self.report_running = False

    def cancel_clicked(self) -> None:
        """Slot raised when the cancel button is clicked.

        Will stop reporting process.
        """
        if self.report_running:
            self.cancel_reporting()

            # Change cancel button to the close button status
            self.btn_cancel.setText(tr("Close"))
            self.btn_view_report.setEnabled(False)

            self.change_status_message(tr("Report generation canceled."))
        else:
            # If close has been clicked.
            super().close()
