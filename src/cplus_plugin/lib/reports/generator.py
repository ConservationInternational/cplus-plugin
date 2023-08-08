# -*- coding: utf-8 -*-
"""
CPLUS Report generator.
"""
import os
from pathlib import Path
import traceback
import typing

from qgis.core import (
    Qgis,
    QgsBasicNumericFormat,
    QgsFeedback,
    QgsFillSymbol,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemManualTable,
    QgsLayoutItemMap,
    QgsLayoutItemPage,
    QgsLayoutItemPicture,
    QgsLayoutItemShape,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsTask,
    QgsTableCell,
    QgsTextFormat,
)
from qgis.utils import iface

from qgis.PyQt import QtCore, QtGui, QtXml

from ...definitions.defaults import (
    IMPLEMENTATION_MODEL_AREA_TABLE_ID,
    MINIMUM_ITEM_HEIGHT,
    MINIMUM_ITEM_WIDTH,
    PRIORITY_GROUP_WEIGHT_TABLE_ID,
)
from .layout_items import CplusMapRepeatItem
from ...models.base import ImplementationModel
from ...models.helpers import extent_to_project_crs_extent
from ...models.report import ReportContext, ReportResult
from ...utils import calculate_raster_value_area, get_report_font, log, tr
from .variables import create_bulleted_text, LayoutVariableRegister


class ReportGeneratorTask(QgsTask):
    """Proxy class for initiating the report generation process."""

    def __init__(self, description: str, context: ReportContext):
        super().__init__(description)
        self._context = context
        self._result = None
        self._generator = ReportGenerator(self._context, self._context.feedback)

    @property
    def context(self) -> ReportContext:
        """Returns the report context used by the generator.

        :returns: Report context object used by the generator.
        :rtype: ReportContext
        """
        return self._context

    @property
    def result(self) -> ReportResult:
        """Returns the result object which contains information
        on whether the process succeeded or failed.

        :returns: The result of the report generation process.
        :rtype: ReportResult
        """
        return self._result

    def cancel(self):
        """Cancel the report generation task."""
        super().cancel()

    def run(self) -> bool:
        """Initiates the report generation process and returns
        a result indicating whether the process succeeded or
        failed.

        :returns: True if the report generation process succeeded
        or False it if failed.
        :rtype: bool
        """
        if self.isCanceled():
            return False

        if self._context.project_file:
            self._result = self._generator.run()
        else:
            msg = tr("Unable to serialize current project for " "report generation.")
            msgs: typing.List[str] = [msg]
            self._result = ReportResult(
                False, self._context.scenario.uuid, "", tuple(msgs)
            )

        return self._result.success

    def _zoom_map_items_to_current_extents(self, layout: QgsPrintLayout):
        """Zoom extents of map items in the layout to current map canvas
        extents.
        """
        extent = iface.mapCanvas().mapSettings().visibleExtent()
        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                item.zoomToExtent(extent)

    def finished(self, result: bool):
        """If successful, add the layout to the project.

        :param result: Flag indicating if the result of the
        report generation process. True if successful,
        else False.
        :type result: bool
        """
        if result:
            log(
                f"Successfully generated the report for "
                f"{self._context.scenario.name} scenario."
            )

            layout_path = self._generator.output_layout_path
            if not layout_path:
                log("Output layout could not be saved.", info=False)
                return

            project = QgsProject.instance()
            layout = _load_layout_from_file(layout_path, project)
            if layout is None:
                log("Could not load layout from file.", info=False)
                return

            # Zoom the extents of map items in the layout
            self._zoom_map_items_to_current_extents(layout)
            project.layoutManager().addLayout(layout)

        else:
            log(
                f"Error occurred when generating the "
                f"report for {self._context.scenario.name} "
                f"scenario. See details below:",
                info=False,
            )
            for err in self._result.messages:
                err_msg = f"{self._context.scenario.name} - {err}"
                log(err_msg, info=False)


