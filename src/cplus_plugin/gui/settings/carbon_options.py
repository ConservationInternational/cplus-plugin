# coding=utf-8

"""Plugin carbon settings."""

import os
import typing

import qgis.core

from qgis.gui import QgsFileWidget, QgsMessageBar, QgsOptionsPageWidget
from qgis.gui import QgsOptionsWidgetFactory
from qgis.PyQt import uic
from qgis.PyQt import QtCore, sip
from qgis.PyQt.QtGui import (
    QIcon,
    QPixmap,
    QShowEvent,
    QStandardItem,
    QStandardItemModel,
)

from qgis.PyQt.QtWidgets import QButtonGroup, QHeaderView, QWidget

from ...api.base import ApiRequestStatus
from ...api.carbon import (
    start_irrecoverable_carbon_download,
    get_downloader_task,
)
from ...api.layer_tasks import calculate_zonal_stats_task

from ...conf import (
    settings_manager,
    Settings,
)
from ...definitions.constants import (
    CPLUS_OPTIONS_KEY,
    CARBON_OPTIONS_KEY,
    LAYER_NAME_ATTRIBUTE,
    MEAN_VALUE_ATTRIBUTE,
)
from ...definitions.defaults import (
    CARBON_IMPACT_PER_HA_HEADER,
    OPTIONS_TITLE,
    CARBON_OPTIONS_TITLE,
    CARBON_SETTINGS_ICON_PATH,
    LAYER_NAME_HEADER,
)
from ...models.base import DataSourceType
from ...utils import FileUtils, tr


Ui_CarbonSettingsWidget, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/carbon_settings.ui")
)


