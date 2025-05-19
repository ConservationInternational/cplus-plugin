import os

import qgis.core
from qgis.gui import QgsFileWidget, QgsMessageBar
from qgis.PyQt import uic, QtWidgets, QtCore, QtGui

from ...api.request import (
    CplusApiRequest,
    CHUNK_SIZE,
)
from ...api.layer_tasks import CreateUpdateDefaultLayerTask
from ...definitions.defaults import ICON_PATH, USER_DOCUMENTATION_SITE
from ...models.base import LayerType
from ...trends_earth import api
from ...trends_earth.constants import API_URL, TIMEOUT
from ...utils import (
    FileUtils,
    log,
    tr,
    zip_shapefile,
    get_layer_type,
    open_documentation,
)

Ui_PwlDlgAddEdit, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/priority_layer_add_dialog.ui")
)

WidgetUi, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/upload_layer_progress.ui")
)


class UploadProgressDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for showing the progress of the uploading priority layer."""

    dialog_closed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.btn_cancel = self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel)

        self.btn_cancel.clicked.connect(self.on_cancel)
        self.pg_bar.setValue(0)

    def update_status_message(self, message: str = None):
        """
        Update the label with the status message.

        param message: The current status message.
        :type str: message
        """
        if message is None:
            return
        self.lbl_info.setText(message)

    def update_task_progress(self, progress: float):
        """Slot raised to update the task progress.

        :param progress: Current progress of the layer upload.
        :type progress: float
        """
        self.pg_bar.setValue(int(progress))

    def on_task_completed(self):
        """Slot raised when overall layer upload has completed."""
        self.pg_bar.setValue(100)
        self.lbl_info.setText(tr("Layer upload completed"))
        self.close()

    def on_cancel(self):
        """Slot raised when the Close button has been clicked."""
        self.dialog_closed.emit()


class DlgPriorityAddEdit(QtWidgets.QDialog, Ui_PwlDlgAddEdit):
    def __init__(
        self,
        parent=None,
        layer: dict = {},
    ):
        super().__init__(parent)

        self.setupUi(self)
        self.layer = layer
        self.parent = parent

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)

        self.map_layer_file_widget.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.map_layer_box.layerChanged.connect(self.map_layer_changed)
        self.rb_common.setChecked(True)

        help_icon = FileUtils.get_icon("mActionHelpContents_green.svg")
        self.btn_help.setIcon(help_icon)
        self.btn_help.clicked.connect(self.open_help)

        if self.layer.get("layer_uuid"):
            self.setWindowTitle(tr("Edit Priority Weighted Layer"))
            self.txt_name.setText(self.layer.get("name"))
            self.map_layer_file_widget.setFilePath("")
            self.txt_description.setPlainText(
                self.layer.get("metadata", {}).get("description")
            )
            self.txt_version.setText(self.layer.get("version", ""))
            self.txt_license.setPlainText(self.layer.get("license", ""))
        else:
            self.setWindowTitle(tr("Add Priority Weighted Layer"))

        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.rejected.connect(self.cancel_clicked)

        self.btn_cancel = self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel)
        self.btn_save = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)

        self.trends_earth_api_client = api.APIClient(API_URL, TIMEOUT)

        self.upload_running = False
        self.task = None

        self.grid_layout = QtWidgets.QGridLayout()
        self.message_bar = QgsMessageBar()

        self.prepare_message_bar()

    @property
    def privacy_type(self):
        if self.rb_private.isChecked():
            return "private"
        if self.rb_internal.isChecked():
            return "internal"
        return "common"

    def prepare_message_bar(self):
        """Initializes the widget message bar settings"""

        self.message_bar.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        self.grid_layout.addWidget(
            self.message_bar, 0, 0, 1, 1, alignment=QtCore.Qt.AlignTop
        )
        self.mainLayout.insertLayout(0, self.grid_layout)
        self.message_bar.clearWidgets()

    def save(self):
        if not self.is_valid_layer():
            return

        self.upload_running = True

        self.btn_save.hide()
        self.message_bar.show()

        layer_properties = {
            "name": self.txt_name.text(),
            "description": self.txt_description.toPlainText(),
            "file_path": zip_shapefile(self.map_layer_file_widget.filePath()),
            "version": self.txt_version.text(),
            "license": self.txt_license.toPlainText(),
            "component_type": "priority_layer",
            "privacy_type": self.privacy_type,
        }

        if self.map_layer_file_widget.filePath() and os.path.exists(
            self.map_layer_file_widget.filePath()
        ):
            metadata = self.layer_metadata()
            layer_properties["metadata"] = metadata

        self.layer.update(layer_properties)

        request = CplusApiRequest()
        self.task = CreateUpdateDefaultLayerTask(
            layer=self.layer, request=request, chunk_size=CHUNK_SIZE
        )

        self.task.task_completed.connect(self.uploading_finished)
        self.task.taskTerminated.connect(self.uploading_cancelled)
        self.task.status_message_changed.connect(self.status_message_changed)
        self.task.custom_progress_changed.connect(self.on_progress_changed)
        qgis.core.QgsApplication.taskManager().addTask(self.task)

        self.progress_dialog = UploadProgressDialog(self)
        self.progress_dialog.setModal(True)
        self.progress_dialog.dialog_closed.connect(self.stop_upload)
        self.progress_dialog.show()

    def layer_metadata(self) -> dict:
        """
        Extracts and returns metadata from the selected layer file.

        Returns:
            dict: A dictionary containing metadata such as layer type, resolution,
                  nodata value, CRS, unit, and whether the CRS is geographic.
        """
        file_path = self.map_layer_file_widget.filePath()
        layer_type = get_layer_type(file_path)
        metadata = {
            "is_raster": layer_type == LayerType.RASTER,
        }

        layer = None

        if layer_type == LayerType.RASTER:
            layer = qgis.core.QgsRasterLayer(file_path)
            if layer.isValid():
                x_res = layer.rasterUnitsPerPixelX()
                y_res = layer.rasterUnitsPerPixelY()
                provider = layer.dataProvider()
                nodata = (
                    provider.sourceNoDataValue(1)
                    if provider and provider.sourceHasNoDataValue(1)
                    else None
                )
                metadata.update(
                    {
                        "resolution": [x_res, y_res],
                        "nodata_value": nodata,
                    }
                )
        elif layer_type == LayerType.VECTOR:
            layer = qgis.core.QgsVectorLayer(file_path)

        if layer and layer.isValid() and layer.crs() and layer.crs().isValid():
            crs = layer.crs()
            metadata.update(
                {
                    "crs": crs.authid(),
                    "unit": crs.mapUnits().name,
                    "is_geographic": crs.isGeographic(),
                }
            )

        return metadata

    def is_valid_layer(self) -> bool:
        """
        Validates the required fields for adding or editing a priority weighted layer.

        Returns:
            bool: True if all required fields are valid, False otherwise.
        """
        # Check if the layer name is provided
        if not self.txt_name.text().strip():
            self.set_status_message(self.tr("Enter a name for the layer."), 1)
            return False

        # For new layers, ensure a file path is provided
        if (
            self.layer.get("layer_uuid") is None
            and not self.map_layer_file_widget.filePath().strip()
        ):
            self.set_status_message(self.tr("Enter a path to the layer."), 1)
            return False

        # Check if the description is provided
        if not self.txt_description.toPlainText().strip():
            self.set_status_message(self.tr("Enter a description for the layer."))
            return False

        # TODO: Validate the Layer using the validation manager
        return True

    def map_layer_changed(self, layer):
        """Sets the file path of the selected layer in file path input

        :param layer: Qgis map layer
        :type layer: QgsMapLayer
        """
        if layer is not None:
            self.map_layer_file_widget.setFilePath(layer.source())

    def cancel_clicked(self) -> None:
        """User clicked cancel.
        Layer upload will be stopped
        """

        if self.upload_running:
            # If cancelled is clicked
            self.stop_upload()
            try:
                if self.task:
                    self.task.upload_cancelled = True
                    self.task.cancel()
            except RuntimeError as e:
                log("Failed with error :", str(e))
        super().close()

    def reject(self) -> None:
        """Called when the dialog is closed"""

        if self.upload_running:
            self.stop_upload()
            try:
                if self.task:
                    self.task.upload_cancelled = True
                    self.task.cancel()
            except RuntimeError as e:
                log("Failed with error :", str(e))

        super().reject()

    def stop_upload(self, hide=False) -> None:
        """The user cancelled the layer upload."""
        # Stops the layer upload task
        self.cancel_upload_task()
        self.uploading_cancelled()

    def uploading_cancelled(self) -> None:
        """Post-steps when layer upload was cancelled."""

        self.upload_running = False
        self.btn_cancel.setText(tr("Close"))
        if self.parent:
            self.parent.refresh_default_layers_table()

    def cancel_upload_task(self):
        try:
            if self.task:
                self.task.upload_cancelled = True
                self.task.cancel_task()
        except Exception as e:
            log(f"Problem cancelling task, {e}")

        self.upload_cancelled = True

    def uploading_finished(self):
        """Post-steps when uploading is finished."""

        self.upload_running = False
        if self.parent:
            self.parent.refresh_default_layers_table()
        self.close()

    def status_message_changed(self, message: str) -> None:
        """Update the status message in the progress dialog.

        :param message: The message to display.
        :type message: str
        """
        self.set_status_message(message)
        self.progress_dialog.update_status_message(message)

    def on_progress_changed(self, progress: float) -> None:
        """Update the progress bar in the progress dialog.

        :param progress: The progress to display.
        :type progress: float
        """
        self.progress_dialog.update_task_progress(progress)

    def set_status_message(self, message, level=0):
        self.message_bar.clearWidgets()
        self.message_bar.pushMessage(message, level=level, duration=5)

    def open_help(self):
        open_documentation(USER_DOCUMENTATION_SITE)
