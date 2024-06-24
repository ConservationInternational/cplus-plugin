import os

from PyQt5.QtCore import pyqtSignal
from qgis.core import QgsTask

from ..api.request import CplusApiRequest
from ..conf import settings_manager

MESSAGE_CATEGORY = "My subclass tasks"


class FetchOnlineTaskStatusTask(QgsTask):
    """This shows how to subclass QgsTask"""

    task_completed = pyqtSignal()

    def __init__(self, main_widget):
        super().__init__()
        self.main_widget = main_widget
        self.exception = None

    def run(self):
        """Run fetch status using API."""

        request = CplusApiRequest()
        online_task = settings_manager.get_online_task()
        if online_task:
            logs = request.fetch_scenario_logs(online_task["online_uuid"])
            log_file = open(os.path.join(online_task["directory"], "processing.log"))
            lines = log_file.readlines()
            log_file.close()

            curr_logs = []
            with open(
                os.path.join(online_task["directory"], "processing.log"), "r"
            ) as log_file:
                curr_logs = log_file.readlines()

            for idx, curr_log in enumerate(curr_logs):
                if curr_log.endswith("INFO Task is sent to worker."):
                    curr_logs = curr_logs[:idx]
                    break

            with open(
                os.path.join(online_task["directory"], "processing.log"), "w"
            ) as log_file:
                for curr_log in curr_logs:
                    log_file.write(curr_log)
                for log_dict in logs:
                    if not lines[-1].endswith(
                        f"{log_dict['severity']}{log_dict['log']}"
                    ):
                        log_file.write(
                            f"\n{log_dict['date_time']} "
                            f"{log_dict['severity']} "
                            f"{log_dict['log']}"
                        )
            if logs[-1]["log"] == "Task has been completed.":
                self.task_completed.emit()

        return True

    def finished(self, result):
        """This method is automatically called when self.run returns.
        result is the return value from self.run.
        This function is automatically called when the task has completed (
        successfully or otherwise). You just implement finished() to do
        whatever
        follow up stuff should happen after the task is complete. finished is
        always called from the main thread, so it's safe to do GUI
        operations and raise Python exceptions here.
        """
        super().finished(result)

    def cancel(self):
        super().cancel()