class NaturebaseCarbonImpactModel(QStandardItemModel):
    """Model for displaying carbon impact values in a table view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels([LAYER_NAME_HEADER, CARBON_IMPACT_PER_HA_HEADER])

    def _readonly_item(self, text: str = "") -> QStandardItem:
        """Helper to create a non-editable QStandardItem with
        given display text.
        """
        item = QStandardItem(text)
        item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)

        return item

    def add_row(self, layer_name: str, carbon_impact: float):
        """Adds a row with the layer details to the model.

        :param layer_name: Name of the layer.
        :type layer_name: str

        :param carbon_impact: Value of the carbon impact.
        :type carbon_impact: float
        """
        name_item = self._readonly_item(str(layer_name))
        carbon_item = self._readonly_item(str(carbon_impact))
        carbon_item.setData(carbon_impact, QtCore.Qt.ItemDataRole.UserRole)

        self.appendRow([name_item, carbon_item])

    def remove_all_rows(self) -> None:
        """Remove all rows from the model while preserving the column headers."""
        row_count = self.rowCount()
        if row_count > 0:
            self.removeRows(0, row_count)


class CarbonSettingsWidget(QgsOptionsPageWidget, Ui_CarbonSettingsWidget):
    """Carbon settings widget."""

    def __init__(self, parent=None):
        QgsOptionsPageWidget.__init__(self, parent)
        self.setupUi(self)

        self.message_bar = QgsMessageBar(self)
        self.layout().insertWidget(0, self.message_bar)

        tif_file_filter = tr("GeoTIFF (*.tif *.tiff *.TIF *.TIFF)")

        # Irrecoverable carbon
        self.gb_ic_reference_layer.toggled.connect(
            self._on_irrecoverable_group_box_toggled
        )

        self._irrecoverable_group = QButtonGroup(self)
        self._irrecoverable_group.addButton(self.rb_local, DataSourceType.LOCAL.value)
        self._irrecoverable_group.addButton(self.rb_online, DataSourceType.ONLINE.value)
        self._irrecoverable_group.idToggled.connect(
            self._on_irrecoverable_button_group_toggled
        )

        self.fw_irrecoverable_carbon.setDialogTitle(
            tr("Select Irrecoverable Carbon Dataset")
        )
        self.fw_irrecoverable_carbon.setRelativeStorage(
            QgsFileWidget.RelativeStorage.Absolute
        )
        self.fw_irrecoverable_carbon.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.fw_irrecoverable_carbon.setFilter(tif_file_filter)

        self.cbo_irrecoverable_carbon.layerChanged.connect(
            self._on_irrecoverable_carbon_layer_changed
        )
        self.cbo_irrecoverable_carbon.setFilters(
            qgis.core.QgsMapLayerProxyModel.Filter.RasterLayer
        )

        self.fw_save_online_file.setDialogTitle(
            tr("Specify Save Location of Irrecoverable Carbon Dataset")
        )
        self.fw_save_online_file.setRelativeStorage(
            QgsFileWidget.RelativeStorage.Absolute
        )
        self.fw_save_online_file.setStorageMode(QgsFileWidget.StorageMode.SaveFile)
        self.fw_save_online_file.setFilter(tif_file_filter)

        # self.lbl_url_tip.setPixmap(FileUtils.get_pixmap("info_green.svg"))
        # self.lbl_url_tip.setScaledContents(True)

        self.btn_ic_download.setIcon(FileUtils.get_icon("downloading_svg.svg"))
        self.btn_ic_download.clicked.connect(self.on_download_irrecoverable_carbon)

        # Use the task to get real time updates on the download progress
        self._irrecoverable_carbon_downloader = None
        self._configure_irrecoverable_carbon_downloader_updates()

        # Stored carbon
        self.fw_biomass.setDialogTitle(tr("Select Reference Layer"))
        self.fw_biomass.setRelativeStorage(QgsFileWidget.RelativeStorage.Absolute)
        self.fw_biomass.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.fw_biomass.setFilter(tif_file_filter)

        self.cbo_biomass.layerChanged.connect(self._on_biomass_layer_changed)
        self.cbo_biomass.setFilters(qgis.core.QgsMapLayerProxyModel.Filter.RasterLayer)

        # Naturebase carbon impact
        self.zonal_stats_task = None
        self._carbon_impact_model = NaturebaseCarbonImpactModel()
        self.tv_naturebase_carbon_impact.setModel(self._carbon_impact_model)
        self.tv_naturebase_carbon_impact.setSortingEnabled(True)

        header = self.tv_naturebase_carbon_impact.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        self.load_carbon_impact()
        self.tv_naturebase_carbon_impact.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)

        self.btn_reload_carbon_impact.clicked.connect(
            self._on_reload_naturebase_carbon_impact
        )

    def load_carbon_impact(self):
        """Load carbon impact info based on the latest values in settings."""
        self._carbon_impact_model.remove_all_rows()
        carbon_impact_info = settings_manager.get_nature_base_zonal_stats()
        if carbon_impact_info:
            for impact in carbon_impact_info.result_collection:
                layer_name = impact.get(LAYER_NAME_ATTRIBUTE)
                mean_value = impact.get(MEAN_VALUE_ATTRIBUTE) or 0.0
                self._carbon_impact_model.add_row(layer_name, mean_value)

            updated_date_str = (
                f'<html><head/><body><p><span style=" color:#6a6a6a;"><i>'
                f'{self.tr("Last updated")}: {carbon_impact_info.to_local_time()}</i></span></p></body></html>'
            )
            self.lbl_last_updated_carbon_impact.setText(updated_date_str)

    def apply(self) -> None:
        """This is called on OK click in the QGIS options panel."""
        self.save_settings()

    def save_settings(self) -> None:
        """Saves the settings."""
        # Irrecoverable carbon
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_LOCAL_SOURCE,
            self.fw_irrecoverable_carbon.filePath(),
        )
        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH,
            self.fw_save_online_file.filePath(),
        )

        if self.rb_local.isChecked():
            settings_manager.set_value(
                Settings.IRRECOVERABLE_CARBON_SOURCE_TYPE, DataSourceType.LOCAL.value
            )
        elif self.rb_online.isChecked():
            settings_manager.set_value(
                Settings.IRRECOVERABLE_CARBON_SOURCE_TYPE, DataSourceType.ONLINE.value
            )

        settings_manager.set_value(
            Settings.IRRECOVERABLE_CARBON_ENABLED,
            self.gb_ic_reference_layer.isChecked(),
        )

        # Stored carbon
        settings_manager.set_value(
            Settings.STORED_CARBON_BIOMASS_PATH,
            self.fw_biomass.filePath(),
        )

        # Carbon impact
        settings_manager.set_value(
            Settings.AUTO_REFRESH_NATURE_BASE_ZONAL_STATS,
            self.cb_auto_refresh_carbon_impact.isChecked(),
        )

    def load_settings(self):
        """Loads the settings and displays it in the UI."""
        # Irrecoverable carbon
        irrecoverable_carbon_enabled = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_ENABLED, default=False
        )
        if irrecoverable_carbon_enabled:
            self.gb_ic_reference_layer.setChecked(True)
        else:
            self.gb_ic_reference_layer.setChecked(False)

        # Local path
        self.fw_irrecoverable_carbon.setFilePath(
            settings_manager.get_value(
                Settings.IRRECOVERABLE_CARBON_LOCAL_SOURCE, default=""
            )
        )

        # Online config
        self.fw_save_online_file.setFilePath(
            settings_manager.get_value(
                Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH, default=""
            )
        )

        source_type_int = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_SOURCE_TYPE,
            default=DataSourceType.ONLINE.value,
            setting_type=int,
        )
        if source_type_int == DataSourceType.LOCAL.value:
            self.rb_local.setChecked(True)
            self.sw_irrecoverable_carbon.setCurrentIndex(0)
        elif source_type_int == DataSourceType.ONLINE.value:
            self.rb_online.setChecked(True)
            self.sw_irrecoverable_carbon.setCurrentIndex(1)

        self.validate_current_irrecoverable_data_source()

        self.reload_irrecoverable_carbon_download_status()

        # Stored carbon - protect
        self.fw_biomass.setFilePath(
            settings_manager.get_value(Settings.STORED_CARBON_BIOMASS_PATH, default="")
        )

        # Carbon impact
        auto_refresh = settings_manager.get_value(
            Settings.AUTO_REFRESH_NATURE_BASE_ZONAL_STATS,
            default=False,
            setting_type=bool,
        )
        self.cb_auto_refresh_carbon_impact.setChecked(auto_refresh)

    def showEvent(self, event: QShowEvent) -> None:
        """Show event being called. This will display the plugin settings.
        The saved settings will be loaded.

        :param event: Event that has been triggered.
        :type event: QShowEvent
        """
        super().showEvent(event)
        self.load_settings()

    def reload_irrecoverable_carbon_download_status(self):
        """Fetch the latest download status of the irrecoverable carbon
        dataset from the online source if applicable.
        """
        status = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_DOWNLOAD_STATUS, None, int
        )
        if status is None:
            return

        # Set notification icon
        path = ""
        status_type = ApiRequestStatus.from_int(status)
        if status_type == ApiRequestStatus.COMPLETED:
            path = FileUtils.get_icon_path("mIconSuccess.svg")
        elif status_type == ApiRequestStatus.ERROR:
            path = FileUtils.get_icon_path("mIconWarning.svg")
        elif status_type == ApiRequestStatus.NOT_STARTED:
            path = FileUtils.get_icon_path("mIndicatorTemporal.svg")
        elif status_type == ApiRequestStatus.IN_PROGRESS:
            path = FileUtils.get_icon_path("progress-indicator.svg")
        elif status_type == ApiRequestStatus.CANCELED:
            path = FileUtils.get_icon_path("mTaskCancel.svg")

        self.lbl_download_status_tip.svg_path = path

        # Set notification description
        description = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_STATUS_DESCRIPTION, "", str
        )
        self.lbl_ic_download_status.setText(description)

    def _configure_irrecoverable_carbon_downloader_updates(self):
        """Get current downloader and connect the signals of the
        task in order to update the UI.
        """
        # Use the task to get real time updates on the download progress
        self._irrecoverable_carbon_downloader = get_downloader_task()

        if self._irrecoverable_carbon_downloader is None:
            return

        self._irrecoverable_carbon_downloader.started.connect(
            self.reload_irrecoverable_carbon_download_status
        )
        self._irrecoverable_carbon_downloader.canceled.connect(
            self.reload_irrecoverable_carbon_download_status
        )
        self._irrecoverable_carbon_downloader.completed.connect(
            self.reload_irrecoverable_carbon_download_status
        )
        self._irrecoverable_carbon_downloader.error_occurred.connect(
            self.reload_irrecoverable_carbon_download_status
        )

    def validate_irrecoverable_carbon_url(self) -> bool:
        """Checks if the irrecoverable data URL is valid.

        :returns: True if the link is valid else False if the
        URL is empty, points to a local file or if not
        well-formed.
        :rtype: bool
        """
        dataset_url = settings_manager.get_value(
            Settings.IRRECOVERABLE_CARBON_ONLINE_SOURCE, default="", setting_type=str
        )
        if not dataset_url:
            self.message_bar.pushWarning(
                tr("CPLUS - Irrecoverable carbon dataset"), tr("URL not defined")
            )
            return False

        url_checker = QtCore.QUrl(dataset_url, QtCore.QUrl.StrictMode)
        if url_checker.isLocalFile():
            self.message_bar.pushWarning(
                tr("CPLUS - Irrecoverable carbon dataset"),
                tr("Invalid URL referencing a local file"),
            )
            return False
        else:
            if not url_checker.isValid():
                self.message_bar.pushWarning(
                    tr("CPLUS - Irrecoverable carbon dataset"),
                    tr("URL is invalid."),
                )
                return False

        return True

    def on_download_irrecoverable_carbon(self):
        """Slot raised to check download link and initiate download
        process of the irrecoverable carbon data.

        The function will check and save the currently defined local
        save as path for the reference dataset as this will be required
        and fetched by the background download process.

        """
        valid_url = self.validate_irrecoverable_carbon_url()
        if not valid_url:
            tr_title = tr("CPLUS - Online irrecoverable carbon dataset")
            tr_msg = tr("URL for downloading irrecoverable carbon data is invalid.")
            self.message_bar.pushWarning(tr_title, tr_msg)

            return

        if not self.fw_save_online_file.filePath():
            tr_title = tr("CPLUS - Online irrecoverable carbon dataset")
            tr_msg = tr(
                "File path for saving downloaded irrecoverable "
                "carbon dataset not defined"
            )
            self.message_bar.pushWarning(tr_title, tr_msg)

            return

        # Check if the local path has been saved in settings or varies from
        # what already is saved in settings
        download_save_path = self.fw_save_online_file.filePath()
        if (
            settings_manager.get_value(
                Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH,
                default="",
                setting_type=str,
            )
            != download_save_path
        ):
            settings_manager.set_value(
                Settings.IRRECOVERABLE_CARBON_ONLINE_LOCAL_PATH, download_save_path
            )

        # (Re)initiate download
        start_irrecoverable_carbon_download()

        # Get downloader for UI updates
        self._configure_irrecoverable_carbon_downloader_updates()

    def validate_current_irrecoverable_data_source(self):
        """Checks if the currently selected irrecoverable data source
        is valid.
        """
        self.message_bar.clearWidgets()

        if self.rb_local.isChecked():
            local_path = self.fw_irrecoverable_carbon.filePath()
            if not os.path.exists(local_path):
                tr_msg = tr("CPLUS - Local irrecoverable carbon dataset not found")
                self.message_bar.pushWarning(tr_msg, local_path)
        elif self.rb_online.isChecked():
            _ = self.validate_irrecoverable_carbon_url()
            if not self.fw_save_online_file.filePath():
                tr_msg = tr("CPLUS - Online irrecoverable carbon dataset")
                self.message_bar.pushWarning(
                    tr_msg, tr("File path for saving dataset not defined")
                )

    def _on_irrecoverable_button_group_toggled(self, button_id: int, toggled: bool):
        """Slot raised when a button in the irrecoverable
        button group has been toggled.

        :param button_id: Button identifier.
        :type button_id: int

        :param toggled: True if the button is checked else False
        if unchecked.
        :type toggled: bool
        """
        if button_id == DataSourceType.LOCAL.value and toggled:
            self.sw_irrecoverable_carbon.setCurrentIndex(0)
        elif button_id == DataSourceType.ONLINE.value and toggled:
            self.sw_irrecoverable_carbon.setCurrentIndex(1)

    def _on_irrecoverable_group_box_toggled(self, toggled: bool):
        """Slot raised when the irrecoverable group box has
        been toggled.

        :param toggled: True if the button is checked else
        False if unchecked.
        :type toggled: bool
        """
        settings_manager.set_value(Settings.IRRECOVERABLE_CARBON_ENABLED, toggled)

    def _on_irrecoverable_carbon_layer_changed(self, layer: qgis.core.QgsMapLayer):
        """Sets the file path of the currently selected irrecoverable
        layer in the corresponding file input widget.

        :param layer: Currently selected layer.
        :type layer: QgsMapLayer
        """
        if layer is not None:
            self.fw_irrecoverable_carbon.setFilePath(layer.source())

    def _on_biomass_layer_changed(self, layer: qgis.core.QgsMapLayer):
        """Sets the file path of the currently selected biomass
        layer in the corresponding file input widget.

        :param layer: Currently selected layer.
        :type layer: QgsMapLayer
        """
        if layer is not None:
            self.fw_biomass.setFilePath(layer.source())

    def _on_reload_naturebase_carbon_impact(self):
        """Slot raised to initiate the fetching of Naturebase zonal stats."""
        # Disconnect any existing zonal stats receivers
        if self.zonal_stats_task and not sip.isdeleted(self.zonal_stats_task):
            self.zonal_stats_task.statusChanged.disconnect(
                lambda s: self.reload_zonal_stats_task_status()
            )
            self.zonal_stats_task.taskCompleted.disconnect(
                self._on_zonal_stats_complete_or_error
            )
            self.zonal_stats_task.taskTerminated.disconnect(
                self._on_zonal_stats_complete_or_error
            )

        self.zonal_stats_task = calculate_zonal_stats_task()

        # Reconnect signals
        if self.zonal_stats_task:
            self.zonal_stats_task.statusChanged.connect(
                lambda s: self.reload_zonal_stats_task_status()
            )
            self.zonal_stats_task.progressChanged.connect(
                lambda s: self.reload_zonal_stats_task_status()
            )
            self.zonal_stats_task.taskCompleted.connect(
                self._on_zonal_stats_complete_or_error
            )
            self.zonal_stats_task.taskTerminated.connect(
                self._on_zonal_stats_complete_or_error
            )

        self.btn_reload_carbon_impact.setEnabled(False)
        self.tv_naturebase_carbon_impact.setEnabled(False)

        # Update the latest status
        self.reload_zonal_stats_task_status()

    def _on_zonal_stats_complete_or_error(self):
        """Re-enable controls and refresh table view if applicable."""
        self.btn_reload_carbon_impact.setEnabled(True)
        self.tv_naturebase_carbon_impact.setEnabled(True)
        if self.zonal_stats_task.status() == qgis.core.QgsTask.TaskStatus.Complete:
            self.load_carbon_impact()

    def reload_zonal_stats_task_status(self):
        """Update icon and description of zonal stats task."""
        icon_path = ""
        description = ""
        if self.zonal_stats_task:
            status = self.zonal_stats_task.status()
            if status == qgis.core.QgsTask.TaskStatus.OnHold:
                icon_path = FileUtils.get_icon_path("mIndicatorTemporal.svg")
                description = self.tr("Not started")
            elif status == qgis.core.QgsTask.TaskStatus.Queued:
                icon_path = FileUtils.get_icon_path("mIndicatorTemporal.svg")
                description = self.tr("Queued")
            elif status == qgis.core.QgsTask.TaskStatus.Running:
                icon_path = FileUtils.get_icon_path("progress-indicator.svg")
                description = f"{self.tr('Running')} ({int(self.zonal_stats_task.progress())}%)..."
            elif status == qgis.core.QgsTask.TaskStatus.Complete:
                icon_path = FileUtils.get_icon_path("mIconSuccess.svg")
                description = self.tr("Completed")
            elif status == qgis.core.QgsTask.TaskStatus.Terminated:
                icon_path = FileUtils.get_icon_path("mIconWarning.svg")
                description = self.tr("Terminated")

        self.lbl_carbon_impact_status_icon.svg_path = icon_path
        self.lbl_carbon_impact_status_description.setText(description)


class CarbonOptionsFactory(QgsOptionsWidgetFactory):
    """Factory for defining CPLUS carbon settings."""

    def __init__(self) -> None:
        super().__init__()

        # Check version for API compatibility for managing items in
        # options tree view.
        version = qgis.core.Qgis.versionInt()
        if version >= 33200:
            self.setKey(CARBON_OPTIONS_KEY)

        self.setTitle(tr(CARBON_OPTIONS_TITLE))

    def icon(self) -> QIcon:
        """Returns the icon which will be used for the carbon settings item.

        :returns: An icon object which contains the provided custom icon
        :rtype: QIcon
        """
        return QIcon(CARBON_SETTINGS_ICON_PATH)

    def path(self) -> typing.List[str]:
        """
        Returns the path to place the widget page at.

        This instructs the registry to place the carbon options tab under the
        main CPLUS settings.

        :returns: Path name of the main CPLUS settings.
        :rtype: list
        """
        version = qgis.core.Qgis.versionInt()
        if version < 33200:
            return [OPTIONS_TITLE]

        return [CPLUS_OPTIONS_KEY]

    def createWidget(self, parent: QWidget) -> CarbonSettingsWidget:
        """Creates a widget for carbon settings.

        :param parent: Parent widget
        :type parent: QWidget

        :returns: Widget for defining carbon settings.
        :rtype: CarbonSettingsWidgetSettingsWidget
        """
        return CarbonSettingsWidget(parent)
