"""at the top"""

import os

from qgis.PyQt import (
    uic,
    QtCore,
    QtWidgets,
)
from qgis.PyQt.QtWidgets import QMenu, QAction, QStyle, QProgressBar
from qgis.PyQt.QtGui import QIcon

from qgis.core import (
    QgsApplication,
    QgsTask,
)

from ..utils import open_documentation, tr, log
from ..definitions.defaults import (
    ICON_PATH,
    ICON_PDF,
    ICON_LAYOUT,
    ICON_REPORT,
    ICON_HELP,
    REPORT_DOCUMENTATION,
)

Ui_DlgProgress, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/analysis_progress_dialog.ui")
)


class ProgressDialog(QtWidgets.QDialog, Ui_DlgProgress):
    """This progress dialog"""
    def __init__(
        self,
        init_message="Processing...",
        minimum=0,
        maximum=100,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)

        # Dialog window options
        self.setWindowIcon(QIcon(ICON_PATH))

        # Dialog window flags
        flags = (QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowCloseButtonHint)
        self.setWindowFlags(flags)

        # Dialog statuses
        self.task = None
        self.analysis_running = True
        self.lbl_status.setText(init_message)

        # Progress bar
        self.progress_bar.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.progress_bar.setMinimum(minimum)
        self.progress_bar.setMaximum(maximum)

        # Cancel/close button
        icon = self.style().standardIcon(QStyle.SP_DialogCancelButton)
        self.btn_cancel.setIcon(icon)

        # Report menu
        self.menu = QMenu("&View Report")
        self.btn_view_report.setMenu(self.menu)
        self.btn_view_report.setIcon(QIcon(ICON_REPORT))

        # Menu button to open report in Layout designer
        action = QAction(QIcon(ICON_LAYOUT), "Layout designer", parent=self)
        action.triggered.connect(self.view_report_layout_designer)
        action.setEnabled(True)
        self.menu.addAction(action)

        # Open a PDF version of the report
        action = QAction(QIcon(ICON_PDF), "Open PDF", parent=self)
        action.triggered.connect(self.view_report_pdf)
        action.setEnabled(True)
        self.menu.addAction(action)

        # Open a Help for reports
        action = QAction(QIcon(ICON_HELP), "Help", parent=self)
        action.triggered.connect(self.open_report_help)
        action.setEnabled(True)
        self.menu.addAction(action)

        # Connections
        self.btn_cancel.clicked.connect(self.cancel_clicked)

    def run(self, task):
        """Starts the task to run in the background.

        :param task: QgsTask which will run the dialog
        :type task: QgsTask
        """

        print('run')

        self.task = task

        # self.task.taskTerminated.connect(self.test)
        # self.task.taskCompleted.connect(self.test2)

        self.show()
        self.exec_()

    # def test(self):
    #
    #     print('====================================a test=============================================')
    #
    # def test2(self):
    #
    #     print('====================================a test2=============================================')

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

                if self.task:
                    self.task.setProgress(int(value))
            except RuntimeError:
                log(tr("Error setting value to a progress bar"), notify=False)

            if value >= 100:

                print('analysis is done')

                # Analysis has finished

                # Steps when analysis stopped

                self.change_status_message("Analysis has finished.")
                self.processing_finished()

    def change_status_message(self, message="Processing...") -> None:
        """Updates the status message

        :param message: Message to show on the status bar
        :type message: str
        """

        self.lbl_status.setText(tr(message))

    def view_report_pdf(self) -> None:
        """Opens a PDF version of the report"""
        pass

    def view_report_layout_designer(self) -> None:
        """Opens the report in layout designer"""
        pass

    def open_report_help(self) -> None:
        """Opens the Report guide in a browser"""
        open_documentation(REPORT_DOCUMENTATION)

    def cancel_clicked(self) -> None:
        """User clicked cancel.

        Processing will be stopped, and the UI will be updated to accommodate
        the processing status.
        """

        if self.analysis_running:
            # If cancelled is clicked
            self.stop_processing()
        else:
            # If close has been clicked. In this case processing were already stopped
            super().close()

    def reject(self) -> None:
        """Called when the dialog is closed"""

        if self.analysis_running:
            # Stops analysis if it is still running
            self.stop_processing()

        super().reject()

    def stop_processing(self) -> None:
        """The user cancelled the processing."""

        self.change_status_message("Processing has been cancelled by the user.")

        # Steps to stop analysis from running

        self.processing_cancelled()

    def processing_cancelled(self):
        """Post-steps when processing were cancelled."""

        self.analysis_running = False

        # Change cancel button to the close button status
        self.btn_cancel.setText(tr("Close"))
        icon = self.style().standardIcon(QStyle.SP_DialogCloseButton)
        self.btn_cancel.setIcon(icon)
        self.btn_view_report.setEnabled(False)

    def processing_finished(self) -> None:
        """Post-steps when processing succeeded."""

        self.analysis_running = False

        # Change cancel button to the close button status
        self.btn_cancel.setText(tr("Close"))
        icon = self.style().standardIcon(QStyle.SP_DialogCloseButton)
        self.btn_cancel.setIcon(icon)
        self.btn_view_report.setEnabled(True)