class ReportGenerator:
    """Generator for CPLUS reports."""

    def __init__(self, context: ReportContext, feedback: QgsFeedback = None):
        self._context = context
        self._feedback = feedback
        self._error_messages: typing.List[str] = []
        self._layout = None
        self._project = None
        self._variable_register = LayoutVariableRegister()
        self._report_output_dir = ""
        self._output_layout_path = ""
        self._repeat_page = None
        self._repeat_page_num = -1
        self._repeat_item = None
        self._normalized_scenario_extent = None

    @property
    def context(self) -> ReportContext:
        """Returns the report context used by the generator.

        :returns: Report context object used by the generator.
        :rtype: ReportContext
        """
        return self._context

    @property
    def feedback(self) -> QgsFeedback:
        """Returns the feedback object for process update and cancellation.

        :returns: Feedback object or None if not specified.
        :rtype: QgsFeedback
        """
        return self._feedback

    @property
    def layout(self) -> QgsPrintLayout:
        """Returns the layout object used to generate the report.

        :returns: The layout object used to generate the report
        or None if the process was not successful.
        :rtype: QgsPrintLayout
        """
        return self._layout

    @property
    def output_layout_path(self) -> str:
        """Absolute path to a temporary file containing the
        layout as a QPT file.

        When this object is used within a QgsTask, it is
        recommended to use this layout path to reconstruct
        the layout rather calling the `layout` attribute since
        it was created in a separate thread.

        :returns: Path to the layout template file.
        :rtype: str
        """
        return self._output_layout_path

    @property
    def repeat_page(self) -> typing.Union[QgsLayoutItemPage, None]:
        """Returns the page item that will be repeated based on the
        number of implementation models in the scenario.

        A repeat page is a layout page item that contains the
        first instance of a CplusMapRepeatItem.

        :returns: Page item containing a CplusMapRepeatItem or None
        if not found.
        :rtype: QgsLayoutItemPage
        """
        return self._repeat_page

    def _process_cancelled(self) -> bool:
        """Check if there is a request to cancel the process
        if a feedback object had been specified.
        """
        if self._feedback and self._feedback.isCanceled():
            tr_msg = tr("Report generation cancelled.")
            self._error_messages.append(tr_msg)
            return True

        return False

    def _set_project(self):
        """Deserialize the project from the report context."""
        if not self._context.project_file:
            tr_msg = tr("Project file not specified.")
            self._error_messages.append(tr_msg)
            return

        else:
            if not os.access(self._context.project_file, os.R_OK):
                tr_msg = tr(
                    "Current user does not have permission to read the project file."
                )
                self._error_messages.append(tr_msg)
                return

            p = Path(self._context.project_file)
            if not p.exists():
                tr_msg = tr("Project file does not exist")
                self._error_messages.append(f"{tr_msg} {self._context.project_file}.")
                return

        project = QgsProject()
        result = project.read(self._context.project_file)
        if not result:
            tr_msg = tr("Unable to read the project file")
            self._error_messages.append(f"{tr_msg} {self._context.project_file}.")
            return

        # Set project metadata which will be cascaded to the PDF document
        metadata = project.metadata()
        metadata.setTitle(self._context.scenario.name)
        metadata.setAuthor("CPLUS plugin")
        metadata.setAbstract(self._context.scenario.description)
        metadata.setCreationDateTime(QtCore.QDateTime.currentDateTime())
        project.setMetadata(metadata)

        self._project = project

    @property
    def output_dir(self) -> str:
        """Creates, if it does not exist, the output directory
        where the analysis reports will be saved. This is relative
        to the base directory and outputs sub-folder.

        :returns: Output directory where the analysis reports
        will be saved.
        :rtype: str
        """
        output_dir = f"{self._context.scenario_output_dir}/reports"

        # Create reports directory
        if not self._report_output_dir:
            p = Path(output_dir)
            if not p.exists():
                try:
                    p.mkdir()
                except FileNotFoundError:
                    tr_msg = (
                        "Missing parent directory when creating "
                        "reports subdirectory."
                    )
                    self._error_messages.append(tr_msg)
                    return ""

        self._report_output_dir = output_dir

        return self._report_output_dir

    def _set_repeat_page(self):
        """Check if the layout has a map repeat item and set
        the corresponding page item containing the map repeat item
        or leave it as None if not found.

        Current implementation only supports one repeat item.
        """
        if self._layout is None:
            return

        items = self._layout.items()
        for item in items:
            if isinstance(item, CplusMapRepeatItem):
                page_num = item.page()
                self._repeat_page = self._layout.pageCollection().page(page_num)
                self._repeat_page_num = page_num
                self._repeat_item = item

    def _set_scenario_extent(self) -> bool:
        """Set scenario extent."""
        extent = extent_to_project_crs_extent(
            self._context.scenario.extent, self._project
        )

        if extent is None:
            tr_msg = tr("Could not get the scenario extent as a QgsRectangle.")
            self._error_messages.append(tr_msg)
            return False

        self._normalized_scenario_extent = extent

        return True

    def duplicate_repeat_page(self, position: int) -> bool:
        """Duplicates the repeat page and adds it to the layout
        at the given position.

        :param position: Zero-based position to insert the duplicated page. If
        the position is greater than the number of pages, then the
        duplicated page will be inserted at the end of the layout.
        :type position: int

        :returns: True if the page was successfully duplicated else False.
        :rtype: bool
        """
        if self._repeat_page is None:
            return False

        if self._layout is None:
            return False

        if self._repeat_page_num == -1:
            tr_msg = "Repeat page not found in page collection"
            self._error_messages.append(tr_msg)
            return False

        new_page = QgsLayoutItemPage(self._layout)
        new_page.attemptResize(self._repeat_page.sizeWithUnits())
        new_page.setPageStyleSymbol(self._repeat_page.pageStyleSymbol().clone())

        # Insert empty repeat page at the given position
        if position < self._layout.pageCollection().pageCount():
            self._layout.pageCollection().insertPage(new_page, position)
        else:
            # Add at the end
            position = self._layout.pageCollection().pageCount()
            self._layout.pageCollection().addPage(new_page)

        doc = QtXml.QDomDocument()
        el = doc.createElement("CopyItems")
        ctx = QgsReadWriteContext()
        repeat_page_items = self._layout.pageCollection().itemsOnPage(
            self._repeat_page_num
        )
        for item in repeat_page_items:
            item.writeXml(el, doc, ctx)
            doc.appendChild(el)

        # Clear element identifier references
        nodes = doc.elementsByTagName("LayoutItem")
        for n in range(nodes.count()):
            node = nodes.at(n)
            if node.isElement():
                node.toElement().removeAttribute("uuid")

        page_ref_point = self._layout.pageCollection().pagePositionToLayoutPosition(
            position, QgsLayoutPoint(0, 0)
        )
        _ = self._layout.addItemsFromXml(el, doc, ctx, page_ref_point, True)

        return True

    def _render_repeat_items(self):
        """Render implementation models in the layout based on the
        scenario result.
        """
        if self._repeat_item is None:
            tr_msg = tr(
                "Unable to render implementation models as no repeat " "item was found."
            )
            self._error_messages.append(tr_msg)
            return

        if MINIMUM_ITEM_HEIGHT <= 0 or MINIMUM_ITEM_WIDTH <= 0:
            tr_msg = tr("Minimum repeat item dimensions cannot be used.")
            self._error_messages.append(tr_msg)
            return

        repeat_size = self._repeat_item.sizeWithUnits()
        repeat_width = repeat_size.width()
        repeat_height = repeat_size.height()

        repeat_ref_point = self._repeat_item.pagePositionWithUnits()
        repeat_ref_x = repeat_ref_point.x()
        repeat_ref_y = repeat_ref_point.y()

        # Determine number of columns
        num_cols = -1
        adjusted_item_width = MINIMUM_ITEM_WIDTH
        if repeat_width < MINIMUM_ITEM_WIDTH:
            tr_msg = tr(
                "Repeat item width is too small to render the " "implementation models."
            )
            self._error_messages.append(tr_msg)
            return
        else:
            num_cols = int(repeat_width // MINIMUM_ITEM_WIDTH)
            bleed_item_width = (
                repeat_width - (num_cols * MINIMUM_ITEM_WIDTH)
            ) / num_cols
            adjusted_item_width = MINIMUM_ITEM_WIDTH + bleed_item_width

        # Determine number of rows
        num_rows = -1
        adjusted_item_height = MINIMUM_ITEM_HEIGHT
        if repeat_height < MINIMUM_ITEM_HEIGHT:
            tr_msg = tr(
                "Repeat item height is too small to render the "
                "implementation models."
            )
            self._error_messages.append(tr_msg)
            return
        else:
            num_rows = int(repeat_height // MINIMUM_ITEM_HEIGHT)
            bleed_item_height = (
                repeat_height - (num_rows * MINIMUM_ITEM_HEIGHT)
            ) / num_cols
            adjusted_item_height = MINIMUM_ITEM_HEIGHT + bleed_item_height

        max_items_page = num_rows * num_cols

        # Temporary for testing
        num_implementation_models = len(self._context.scenario.models)

        if num_implementation_models == 0:
            tr_msg = "No implementation models in the scenario"
            self._error_messages.append(tr_msg)
            return

        # Calculate number of pages required
        num_pages, req_pages = divmod(num_implementation_models, int(max_items_page))
        if num_pages == 0:
            num_pages = 1

        # Check if there is an additional page required
        if req_pages != 0:
            num_pages += 1

        # First create the additional required pages for the
        # report so that we don't also duplicate the groups
        # in the repeat page when adding the IMs. Not the
        # most efficient but should suffice.
        for p in range(1, num_pages):
            page_pos = self._repeat_page_num + p
            _ = self.duplicate_repeat_page(page_pos)

        # Now, add IMs to the pages
        im_count = 0
        for p in range(num_pages):
            page_pos = self._repeat_page_num + p
            for r in range(num_rows):
                reference_y_pos = repeat_ref_y + (r * adjusted_item_height)
                for c in range(num_cols):
                    if im_count == num_implementation_models:
                        break

                    imp_model = self._context.scenario.models[im_count]
                    reference_x_pos = repeat_ref_x + (c * adjusted_item_width)
                    self._add_implementation_model_items(
                        reference_x_pos,
                        reference_y_pos,
                        adjusted_item_width,
                        adjusted_item_height,
                        page_pos,
                        imp_model,
                    )
                    im_count += 1

        # Hide repeat item frame
        for p in range(self._layout.pageCollection().pageCount()):
            items = self._layout.pageCollection().itemsOnPage(p)
            for item in items:
                if isinstance(item, CplusMapRepeatItem):
                    item.setFrameEnabled(False)

    def _add_implementation_model_items(
        self,
        pos_x: float,
        pos_y: float,
        width: float,
        height: float,
        page: int,
        imp_model: ImplementationModel,
    ):
        """Add a group item with map, labels etc. to the layout for the
        given IM.
        """
        # Map
        map_height = 0.8 * height
        im_map = QgsLayoutItemMap(self._layout)
        self._layout.addLayoutItem(im_map)
        im_map.setFrameEnabled(False)
        im_map.zoomToExtent(self._normalized_scenario_extent)
        if imp_model.layer is not None:
            im_map.setLayers([imp_model.layer])
        map_ref_point = QgsLayoutPoint(pos_x, pos_y, self._layout.units())
        im_map.attemptMove(map_ref_point, True, False, page)
        im_map.attemptResize(QgsLayoutSize(width, map_height, self._layout.units()))

        # Background IM details shape
        shape_height = 0.2 * height
        im_shape = QgsLayoutItemShape(self._layout)
        self._layout.addLayoutItem(im_shape)
        im_shape.setShapeType(QgsLayoutItemShape.Shape.Rectangle)
        shape_ref_point = QgsLayoutPoint(
            pos_x, pos_y + map_height, self._layout.units()
        )
        im_shape.attemptMove(shape_ref_point, True, False, page)
        im_shape.attemptResize(QgsLayoutSize(width, shape_height, self._layout.units()))
        symbol_props = {
            "color": "#b2df8a",
            "style": "solid",
            "outline_style": "no",
            "line_color": "#000000",
            "outline_width": "0",
        }
        symbol = QgsFillSymbol.createSimple(symbol_props)
        im_shape.setSymbol(symbol)

        # North arrow
        arrow_item = QgsLayoutItemPicture(self._layout)
        self._layout.addLayoutItem(arrow_item)
        arrow_item.setPicturePath(
            ":/images/north_arrows/layout_default_north_arrow.svg"
        )
        arrow_ref_point = QgsLayoutPoint(
            pos_x + 0.02 * width,
            pos_y + map_height - (0.1 * height),
            self._layout.units(),
        )
        arrow_item.attemptMove(arrow_ref_point, True, False, page)
        arrow_item.attemptResize(
            QgsLayoutSize(0.07 * width, 0.07 * height, self._layout.units())
        )

        title_font_size = 10
        description_font_size = 7

        # IM name label
        margin = 0.01 * width
        label_width = (width - (2 * margin)) / 2
        name_label_height = 0.15 * shape_height
        im_name_lbl = QgsLayoutItemLabel(self._layout)
        self._layout.addLayoutItem(im_name_lbl)
        im_name_lbl.setText(imp_model.name)
        self.set_label_font(im_name_lbl, title_font_size)
        name_lbl_ref_point = QgsLayoutPoint(
            pos_x + margin, pos_y + map_height + margin, self._layout.units()
        )
        im_name_lbl.attemptMove(name_lbl_ref_point, True, False, page)
        im_name_lbl.attemptResize(
            QgsLayoutSize(label_width, name_label_height, self._layout.units())
        )

        # IM description label
        desc_label_height = 0.85 * shape_height - (margin * 2)
        im_desc_lbl = QgsLayoutItemLabel(self._layout)
        self._layout.addLayoutItem(im_desc_lbl)
        im_desc_lbl.setText(imp_model.description)
        self.set_label_font(im_desc_lbl, description_font_size)
        desc_lbl_ref_point = QgsLayoutPoint(
            pos_x + margin,
            pos_y + map_height + name_label_height + margin * 2,
            self._layout.units(),
        )
        im_desc_lbl.attemptMove(desc_lbl_ref_point, True, False, page)
        im_desc_lbl.attemptResize(
            QgsLayoutSize(label_width, desc_label_height, self._layout.units())
        )

        # NCS Pathway label
        pathway_lbl_height = 0.15 * shape_height
        ncs_name_lbl = QgsLayoutItemLabel(self._layout)
        self._layout.addLayoutItem(ncs_name_lbl)
        ncs_name_lbl.setText(tr("NCS Pathways"))
        self.set_label_font(ncs_name_lbl, title_font_size)
        ncs_lbl_ref_point = QgsLayoutPoint(
            pos_x + label_width + 2 * margin,
            pos_y + map_height + margin,
            self._layout.units(),
        )
        ncs_name_lbl.attemptMove(ncs_lbl_ref_point, True, False, page)
        ncs_name_lbl.attemptResize(
            QgsLayoutSize(label_width, pathway_lbl_height, self._layout.units())
        )

        # NCS Pathways for IM label
        if len(imp_model.pathways) == 0:
            ncs_txt = tr("No NCS pathways in the implementation model")
        else:
            ncs_names = [ncs.name for ncs in imp_model.pathways]
            ncs_txt = create_bulleted_text("", ncs_names)

        im_pathways_lbl_height = 0.85 * shape_height - (margin * 2)
        im_ncs_desc_lbl = QgsLayoutItemLabel(self._layout)
        self._layout.addLayoutItem(im_ncs_desc_lbl)
        im_ncs_desc_lbl.setText(ncs_txt)
        self.set_label_font(im_ncs_desc_lbl, description_font_size)
        im_ncs_lbl_ref_point = QgsLayoutPoint(
            pos_x + label_width + 2 * margin,
            pos_y + map_height + pathway_lbl_height + margin * 2,
            self._layout.units(),
        )
        im_ncs_desc_lbl.attemptMove(im_ncs_lbl_ref_point, True, False, page)
        im_ncs_desc_lbl.attemptResize(
            QgsLayoutSize(label_width, im_pathways_lbl_height, self._layout.units())
        )

    @classmethod
    def set_label_font(
        cls,
        label: QgsLayoutItemLabel,
        size: int,
        bold: bool = False,
        italic: bool = False,
    ):
        """Set font properties of the given layout label item.

        :param label: Label item whose font properties will
        be updated.
        :type label: QgsLayoutItemLabel

        :param size: Point size of the font.
        :type size: int

        :param bold: True if font is to be bold, else
        False (default).
        :type bold: bool

        :param italic: True if font is to be in italics, else
        False (default).
        :type italic: bool
        """
        font = get_report_font(size, bold, italic)
        version = Qgis.versionInt()
        if version < 32400:
            label.setFont(font)
        else:
            txt_format = QgsTextFormat()
            txt_format.setFont(font)
            txt_format.setSize(size)
            txt_format.setSizeUnit(Qgis.RenderUnit.Points)
            label.setTextFormat(txt_format)

        label.refresh()

    def _update_map_extents(self):
        """Update the extent of all map items in the layout."""
        if self._normalized_scenario_extent is None:
            return

        items = self._layout.items()
        for item in items:
            if isinstance(item, QgsLayoutItemMap):
                item.zoomToExtent(self._normalized_scenario_extent)

    def _get_table_from_id(
        self, table_id: str
    ) -> typing.Union[QgsLayoutItemManualTable, None]:
        """Get the table object from the corresponding item id or return None if the table was not found."""
        table_frame = self._layout.itemById(table_id)
        if table_frame is None:
            return None

        return table_frame.multiFrame()

    def _populate_im_area_table(self):
        """Populate the table(s) for implementation models and
        corresponding areas.
        """
        parent_table = self._get_table_from_id(IMPLEMENTATION_MODEL_AREA_TABLE_ID)
        if parent_table is None:
            tr_msg = tr(
                "Could not find parent table for areas of implementation models."
            )
            self._error_messages.append(tr_msg)
            return

        rows_data = []
        for imp_model in self._context.scenario.models:
            name_cell = QgsTableCell(imp_model.name)
            name_cell.setBackgroundColor(QtGui.QColor("#e9e9e9"))
            layer = imp_model.layer
            if layer is None:
                area_info = tr("No area <Error in layer>")
            else:
                area_info = calculate_raster_value_area(layer)
                if area_info == -1:
                    area_info = tr("An error occurred when computing the area.")
            area_cell = QgsTableCell(area_info)
            number_format = QgsBasicNumericFormat()
            number_format.setThousandsSeparator(",")
            number_format.setNumberDecimalPlaces(2)
            area_cell.setNumericFormat(number_format)
            rows_data.append([name_cell, area_cell])

        parent_table.setTableContents(rows_data)

    def _populate_scenario_weighting_values(self):
        """Populate table with weighting values for priority layer groups."""
        parent_table = self._get_table_from_id(PRIORITY_GROUP_WEIGHT_TABLE_ID)
        if parent_table is None:
            tr_msg = tr("Could not find parent table for priority weighting values.")
            self._error_messages.append(tr_msg)
            return

        rows_data = []
        for priority_group in self._context.scenario.priority_layer_groups:
            if "name" not in priority_group or "value" not in priority_group:
                continue
            name_cell = QgsTableCell(priority_group["name"])
            value_cell = QgsTableCell(priority_group["value"])
            rows_data.append([name_cell, value_cell])

        parent_table.setTableContents(rows_data)

    def run(self) -> ReportResult:
        """Initiates the report generation process and returns
        a result which contains information on whether the
        process succeeded or failed.

        :returns: The result of the report generation process.
        :rtype: ReportResult
        """
        try:
            return self._run()
        except Exception as ex:
            # Last resort to capture general exceptions.
            exc_info = "".join(traceback.TracebackException.from_exception(ex).format())
            self._error_messages.append(exc_info)
            return self._get_failed_result()

    def _run(self) -> ReportResult:
        """Runs report generation process."""
        if self._process_cancelled():
            return self._get_failed_result()

        self._set_project()
        if self._project is None:
            return self._get_failed_result()

        if self._process_cancelled():
            return self._get_failed_result()

        if not self._load_template() or not self.output_dir:
            return self._get_failed_result()

        if self._process_cancelled():
            return self._get_failed_result()

        # Set the normalized scenario extent
        if not self._set_scenario_extent():
            return self._get_failed_result()

        if self._process_cancelled():
            return self._get_failed_result()

        # Update the extent of all map items in the layout
        self._update_map_extents()

        if self._process_cancelled():
            return self._get_failed_result()

        # Update variable values
        self._variable_register.update_variables(self.layout, self._context)

        if self._process_cancelled():
            return self._get_failed_result()

        # Set repeat page
        self._set_repeat_page()

        # Render repeat items i.e. implementation models
        self._render_repeat_items()

        if self._process_cancelled():
            return self._get_failed_result()

        # Populate implementation model area table
        self._populate_im_area_table()

        if self._process_cancelled():
            return self._get_failed_result()

        # Populate table with priority weighting values
        self._populate_scenario_weighting_values()

        # Add CPLUS report flag
        self._variable_register.set_report_flag(self._layout)

        if self._process_cancelled():
            return self._get_failed_result()

        self._export_to_pdf()

        result = self._save_layout_to_file()
        if not result:
            return self._get_failed_result()

        return ReportResult(
            True,
            self._context.scenario.uuid,
            self.output_dir,
            tuple(self._error_messages),
            self._context.name,
        )

    def _save_layout_to_file(self) -> bool:
        """Serialize the layout to a temporary file."""
        temp_layout_file = QtCore.QTemporaryFile()
        if not temp_layout_file.open():
            tr_msg = tr("Could not open temporary file to write the layout.")
            self._error_messages.append(tr_msg)
            return False

        file_name = temp_layout_file.fileName()
        self._output_layout_path = f"{file_name}.qpt"

        result = self._layout.saveAsTemplate(
            self._output_layout_path, QgsReadWriteContext()
        )
        if not result:
            tr_msg = tr("Could not save the layout template.")
            self._error_messages.append(tr_msg)
            return False

        return True

    def _get_failed_result(self) -> ReportResult:
        """Creates the report result object."""
        return ReportResult(
            False,
            self._context.scenario.uuid,
            self.output_dir,
            tuple(self._error_messages),
            self._context.name,
        )

    def _export_to_pdf(self) -> bool:
        """Exports the layout to a PDF file in the output
        directory using the layout name as the file name.
        """
        if self._layout is None or self._project is None or not self.output_dir:
            return False

        exporter = QgsLayoutExporter(self._layout)
        pdf_path = f"{self.output_dir}/{self._layout.name()}.pdf"
        result = exporter.exportToPdf(pdf_path, QgsLayoutExporter.PdfExportSettings())
        if result == QgsLayoutExporter.ExportResult.Success:
            return True
        else:
            tr_msg = tr("Could not export layout to PDF")
            self._error_messages.append(f"{tr_msg} {pdf_path}.")
            return False

    def _load_template(self) -> bool:
        """Loads the template in the report context and returns
        the corresponding layout object.

        :returns: True if the template was successfully loaded,
        else False.
        :rtype: bool
        """
        layout = _load_layout_from_file(
            self._context.template_path, self._project, self._error_messages
        )
        if layout is None:
            return False

        self._layout = layout
        self._variable_register.register_variables(self._layout)
        self._layout.setName(self._context.name)

        return True


def _load_layout_from_file(
    template_path: str, project: QgsProject, error_messages: list = None
) -> typing.Union[QgsPrintLayout, None]:
    """Util for loading layout templates from a file. It supports
    an optional argument for list to write error messages.
    """
    p = Path(template_path)
    if not p.exists():
        if error_messages:
            tr_msg = tr("Template file does not exist")
            error_messages.append(f"{tr_msg} {template_path}.")
        return None

    template_file = QtCore.QFile(template_path)
    doc = QtXml.QDomDocument()
    doc_status = True
    try:
        if not template_file.open(QtCore.QIODevice.ReadOnly):
            if error_messages:
                tr_msg = tr("Unable to read template file")
                error_messages.append(f"{tr_msg} {template_path}.")
            doc_status = False

        if doc_status:
            if not doc.setContent(template_file):
                if error_messages:
                    tr_msg = tr("Failed to parse template file contents")
                    error_messages.append(f"{tr_msg} {template_path}.")
                doc_status = False
    finally:
        template_file.close()

    if not doc_status:
        return None

    layout = QgsPrintLayout(project)
    _, load_status = layout.loadFromTemplate(doc, QgsReadWriteContext())
    if not load_status:
        if error_messages:
            tr_msg = tr("Could not load template from")
            error_messages.append(f"{tr_msg} {template_path}.")
        return None

    return layout
