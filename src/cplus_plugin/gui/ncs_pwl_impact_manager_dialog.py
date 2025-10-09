# -*- coding: utf-8 -*-
"""
Dialog for creating a new financial PWL.
"""

import json
import os
import typing

from qgis.core import Qgis
from qgis.gui import QgsGui, QgsMessageBar

from qgis.PyQt import QtCore, QtGui, QtWidgets

from qgis.PyQt.uic import loadUiType

from ..conf import settings_manager, Settings
from ..definitions.defaults import ICON_PATH, USER_DOCUMENTATION_SITE
from ..models.base import NcsPathway, PriorityLayerType
from ..utils import FileUtils, open_documentation, tr, log


WidgetUi, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/ncs_pwl_impact_manager_dialog.ui")
)

IMPACT_MATRIX_COLORS = {
    -3: {"color": "#d7191c", "impact": "Worst"},
    -2: {"color": "#f07c4a", "impact": "Worse"},
    -1: {"color": "#fec981", "impact": "Bad"},
    0: {"color": "#ffffc0", "impact": "Neutral"},
    1: {"color": "#c4e687", "impact": "Good"},
    2: {"color": "#77c35c", "impact": "Better"},
    3: {"color": "#1a9641", "impact": "Best"},
}

DEFAULT_CELL_STYLE = "QLineEdit {background: white;} QLineEdit:hover {border: 1px solid gray; background: white;}"


class RotatedHeaderView(QtWidgets.QHeaderView):
    """
    A QHeaderView subclass that displays header labels rotated 90 degrees.
    """

    def __init__(self, orientation, parent=None):
        """
        Initialize the rotated header view.

        :param orientation: The orientation of the header (Qt.Horizontal or Qt.Vertical).
        :param parent: The parent widget.
        """
        super().__init__(orientation, parent)
        self.setMinimumSectionSize(20)

    def paintSection(self, painter, rect, logicalIndex):
        """
        Paints the header section rotated 90 degrees.

        :param painter: QPainter object used for painting.
        :param rect: QRect of the section to paint.
        :param logicalIndex: Logical index of the section.
        """
        painter.save()
        # Move the painter origin to the bottom-left of the section
        painter.translate(rect.x() + rect.width(), rect.y())
        painter.rotate(90)
        # Paint the section using the base class at the new orientation
        new_rect = QtCore.QRect(0, 0, rect.height(), rect.width())
        super().paintSection(painter, new_rect, logicalIndex)
        painter.restore()

    def minimumSizeHint(self):
        """
        Returns the minimum size hint with transposed dimensions for rotation.
        """
        size = super().minimumSizeHint()
        size.transpose()
        return size

    def sectionSizeFromContents(self, logicalIndex):
        """
        Returns the section size from contents, transposed for rotation.

        :param logicalIndex: Logical index of the section.
        """
        size = super().sectionSizeFromContents(logicalIndex)
        size.transpose()
        return size


class VerticalLabel(QtWidgets.QLabel):
    """
    A QLabel subclass that displays its text vertically (rotated 270 degrees).
    Used for vertical header in the matrix table.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        """
        Paints the label text rotated 270 degrees (vertical orientation).
        """
        painter = QtGui.QPainter(self)
        painter.translate(0, self.height())
        painter.rotate(-90)
        painter.drawText(
            0, 0, self.height(), self.width(), QtCore.Qt.AlignCenter, self.text()
        )

    def sizeHint(self):
        """
        Returns the size hint, swapping width and height for vertical orientation.
        """
        size = super().sizeHint()
        return size.transposed()


class TransMatrixEdit(QtWidgets.QLineEdit):
    """
    Custom QLineEdit for matrix cell editing with validation and color feedback.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editingFinished.connect(self.style_cell)
        self.textChanged.connect(self.validate_cell)

    def validate_cell(self):
        """Validate the cell input. Values must be integers between -3 and 3, or empty."""
        text = self.text().strip()
        if text == "" or text == "-":
            # Allow empty input
            return
        try:
            value = int(text)
            if value < -3 or value > 3:
                raise ValueError
        except ValueError:
            # Invalid input: reset to empty
            self.setText("")

    def style_cell(self):
        """
        Validates the cell input and updates the background color accordingly.
        """
        text = self.text().strip()
        # Reset style for empty input
        if text == "":
            self.setText("")
            self.setStyleSheet(DEFAULT_CELL_STYLE)
            return

        try:
            value = int(text)
            if value < -3 or value > 3:
                raise ValueError
            color = IMPACT_MATRIX_COLORS.get(value, {}).get("color", "white")
            self.setStyleSheet(
                f"QLineEdit {{background: {color};}} "
                f"QLineEdit:hover {{border: 1px solid gray; background: {color};}}"
            )
        except ValueError:
            # Invalid input: reset to empty and default style
            self.setText("")
            self.setStyleSheet(DEFAULT_CELL_STYLE)

    def focusInEvent(self, event):
        """
        Selects all text when the widget gains focus.
        """
        super().focusInEvent(event)
        self.selectAll()


