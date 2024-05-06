# coding=utf-8

"""Plugin global settings.

Covers the plugin global settings which a user can set and save. The settings
will be saved using QgsSettings. Settings can be accessed via the QGIS options,
a button on the docking widget, and from the toolbar menu.
"""

import os
import typing
import uuid

import qgis.core
import qgis.gui

from qgis.analysis import QgsAlignRaster

from qgis.gui import QgsFileWidget, QgsOptionsPageWidget
from qgis.gui import QgsOptionsWidgetFactory
from qgis.PyQt import uic
from qgis.PyQt.QtGui import (
    QIcon,
    QShowEvent,
    QPixmap,
)
from qgis.utils import iface

from qgis.PyQt.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox, QWidget
from qgis.PyQt import QtCore

from ...conf import (
    settings_manager,
    Settings,
)
from ...definitions.constants import CPLUS_OPTIONS_KEY
from ...definitions.defaults import (
    GENERAL_OPTIONS_TITLE,
    ICON_PATH,
    OPTIONS_TITLE,
)
from ...utils import FileUtils, log, tr


Ui_DlgSettings, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/cplus_settings.ui")
)


class CplusSettings(Ui_DlgSettings, QgsOptionsPageWidget):
    message_bar: qgis.gui.QgsMessageBar

    """CPLUS plugin settings class.

    Class which manages the CPLUS settings. Initializes the UI, which can be accessed
    from the menu drop-down or the QGIS settings.
    """

    def __init__(self, parent=None) -> None:
        """QGIS CPLUS Plugin Settings dialog."""
        QgsOptionsPageWidget.__init__(self, parent)

        self.setupUi(self)
        self.message_bar = qgis.gui.QgsMessageBar(self)
        self.layout().insertWidget(0, self.message_bar)

        self.settings = qgis.core.QgsSettings()
        settings_manager.settings_updated[str, object].connect(self.on_settings_changed)

        # Connections
        self.folder_data.fileChanged.connect(self.base_dir_exists)

        self.map_layer_file_widget.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.map_layer_box.layerChanged.connect(self.map_layer_changed)

        self.mask_layer_widget.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.mask_layer_box.layerChanged.connect(self.mask_layer_changed)

        self.resample_method_box.addItem(
            tr("Nearest Neighbour"), QgsAlignRaster.ResampleAlg.RA_NearestNeighbour
        )
        self.resample_method_box.addItem(
            tr("Bilinear (2x2 Kernel)"), QgsAlignRaster.ResampleAlg.RA_Bilinear
        )
        self.resample_method_box.addItem(
            tr("Cubic (4x4 Kernel)"), QgsAlignRaster.ResampleAlg.RA_Cubic
        )
        self.resample_method_box.addItem(
            tr("Cubic B-Spline (4x4 Kernel)"), QgsAlignRaster.ResampleAlg.RA_CubicSpline
        )
        self.resample_method_box.addItem(
            tr("Lanczos (6x6 Kernel)"), QgsAlignRaster.ResampleAlg.RA_Lanczos
        )
        self.resample_method_box.addItem(
            tr("Average"), QgsAlignRaster.ResampleAlg.RA_Average
        )
        self.resample_method_box.addItem(tr("Mode"), QgsAlignRaster.ResampleAlg.RA_Mode)
        self.resample_method_box.addItem(
            tr("Maximum"), QgsAlignRaster.ResampleAlg.RA_Max
        )
        self.resample_method_box.addItem(
            tr("Minimum"), QgsAlignRaster.ResampleAlg.RA_Min
        )
        self.resample_method_box.addItem(
            tr("Median"), QgsAlignRaster.ResampleAlg.RA_Median
        )
        self.resample_method_box.addItem(
            tr("First Quartile (Q1)"), QgsAlignRaster.ResampleAlg.RA_Q1
        )
        self.resample_method_box.addItem(
            tr("Third Quartile (Q3)"), QgsAlignRaster.ResampleAlg.RA_Q3
        )

        # Mask layers
        add_icon = FileUtils.get_icon("symbologyAdd.svg")
        self.btn_add_mask.setIcon(add_icon)
        self.btn_add_mask.clicked.connect(self._on_add_mask_layer)

        remove_icon = FileUtils.get_icon("symbologyRemove.svg")
        self.btn_delete_mask.setIcon(remove_icon)
        self.btn_delete_mask.setEnabled(False)
        self.btn_delete_mask.clicked.connect(self._on_remove_mask_layer)

        edit_icon = FileUtils.get_icon("mActionToggleEditing.svg")
        self.btn_edit_mask.setIcon(edit_icon)
        self.btn_edit_mask.setEnabled(False)
        self.btn_edit_mask.clicked.connect(self._on_edit_mask_layer)

    def apply(self) -> None:
        """This is called on OK click in the QGIS options panel."""

        self.save_settings()

    def map_layer_changed(self, layer):
        """Sets the file path of the selected layer in file path input

        :param layer: Qgis map layer
        :type layer: QgsMapLayer
        """
        if layer is not None:
            self.map_layer_file_widget.setFilePath(layer.source())

    def mask_layer_changed(self, layer):
        """Sets the file path of the selected mask layer in file path input

        :param layer: Qgis map layer
        :type layer: QgsMapLayer
        """
        if layer is not None:
            self.mask_layer_widget.setFilePath(layer.source())

    def on_settings_changed(self, name: str, value: typing.Any):
        """Slot raised when settings has been changed.

        :param name: Name of the setting that has changed.
        :type name: str

        :param value: New value for the given settings name.
        :type value: Any
        """
        # Create NCS pathway subdirectory if base directory has changed.
        if name == Settings.BASE_DIR.value:
            if not value:
                return

            # Create data directories if they do not exist.
            FileUtils.create_ncs_pathways_dir(value)
            FileUtils.create_ncs_carbon_dir(value)
            FileUtils.create_pwls_dir(value)

    def base_dir_exists(self) -> bool:
        """Checks if the provided base directory exists.
        A warning messages is presented if the directory does not exist.

        :returns: Whether the base directory exists
        :rtype: bool
        """

        # Clears the error messages when doing next check
        self.message_bar.clearWidgets()

        folder_found = False
        base_dir_path = self.folder_data.filePath()
        if not os.path.exists(base_dir_path):
            # File not found
            self.message_bar.pushWarning(
                "CPLUS - Base directory not found: ", base_dir_path
            )
        else:
            folder_found = True

        return folder_found

    def save_settings(self) -> None:
        """Saves the settings.
        Also does error checking for settings (e.g if the custom logo exists).
        Will present the user with an error message if an issue is found.
        """
        # Advanced settings
        base_dir_path = self.folder_data.filePath()
        settings_manager.set_value(Settings.BASE_DIR, base_dir_path)

        # Carbon layers coefficient saving
        coefficient = self.carbon_coefficient_box.value()
        settings_manager.set_value(Settings.CARBON_COEFFICIENT, coefficient)

        # Pathway suitability index
        pathway_suitability_index = self.suitability_index_box.value()
        settings_manager.set_value(
            Settings.PATHWAY_SUITABILITY_INDEX, pathway_suitability_index
        )

        # Snapping settings saving
        settings_manager.set_value(
            Settings.SNAPPING_ENABLED, self.snapping_group_box.isChecked()
        )
        snap_layer_path = self.map_layer_file_widget.filePath()
        settings_manager.set_value(Settings.SNAP_LAYER, snap_layer_path)

        settings_manager.set_value(
            Settings.RESCALE_VALUES, self.rescale_values.isChecked()
        )
        settings_manager.set_value(
            Settings.RESAMPLING_METHOD, self.resample_method_box.currentIndex()
        )

        # Saving sieve function settings

        settings_manager.set_value(
            Settings.SIEVE_ENABLED, self.sieve_group_box.isChecked()
        )
        mask_layer_path = self.mask_layer_widget.filePath()
        settings_manager.set_value(Settings.SIEVE_MASK_PATH, mask_layer_path)

        settings_manager.set_value(
            Settings.SIEVE_THRESHOLD, self.pixel_size_box.value()
        )

        # Mask layers settings
        mask_paths = ""
        for row in range(0, self.lst_mask_layers.count()):
            item = self.lst_mask_layers.item(row)
            item_path = item.data(QtCore.Qt.DisplayRole)
            mask_paths += f"{item_path},"

        settings_manager.set_value(Settings.MASK_LAYERS_PATHS, mask_paths)

        # Checks if the provided base directory exists
        if not os.path.exists(base_dir_path):
            iface.messageBar().pushCritical(
                "CPLUS - Base directory not found: ", base_dir_path
            )

    def load_settings(self) -> None:
        """Loads the settings and displays it in the options UI"""
        # Advanced settings
        base_dir = settings_manager.get_value(Settings.BASE_DIR, default="")
        self.folder_data.setFilePath(base_dir)
        self.base_dir_exists()

        # Carbon layers coefficient
        coefficient = settings_manager.get_value(
            Settings.CARBON_COEFFICIENT, default=0.0
        )
        self.carbon_coefficient_box.setValue(float(coefficient))

        # Pathway suitability index
        pathway_suitability_index = settings_manager.get_value(
            Settings.PATHWAY_SUITABILITY_INDEX, default=0
        )
        self.suitability_index_box.setValue(float(pathway_suitability_index))

        # Snapping settings
        self.snapping_group_box.setChecked(
            settings_manager.get_value(
                Settings.SNAPPING_ENABLED, default=False, setting_type=bool
            )
        )
        snap_layer_path = settings_manager.get_value(Settings.SNAP_LAYER, default="")
        self.map_layer_file_widget.setFilePath(snap_layer_path)

        self.rescale_values.setChecked(
            settings_manager.get_value(
                Settings.RESCALE_VALUES, default=False, setting_type=bool
            )
        )
        self.resample_method_box.setCurrentIndex(
            int(settings_manager.get_value(Settings.RESAMPLING_METHOD, default=0))
        )

        # Sieve settings
        self.sieve_group_box.setChecked(
            settings_manager.get_value(
                Settings.SIEVE_ENABLED, default=False, setting_type=bool
            )
        )
        mask_layer_path = settings_manager.get_value(
            Settings.SIEVE_MASK_PATH, default=""
        )
        self.mask_layer_widget.setFilePath(mask_layer_path)

        self.pixel_size_box.setValue(
            float(settings_manager.get_value(Settings.SIEVE_THRESHOLD, default=10.0))
        )

        # Mask layers settings
        mask_paths = settings_manager.get_value(
            Settings.MASK_LAYERS_PATHS, default=None
        )
        mask_paths_list = mask_paths.split(",") if mask_paths else []

        for mask_path in mask_paths_list:
            if mask_path is "":
                continue
            item = QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, mask_path)
            self.lst_mask_layers.addItem(item)

        if len(mask_paths_list) > 0:
            self.mask_layers_changed()

    def showEvent(self, event: QShowEvent) -> None:
        """Show event being called. This will display the plugin settings.
        The stored/saved settings will be loaded.

        :param event: Event that has been triggered
        :type event: QShowEvent
        """

        super().showEvent(event)
        self.load_settings()

    def closeEvent(self, event: QShowEvent) -> None:
        """When closing the setings.

        :param event: Event that has been triggered
        :type event: QShowEvent
        """

        super().closeEvent(event)

    def _on_add_mask_layer(self, activated: bool):
        """Slot raised to add a mask layer."""
        data_dir = settings_manager.get_value(Settings.LAST_DATA_DIR, "")
        if not data_dir and self._layer:
            data_path = self._layer.source()
            if os.path.exists(data_path):
                data_dir = os.path.dirname(data_path)

        if not data_dir:
            data_dir = "/home"

        mask_path = self._show_mask_path_selector(data_dir)
        if not mask_path:
            return

        item = QListWidgetItem()
        item.setData(QtCore.Qt.DisplayRole, mask_path)

        if self.lst_mask_layers.findItems(mask_path, QtCore.Qt.MatchExactly):
            error_tr = tr("The selected mask layer already exists.")
            self.message_bar.pushMessage(error_tr, qgis.core.Qgis.MessageLevel.Warning)
            return

        self.lst_mask_layers.addItem(item)
        self.mask_layers_changed()

    def _on_edit_mask_layer(self, activated: bool):
        """Slot raised to edit a mask layer."""

        item = self.lst_mask_layers.currentItem()
        if not item:
            error_tr = tr("Select a mask layer first.")
            self.message_bar.pushMessage(error_tr, qgis.core.Qgis.MessageLevel.Warning)
            return
        mask_path = self._show_mask_path_selector(item.data(QtCore.Qt.DisplayRole))
        if not mask_path:
            return

        if self.lst_mask_layers.findItems(mask_path, QtCore.Qt.MatchExactly):
            error_tr = tr("The selected mask layer already exists.")
            self.message_bar.pushMessage(error_tr, qgis.core.Qgis.MessageLevel.Warning)
            return

        item.setData(QtCore.Qt.DisplayRole, mask_path)

    def _on_remove_mask_layer(self, activated: bool):
        """Slot raised to remove one or more selected mask layers."""
        item = self.lst_mask_layers.currentItem()
        if not item:
            error_tr = tr("Select the target mask layer first, before removing it.")
            self.message_bar.pushMessage(error_tr, qgis.core.Qgis.MessageLevel.Warning)
            return

        reply = QMessageBox.warning(
            self,
            tr("QGIS CPLUS PLUGIN | Settings"),
            tr('Remove the mask layer from "{}"?').format(
                item.data(QtCore.Qt.DisplayRole)
            ),
            QMessageBox.Yes,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            item_row = self.lst_mask_layers.row(item)
            self.lst_mask_layers.takeItem(item_row)

            self.mask_layers_changed()

    def _show_mask_path_selector(self, layer_dir: str) -> str:
        """Show file selector dialog for selecting a mask layer."""
        filter_tr = tr("All files")

        layer_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select mask Layer"),
            layer_dir,
            f"{filter_tr} (*.*)",
            options=QFileDialog.DontResolveSymlinks,
        )
        if not layer_path:
            return ""

        return layer_path

    def mask_layers_changed(self):
        contains_items = self.lst_mask_layers.count() > 0

        self.btn_edit_mask.setEnabled(contains_items)
        self.btn_delete_mask.setEnabled(contains_items)


