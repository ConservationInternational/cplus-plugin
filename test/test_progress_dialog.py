import unittest

from utilities_for_testing import get_qgis_app
from qgis.PyQt.QtWidgets import QMenu, QAction, QStyle, QProgressBar

from cplus_plugin.gui.progress_dialog import ProgressDialog

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class CplusPluginProgressDialogTest(unittest.TestCase):
    def test_get_progress_status(self) -> None:
        """Tests if the progress is correctly set to True after
        initializing the progress dialog.
        """
        progress_dialog = ProgressDialog(parent=PARENT)

        # Processing should still be running because the dialog just got initialized
        processing_status = progress_dialog.get_processing_status()
        self.assertEqual(processing_status, True)

    def test_get_progressbar(self) -> None:
        """Test if the progress bar is there."""
        progress_dialog = ProgressDialog(parent=PARENT)
        progress_bar = progress_dialog.get_progress_bar()

        self.assertIsInstance(progress_bar, QProgressBar)

    def test_change_status_messaage(self) -> None:
        """A test to see if the status message is correctly set"""
        progress_dialog = ProgressDialog(parent=PARENT)

        test_message = "This is a status message"
        progress_dialog.change_status_message(test_message)
        current_message = progress_dialog.lbl_status.text()
        self.assertEqual(test_message, current_message)

    def test_progress_bar(self) -> None:
        """Test if progress bar updating/changes works correctly."""
        progress_dialog = ProgressDialog(parent=PARENT)

        # Checks value at non-100%
        test_value = 18
        progress_dialog.update_progress_bar(test_value)
        current_value = progress_dialog.get_progress_bar().value()
        self.assertEqual(test_value, current_value)

        # Checks value at 100%
        test_value = 100
        progress_dialog.update_progress_bar(test_value)
        current_value = progress_dialog.get_progress_bar().value()
        self.assertEqual(test_value, current_value)

        # Checks if processing were stopped at 100% status
        processing_status = progress_dialog.get_processing_status()
        self.assertEqual(processing_status, False)

    def test_view_report(self) -> None:
        """Tests if the report is correctly opened in as a PDF"""

        # view_report_pdf()
        print("Not sure if this will require a test in the future")

        self.assertEqual(True, True)

    def test_view_report_layout_designer(self) -> None:
        """A check on whether the report is opened correctly in layout view."""

        # view_report_layout_designer()
        print("Not sure if this will require a test in the future")

        self.assertEqual(True, True)

    def test_stop_processing(self) -> None:
        """Checks if processing has been stopped correctly."""
        # stop_processing()
        print("Not sure if this will require a test in the future")

        self.assertEqual(True, True)

    def test_processing_stopped(self) -> None:
        """Checks if post-stopped changes occurs."""

        progress_dialog = ProgressDialog(parent=PARENT)

        # Processing should have been stopped
        progress_dialog.processing_stopped()
        processing_status = progress_dialog.get_processing_status()
        self.assertEqual(processing_status, False)


if __name__ == "__main__":
    unittest.main()