class NcsPwlImpactManagerDialog(QtWidgets.QDialog, WidgetUi):
    """Dialog for managing matrix of relative impact of priority weighting layers and NCS pathways."""

    MINIMUM_RATING_VALUE = -3
    MAXIMUM_RATING_VALUE = 3

    # If there are equal to less than this value rows than the row height will be decreased
    RESIZE_NUM_ROWS = 5
    # This is the minimum row height value. 40 is the cell font minimum
    MINIMUM_ROW_HEIGHT = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        QgsGui.enableAutoGeometryRestore(self)

        self._message_bar = QgsMessageBar()
        self.vl_notification.addWidget(self._message_bar)

        # Initialize UI
        help_icon = FileUtils.get_icon("mActionHelpContents_green.svg")
        self.btn_help.setIcon(help_icon)

        btn_save = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        btn_save.setText(tr("Save"))
        btn_save.setAutoDefault(False)
        btn_save.setDefault(False)
        btn_save.clicked.connect(self._on_accepted)

        btn_reset = self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset)
        btn_reset.setText(tr("Reset Matrix"))
        btn_reset.setAutoDefault(False)
        btn_reset.setDefault(False)
        btn_reset.clicked.connect(self.reset_matrix_values)

        # Current selected NCS pathway identifier
        self._current_pathway_identifier: str = None

        icon_pixmap = QtGui.QPixmap(ICON_PATH)
        self.icon_la.setPixmap(icon_pixmap)
        self.btn_help.clicked.connect(self.open_help)

        # Set up table for land cover transitions
        label_ncs_pathways = VerticalLabel(self)
        label_ncs_pathways.setText(self.tr("NCS Pathways"))
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_pwls.sizePolicy().hasHeightForWidth())
        label_ncs_pathways.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        label_ncs_pathways.setFont(font)
        self.matrix_table_layout.addWidget(
            label_ncs_pathways, 1, 0, 1, 1, QtCore.Qt.AlignCenter
        )

        # Set up the matrix
        self.setup_matrix_table()

        self.restore_matrix_values()

        # Sets the LC table height based on the row height
        table_header = self.rel_impact_matrix.horizontalHeader()
        header_height = table_header.height()

        table_row_cnt = self.rel_impact_matrix.rowCount()

        # There will always be atleast one class
        table_row_height = self.rel_impact_matrix.rowHeight(0)

        # Table height with 5 added as an additional precaution to
        # avoid the addition of a scroll bar
        table_height = (table_row_height * table_row_cnt) + header_height + 5
        self.rel_impact_matrix.setFixedHeight(table_height)

        # Set up legend
        self.setup_legend()

    def setup_matrix_table(self) -> None:
        """
        Sets up the matrix QTableWidget with editable cells for each pathway/PWL pair.
        """
        pathways: typing.List[NcsPathway] = settings_manager.get_all_ncs_pathways()
        priority_layers: typing.List = [
            pwl
            for pwl in settings_manager.get_priority_layers()
            if pwl.get("type") == PriorityLayerType.DEFAULT.value
        ]

        num_pathways = len(pathways)
        num_priority_layers = len(priority_layers)
        self.rel_impact_matrix.setRowCount(num_pathways)
        self.rel_impact_matrix.setColumnCount(num_priority_layers)

        # Set header labels
        pathway_names = [pathway.name for pathway in pathways]
        priority_layer_names = [pwl["name"] for pwl in priority_layers]

        self.rel_impact_matrix.setHorizontalHeaderLabels(priority_layer_names)
        self.rel_impact_matrix.setVerticalHeaderLabels(pathway_names)

        # Use rotated headers for large matrices for better readability
        if num_pathways > 15:
            rotated_header = RotatedHeaderView(
                QtCore.Qt.Horizontal, self.rel_impact_matrix
            )
            self.rel_impact_matrix.setHorizontalHeader(rotated_header)

        # Populate each cell with a validated TransMatrixEdit widget
        for row in range(num_pathways):
            for col in range(num_priority_layers):
                line_edit = TransMatrixEdit()
                line_edit.setAlignment(QtCore.Qt.AlignHCenter)
                line_edit.setToolTip(
                    f"""
                    Pathway: {pathways[row].name},
                    <br>PWL: {priority_layers[col]["name"]}
                    """
                )
                self.rel_impact_matrix.setCellWidget(row, col, line_edit)

        # Style the table and headers for better appearance
        self.rel_impact_matrix.setStyleSheet("QTableWidget {border: 0px;}")
        self.rel_impact_matrix.horizontalHeader().setStyleSheet(
            "QHeaderView::section {padding-top: 5px; padding-bottom: 5px;}"
        )
        self.rel_impact_matrix.verticalHeader().setStyleSheet(
            "QHeaderView::section {padding-left: 10px; padding-right: 5px;}"
        )
        self.rel_impact_matrix.setStyleSheet("QTableWidget::item {padding: 1px;}")

        # Stretch horizontal header sections to fill available width
        for col in range(num_priority_layers):
            self.rel_impact_matrix.horizontalHeader().setSectionResizeMode(
                col, QtWidgets.QHeaderView.Stretch
            )

        # Adjust row heights based on the number of pathways
        for row in range(num_pathways):
            if num_pathways <= self.RESIZE_NUM_ROWS:
                # For small matrices, use a fixed minimum row height
                self.rel_impact_matrix.verticalHeader().setSectionResizeMode(
                    row, QtWidgets.QHeaderView.Fixed
                )
                self.rel_impact_matrix.verticalHeader().resizeSection(
                    row, self.MINIMUM_ROW_HEIGHT
                )
            else:
                # For larger matrices, stretch rows to fill the table
                self.rel_impact_matrix.verticalHeader().setSectionResizeMode(
                    row, QtWidgets.QHeaderView.Stretch
                )

    def restore_matrix_values(self) -> None:
        """
        Restores the matrix values from the saved impact matrix.
        """
        pathways = settings_manager.get_all_ncs_pathways()
        priority_layers = settings_manager.get_priority_layers()

        impact_matrix = settings_manager.get_value(
            Settings.SCENARIO_IMPACT_MATRIX, dict()
        )

        try:
            if not impact_matrix:
                return

            impact_matrix_dict = json.loads(impact_matrix)
            impact_pathway_uuids = impact_matrix_dict.get("pathway_uuids", [])
            impact_priority_layer_uuids = impact_matrix_dict.get(
                "priority_layer_uuids", []
            )
            impact_matrix_values = impact_matrix_dict.get("values", [])

            for row, pathway in enumerate(pathways):
                pathway_uuid = str(pathway.uuid)
                if pathway_uuid not in impact_pathway_uuids:
                    continue
                matrix_row = impact_pathway_uuids.index(pathway_uuid)

                for col, pwl in enumerate(priority_layers):
                    pwl_uuid = str(pwl["uuid"])
                    if pwl_uuid not in impact_priority_layer_uuids:
                        continue

                    # Skip constant raster PWLs as they are used in investability analysis only
                    if pwl.get("type") != PriorityLayerType.DEFAULT.value:
                        continue

                    matrix_col = impact_priority_layer_uuids.index(pwl_uuid)

                    # Validate indices
                    if matrix_row >= len(impact_matrix_values) or matrix_col >= len(
                        impact_matrix_values[matrix_row]
                    ):
                        continue

                    value = impact_matrix_values[matrix_row][matrix_col]
                    cell_widget = self.rel_impact_matrix.cellWidget(row, col)
                    if isinstance(cell_widget, TransMatrixEdit):
                        if value is None:
                            cell_widget.setText("")
                            cell_widget.setStyleSheet(DEFAULT_CELL_STYLE)
                        else:
                            cell_widget.setText(str(value))
                            color = IMPACT_MATRIX_COLORS.get(value, {}).get(
                                "color", "white"
                            )
                            cell_widget.setStyleSheet(
                                f"QLineEdit {{background: {color};}} "
                                f"QLineEdit:hover {{border: 1px solid gray; background: {color};}}"
                            )
        except Exception as e:
            error_tr = tr(f"Error restoring matrix values: {e}")
            self.show_message(error_tr, Qgis.MessageLevel.Warning)
            log(error_tr)

    def get_impact_matrix(self) -> typing.Dict:
        """
        Retrieves the current values from the matrix
        mapping pathway uuids, priority layer uuids and their corresponding ratings.
        Rows -> pathways, Columns -> priority layers

        :return: Dictionary mapping pathway, PWL  and ratings.
        :rtype: typing.Dict
        """
        pathways = settings_manager.get_all_ncs_pathways()
        priority_layers = settings_manager.get_priority_layers()
        matrix_values = self.get_matrix_values()

        return {
            "pathway_uuids": [str(pathway.uuid) for pathway in pathways],
            "priority_layer_uuids": [
                str(pwl.get("uuid"))
                for pwl in priority_layers
                if pwl.get("type") == PriorityLayerType.DEFAULT.value
            ],
            "values": matrix_values,
        }

    def get_matrix_values(self) -> typing.List[typing.List[int]]:
        """
        Retrieves the current values from the matrix as a 2D list of integers.

        :return: 2D list representing the matrix values.
        :rtype: typing.List[typing.List[int]]
        """
        num_rows = self.rel_impact_matrix.rowCount()
        num_cols = self.rel_impact_matrix.columnCount()
        matrix_values = []

        for row in range(num_rows):
            row_values = []
            for col in range(num_cols):
                cell_widget = self.rel_impact_matrix.cellWidget(row, col)
                if isinstance(cell_widget, TransMatrixEdit):
                    text = cell_widget.text().strip()
                    if text == "":
                        row_values.append(None)
                    else:
                        try:
                            value = int(text)
                            row_values.append(value)
                        except ValueError:
                            row_values.append(None)
                else:
                    row_values.append(0)
            matrix_values.append(row_values)
        return matrix_values

    def reset_matrix_values(self):
        """Resets the matrix values."""
        reply = QtWidgets.QMessageBox.question(
            self,
            self.tr("Reset Matrix Table"),
            self.tr(
                "Are you sure you want to reset the matrix table? All changes will be lost."
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            num_rows = self.rel_impact_matrix.rowCount()
            num_cols = self.rel_impact_matrix.columnCount()
            for row in range(num_rows):
                for col in range(num_cols):
                    cell_widget = self.rel_impact_matrix.cellWidget(row, col)
                    if isinstance(cell_widget, TransMatrixEdit):
                        cell_widget.setText("")
                        cell_widget.setStyleSheet(DEFAULT_CELL_STYLE)
            settings_manager.set_value(
                Settings.SCENARIO_IMPACT_MATRIX, json.dumps(self.get_impact_matrix())
            )

    def setup_legend(self):
        """Sets up the legend for the relative impact ratings."""
        idx = 0
        for rating, color in IMPACT_MATRIX_COLORS.items():
            self.gridLayoutLegend.addWidget(
                QtWidgets.QLabel(color["impact"]), 0, idx, QtCore.Qt.AlignCenter
            )

            legend_text = QtWidgets.QLineEdit()
            legend_text.setReadOnly(True)
            legend_text.setText(str(rating))
            legend_text.setStyleSheet(
                "QLineEdit {background: "
                + color["color"]
                + "; border: "
                + color["color"]
                + ";}"
            )
            legend_text.setToolTip(f"Rating: {rating}, Impact {color['impact']}")
            legend_text.setAlignment(QtCore.Qt.AlignHCenter)
            legend_text.setMinimumWidth(100)
            legend_text.setMinimumHeight(30)

            font = QtGui.QFont()
            font.setBold(True)
            font.setWeight(60)
            legend_text.setFont(font)

            sizePolicy = QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
            )
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(0)
            legend_text.setSizePolicy(sizePolicy)

            self.gridLayoutLegend.addWidget(legend_text, 1, idx, QtCore.Qt.AlignCenter)

            idx += 1

    def open_help(self, activated: bool):
        """Opens the user documentation for the plugin in a browser."""
        open_documentation(USER_DOCUMENTATION_SITE)

    def _show_warning_message(self, message: str):
        """Shows a warning message in the message bar.

        :param message: Message to show in the message bar.
        :type message: str
        """
        self._message_bar.pushMessage(message, Qgis.MessageLevel.Warning)

    def _on_accepted(self):
        """Validates user input before closing."""
        settings_manager.set_value(
            Settings.SCENARIO_IMPACT_MATRIX, json.dumps(self.get_impact_matrix())
        )
        self.accept()

    def show_message(self, message, level=Qgis.Info, duration: int = 0):
        """Shows message on the main widget message bar.

        :param message: Text message
        :type message: str

        :param level: Message level type
        :type level: Qgis.MessageLevel

        :param duration: Duration of the shown message
        :type level: int
        """
        self.message_bar.clearWidgets()
        self.message_bar.pushMessage(message, level=level, duration=duration)