class CplusOptionsFactory(QgsOptionsWidgetFactory):
    """Options factory initializes the CPLUS settings.

    Class which creates the widget required for the CPLUS settings.
    QgsOptionsWidgetFactory is used to accomplish this.
    """

    def __init__(self) -> None:
        """QGIS CPLUS Plugin Settings factory."""
        super().__init__()

        # Check version for API compatibility for managing items in
        # options tree view.
        version = qgis.core.Qgis.versionInt()
        log(str(version))
        if version < 33200:
            log("Old version")
            self.setTitle(GENERAL_OPTIONS_TITLE)
        else:
            log("New version")
            self.setTitle(OPTIONS_TITLE)
            self.setKey(CPLUS_OPTIONS_KEY)

    def icon(self) -> QIcon:
        """Returns the icon which will be used for the CPLUS options tab.

        :returns: An icon object which contains the provided custom icon
        :rtype: QIcon
        """

        return QIcon(ICON_PATH)

    def path(self) -> typing.List[str]:
        """
        Returns the path to place the widget page at.

        This instructs the registry to place the log options tab under the
        main CPLUS settings.

        :returns: Path name of the main CPLUS settings.
        :rtype: list
        """
        version = qgis.core.Qgis.versionInt()
        if version < 33200:
            return [OPTIONS_TITLE]

        return list()

    def createWidget(self, parent: QWidget) -> CplusSettings:
        """Creates a widget for CPLUS settings.

        :param parent: Parent widget
        :type parent: QWidget

        :returns: Widget to be used in the QGIS options
        :rtype: CplusSettings
        """

        return CplusSettings(parent)
