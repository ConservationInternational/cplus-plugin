# -*- coding: utf-8 -*-
"""
CPLUS Report generator.
"""
from numbers import Number
import os
from pathlib import Path
import traceback
import typing

from qgis.core import (
    Qgis,
    QgsBasicNumericFormat,
    QgsFeedback,
    QgsFillSymbol,
    QgsLayerTreeNode,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemManualTable,
    QgsLayoutItemMap,
    QgsLayoutItemPage,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsMapLayerLegendUtils,
    QgsNumericFormatContext,
    QgsPrintLayout,
    QgsProcessingFeedback,
    QgsProject,
    QgsRasterLayer,
    QgsReadWriteContext,
    QgsLegendRenderer,
    QgsLegendStyle,
    QgsScaleBarSettings,
    QgsTask,
    QgsTableCell,
    QgsTextFormat,
    QgsUnitTypes,
)

from qgis.PyQt import QtCore, QtGui, QtXml

from ...definitions.constants import (
    ACTIVITY_GROUP_LAYER_NAME,
    ACTIVITY_WEIGHTED_GROUP_NAME,
    ACTIVITY_IDENTIFIER_PROPERTY,
)
from ...definitions.defaults import (
    ACTIVITY_AREA_TABLE_ID,
    MAX_ACTIVITY_DESCRIPTION_LENGTH,
    MAX_ACTIVITY_NAME_LENGTH,
    MINIMUM_ITEM_HEIGHT,
    MINIMUM_ITEM_WIDTH,
    PRIORITY_GROUP_WEIGHT_TABLE_ID,
)
from .layout_items import CplusMapRepeatItem
from ...models.base import Activity
from ...models.helpers import extent_to_project_crs_extent
from ...models.report import ReportContext, ReportResult
from ...utils import (
    calculate_raster_value_area,
    get_report_font,
    log,
    tr,
)
from .variables import create_bulleted_text, LayoutVariableRegister


class ReportGeneratorTask(QgsTask):
    """Proxy class for initiating the report generation process."""

    def __init__(self, description: str, context: ReportContext):
        super().__init__(description)
        self._context = context
        self._result = None
        self._generator = ReportGenerator(self._context, self._context.feedback)
        self.layout_manager = QgsProject.instance().layoutManager()
        self.layout_manager.layoutAdded.connect(self._on_layout_added)

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
        if self._context.feedback:
            self._context.feedback.cancel()

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
            msg = tr("Unable to serialize current project for report generation.")
            msgs: typing.List[str] = [msg]
            self._result = ReportResult(
                False, self._context.scenario.uuid, "", tuple(msgs)
            )

        return self._result.success

    def _zoom_map_items_to_current_extents(self, layout: QgsPrintLayout):
        """Zoom extents of map items in the layout to current map canvas
        extents.
        """
        scenario_extent = extent_to_project_crs_extent(
            self._context.scenario.extent, QgsProject.instance()
        )
        if scenario_extent is None:
            log("Cannot set extents for map items in the report.")
            return

        for item in layout.items():
            if isinstance(item, QgsLayoutItemMap):
                item.zoomToExtent(scenario_extent)

    def _on_layout_added(self, name: str):
        """Slot raised when a layout has been added to the manager."""
        self._export_to_pdf()

    def _export_to_pdf(self):
        """Export layout to PDF after the extents have been updated to
        the current canvas extents.
        """
        # We fetch the layout afresh so that the PDF export can contain
        # synced extents.
        layout_name = self._generator.layout.name()
        layout = self.layout_manager.layoutByName(layout_name)
        if layout is None:
            log(
                f"Could not find {layout_name} layout for exporting to PDF.", info=False
            )
            return

        # Set project metadata which will be cascaded to the PDF document
        project = QgsProject.instance()
        metadata = project.metadata()
        metadata.setTitle(self._context.scenario.name)
        metadata.setAuthor("CPLUS plugin")
        metadata.setAbstract(self._context.scenario.description)
        metadata.setCreationDateTime(QtCore.QDateTime.currentDateTime())
        project.setMetadata(metadata)

        exporter = QgsLayoutExporter(layout)
        pdf_path = f"{self._generator.output_dir}/{layout_name}.pdf"
        result = exporter.exportToPdf(pdf_path, QgsLayoutExporter.PdfExportSettings())
        if result != QgsLayoutExporter.ExportResult.Success:
            log(f"Could not export {layout_name} layout to PDF.", info=False)

    def finished(self, result: bool):
        """If successful, add the layout to the project.

        :param result: Flag indicating if the result of the
        report generation process. True if successful,
        else False.
        :type result: bool
        """
        if len(self._result.messages) > 0:
            log(
                f"Warnings and errors occurred when generating the "
                f"report for {self._context.scenario.name} "
                f"scenario. See details below:",
                info=False,
            )
            for err in self._result.messages:
                err_msg = f"{self._context.scenario.name} - {err}\n"
                log(err_msg, info=False)

        if result:
            log(
                f"Successfully generated the report for "
                f"{self._context.scenario.name} scenario."
            )

            layout_path = self._generator.output_layout_path
            if not layout_path:
                log("Output layout could not be saved.", info=False)
                return

            feedback = self._context.feedback
            project = QgsProject.instance()
            layout = _load_layout_from_file(layout_path, project)
            if layout is None:
                log("Could not load layout from file.", info=False)
                return

            # Zoom the extents of map items in the layout then export to PDF
            self._zoom_map_items_to_current_extents(layout)
            project.layoutManager().addLayout(layout)

            if feedback is not None:
                feedback.setProgress(100)


class ReportGenerator:
    """Generator for CPLUS reports."""

    AREA_DECIMAL_PLACES = 2

    def __init__(self, context: ReportContext, feedback: QgsFeedback = None):
        self._context = context
        self._feedback = context.feedback or feedback
        self._error_messages: typing.List[str] = []
        self._error_occurred = False
        self._layout = None
        self._project = None
        self._variable_register = LayoutVariableRegister()
        self._report_output_dir = ""
        self._output_layout_path = ""
        self._repeat_page = None
        self._repeat_page_num = -1
        self._repeat_item = None
        self._reference_layer_group = None
        self._scenario_layer = None
        self._area_processing_feedback = None
        self._activities_area = {}
        self._pixel_area_info = {}

        if self._feedback:
            self._feedback.canceled.connect(self._on_feedback_cancelled)

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
        number of activities in the scenario.

        A repeat page is a layout page item that contains the
        first instance of a CplusMapRepeatItem.

        :returns: Page item containing a CplusMapRepeatItem or None
        if not found.
        :rtype: QgsLayoutItemPage
        """
        return self._repeat_page

    def _process_check_cancelled_or_set_progress(self, value: float) -> bool:
        """Check if there is a request to cancel the process
        if a feedback object had been specified.
        """
        if (self._feedback and self._feedback.isCanceled()) or self._error_occurred:
            tr_msg = tr("Report generation cancelled.")
            self._error_messages.append(tr_msg)

            return True

        self._feedback.setProgress(value)

        return False

    def _on_feedback_cancelled(self):
        # Slot raised when the main feedback object has been cancelled.
        # Cancel both area calculation processes as well.
        if (
            self._area_processing_feedback
            and not self._area_processing_feedback.isCanceled()
        ):
            self._area_processing_feedback.cancel()

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

        # Set reference layer group in project i.e. the one that contains
        # the scenario output layer.
        layer_root = project.layerTreeRoot()
        matching_tree_layers = [
            tl
            for tl in layer_root.findLayers()
            if tl.layer().name() == self._context.output_layer_name
        ]
        if len(matching_tree_layers) > 0:
            scenario_tree_layer = matching_tree_layers[0]
            self._scenario_layer = scenario_tree_layer.layer()
            parent = scenario_tree_layer.parent()
            if parent.nodeType() == QgsLayerTreeNode.NodeType.NodeGroup:
                self._reference_layer_group = parent

        self._project = project

    @property
    def output_dir(self) -> str:
        """Creates, if it does not exist, the output directory
        where the analysis reports will be saved. This is relative
        to the base directory and scenario output sub-folder.

        :returns: Output directory where the analysis reports
        will be saved.
        :rtype: str
        """
        # Create reports directory
        if not self._report_output_dir:
            p = Path(self._context.scenario_output_dir)
            if not p.exists():
                try:
                    p.mkdir()
                except FileNotFoundError:
                    tr_msg = (
                        "Missing parent directory when creating "
                        "'report' subdirectory."
                    )
                    self._error_messages.append(tr_msg)
                    return ""

        self._report_output_dir = self._context.scenario_output_dir

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
        """Render activities in the layout based on the
        scenario result.
        """
        if self._repeat_item is None:
            tr_msg = tr("Unable to render activities as no repeat " "item was found.")
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
            tr_msg = tr("Repeat item width is too small to render the activities.")
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
            tr_msg = tr("Repeat item height is too small to render the " "activities.")
            self._error_messages.append(tr_msg)
            return
        else:
            num_rows = int(repeat_height // MINIMUM_ITEM_HEIGHT)
            bleed_item_height = (
                repeat_height - (num_rows * MINIMUM_ITEM_HEIGHT)
            ) / num_cols
            adjusted_item_height = MINIMUM_ITEM_HEIGHT + bleed_item_height

        max_items_page = num_rows * num_cols

        num_activities = len(self._context.scenario.weighted_activities)

        if num_activities == 0:
            tr_msg = "No activities in the scenario."
            self._error_messages.append(tr_msg)
            return

        progress_percent_per_activity = 25 / num_activities

        # Calculate number of pages required
        num_pages, req_pages = divmod(num_activities, int(max_items_page))

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

        self._pixel_area_info = calculate_raster_value_area(
            self._scenario_layer, feedback=self._area_processing_feedback
        )

        # Now, add IMs to the pages
        im_count = 0
        for p in range(num_pages):
            page_pos = self._repeat_page_num + p
            for r in range(num_rows):
                reference_y_pos = repeat_ref_y + (r * adjusted_item_height)
                for c in range(num_cols):
                    if im_count == num_activities:
                        break

                    activity = self._context.scenario.weighted_activities[im_count]
                    reference_x_pos = repeat_ref_x + (c * adjusted_item_width)
                    self._add_activity_items(
                        reference_x_pos,
                        reference_y_pos,
                        adjusted_item_width,
                        adjusted_item_height,
                        page_pos,
                        activity,
                    )

                    # Check cancel or update progress
                    if self._feedback:
                        progress = (
                            self._feedback.progress() + progress_percent_per_activity
                        )
                        if self._process_check_cancelled_or_set_progress(progress):
                            break

                    im_count += 1

        # Hide repeat item frame
        for p in range(self._layout.pageCollection().pageCount()):
            items = self._layout.pageCollection().itemsOnPage(p)
            for item in items:
                if isinstance(item, CplusMapRepeatItem):
                    item.setFrameEnabled(False)

    def _add_activity_items(
        self,
        pos_x: float,
        pos_y: float,
        width: float,
        height: float,
        page: int,
        activity: Activity,
    ):
        """Add a group item with map, labels etc. to the layout for the
        given activity.
        """
        # Map
        map_height = 0.8 * height
        im_map = QgsLayoutItemMap(self._layout)
        self._layout.addLayoutItem(im_map)
        im_map.setFrameEnabled(False)
        im_map.setBackgroundColor(self._project.backgroundColor())
        im_name = activity.name.lower().replace(" ", "_")
        im_map.setId(f"map_{im_name}")
        map_ref_point = QgsLayoutPoint(pos_x, pos_y, self._layout.units())
        im_map.attemptMove(map_ref_point, True, False, page)
        im_map.attemptResize(QgsLayoutSize(width, map_height, self._layout.units()))
        im_layer = self._get_activity_layer_in_project(
            str(activity.uuid), weighted=True
        )
        if im_layer is not None:
            ext = im_layer.extent()
            im_map.setLayers([im_layer])
            im_map.setExtent(ext)
            # Resize item again after the scale has been set correctly
            im_map.attemptResize(QgsLayoutSize(width, map_height, self._layout.units()))
        else:
            log(f"Could not find matching map layer for {activity.name} activity.")

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

        # Area details
        area_shape_item = QgsLayoutItemShape(self._layout)
        self._layout.addLayoutItem(area_shape_item)
        area_shape_item.setShapeType(QgsLayoutItemShape.Shape.Ellipse)
        area_shape_ref_point = QgsLayoutPoint(
            pos_x + 0.05 * width,
            pos_y + map_height - (0.75 * height),
            self._layout.units(),
        )

        area_shape_item.attemptMove(area_shape_ref_point, True, False, page)
        area_shape_item.attemptResize(
            QgsLayoutSize(0.18 * width, 0.18 * width, self._layout.units())
        )
        symbol_props_area = {
            "color": "255,255,255,179",
            "style": "solid",
            "outline_style": "solid",
            "line_color": "#b2df8a",
            "outline_width": "1.2",
        }
        symbol = QgsFillSymbol.createSimple(symbol_props_area)
        area_shape_item.setSymbol(symbol)

        # Area title name label
        area_name_lbl = QgsLayoutItemLabel(self._layout)
        self._layout.addLayoutItem(area_name_lbl)
        area_name_lbl.setText("Area")
        self.set_label_font(area_name_lbl, 10)

        name_lbl_ref_point = QgsLayoutPoint(
            pos_x + (0.105 * width),
            pos_y + map_height - (0.71 * height),
            self._layout.units(),
        )
        area_name_lbl.attemptMove(name_lbl_ref_point, True, False, page)
        area_name_lbl.attemptResize(
            QgsLayoutSize(0.15 * width, 0.15 * height, self._layout.units())
        )

        # Area size label
        area_size_lbl = QgsLayoutItemLabel(self._layout)
        self._layout.addLayoutItem(area_size_lbl)

        int_pixel_area_info = {
            int(value): area for value, area in self._pixel_area_info.items()
        }

        area_size = int_pixel_area_info.get(activity.style_pixel_value, 0)

        number_format = QgsBasicNumericFormat()
        number_format.setThousandsSeparator(",")
        number_format.setShowTrailingZeros(True)
        number_format.setNumberDecimalPlaces(self.AREA_DECIMAL_PLACES)

        font_size = 8 if area_size < 100000 else 6

        area_size_lbl.setText(
            number_format.formatDouble(area_size, QgsNumericFormatContext())
        )
        self.set_label_font(area_size_lbl, font_size)

        size_lbl_ref_point = QgsLayoutPoint(
            pos_x + (0.09 * width),
            pos_y + map_height - (0.67 * height),
            self._layout.units(),
        )

        area_size_lbl.attemptMove(size_lbl_ref_point, True, False, page)
        area_size_lbl.attemptResize(
            QgsLayoutSize(0.2 * width, 0.2 * height, self._layout.units())
        )

        # North arrow
        arrow_item = QgsLayoutItemPicture(self._layout)
        self._layout.addLayoutItem(arrow_item)
        arrow_item.setPicturePath(
            ":/images/north_arrows/layout_default_north_arrow.svg"
        )
        arrow_ref_point = QgsLayoutPoint(
            pos_x + 0.10 * width,
            pos_y + map_height - (0.13 * height),
            self._layout.units(),
        )
        arrow_item.attemptMove(arrow_ref_point, True, False, page)
        arrow_item.attemptResize(
            QgsLayoutSize(0.05 * width, 0.05 * height, self._layout.units())
        )

        # Add scale bar
        scale_bar = QgsLayoutItemScaleBar(self._layout)
        self._layout.addLayoutItem(scale_bar)
        scale_bar.setLinkedMap(im_map)
        scale_bar_ref_point = QgsLayoutPoint(
            pos_x + 0.02 * width,
            pos_y + map_height - (0.08 * height),
            self._layout.units(),
        )
        scale_bar.setUnitLabel("km")
        scale_bar.setHeight(1)
        scale_bar.setLabelBarSpace(1)

        version = Qgis.versionInt()
        if version < 33000:
            distance_unit_type = QgsUnitTypes.DistanceUnit.DistanceKilometers
            font_unit_type = QgsUnitTypes.RenderUnit.RenderPoints
        else:
            distance_unit_type = Qgis.DistanceUnit.Kilometers
            font_unit_type = Qgis.RenderUnit.Points

        scale_bar.setUnits(distance_unit_type)
        scale_bar.setSegmentSizeMode(
            QgsScaleBarSettings.SegmentSizeMode.SegmentSizeFitWidth
        )
        scale_bar.setUnitsPerSegment(100)
        scale_bar.setMinimumBarWidth(15)
        scale_bar.setMaximumBarWidth(30)

        # Scalebar text options
        scale_bar_font_size = 7
        font = get_report_font(scale_bar_font_size)
        txt_format = QgsTextFormat()
        txt_format.setFont(font)
        txt_format.setSize(scale_bar_font_size)
        txt_format.setSizeUnit(font_unit_type)
        scale_bar.setTextFormat(txt_format)

        scale_bar.attemptMove(scale_bar_ref_point, True, False, page)
        scale_bar.attemptResize(
            QgsLayoutSize(0.1 * width, 0.1 * height, self._layout.units())
        )

        title_font_size = 10
        description_font_size = 6.5

        # Activity name label
        margin = 0.01 * width
        label_width = (width - (2 * margin)) / 2
        name_label_height = 0.33 * shape_height
        activity_name_lbl = QgsLayoutItemLabel(self._layout)
        self._layout.addLayoutItem(activity_name_lbl)
        # Chop name to set limit in order to fit in the label
        activity_name = activity.name
        if len(activity_name) > MAX_ACTIVITY_NAME_LENGTH:
            activity_name = f"{activity.name[:MAX_ACTIVITY_NAME_LENGTH]}..."
        activity_name_lbl.setText(activity_name)
        self.set_label_font(activity_name_lbl, title_font_size)
        name_lbl_ref_point = QgsLayoutPoint(
            pos_x + margin, pos_y + map_height + margin, self._layout.units()
        )
        activity_name_lbl.attemptMove(name_lbl_ref_point, True, False, page)
        activity_name_lbl.attemptResize(
            QgsLayoutSize(label_width, name_label_height, self._layout.units())
        )

        # Activity description label
        desc_label_height = 0.67 * shape_height - (margin * 2)
        activity_desc_lbl = QgsLayoutItemLabel(self._layout)
        self._layout.addLayoutItem(activity_desc_lbl)
        # Chop description to set limit in order to fit in the label
        activity_description = activity.description
        if len(activity_description) > MAX_ACTIVITY_DESCRIPTION_LENGTH:
            activity_description = (
                f"{activity.description[:MAX_ACTIVITY_DESCRIPTION_LENGTH]}..."
            )
        activity_desc_lbl.setText(activity_description)
        self.set_label_font(activity_desc_lbl, description_font_size)
        desc_lbl_ref_point = QgsLayoutPoint(
            pos_x + margin,
            pos_y + map_height + name_label_height + margin * 2,
            self._layout.units(),
        )
        activity_desc_lbl.attemptMove(desc_lbl_ref_point, True, False, page)
        activity_desc_lbl.attemptResize(
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
        if len(activity.pathways) == 0:
            ncs_txt = tr("No NCS pathways in the activity")
        else:
            ncs_names = [ncs.name for ncs in activity.pathways]
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
        size: float,
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

        # Text format size unit
        if version < 33000:
            unit_type = QgsUnitTypes.RenderUnit.RenderPoints
        else:
            unit_type = Qgis.RenderUnit.Points

        # Label font setting option
        if version < 32400:
            label.setFont(font)
        else:
            txt_format = QgsTextFormat()
            txt_format.setFont(font)
            txt_format.setSize(size)
            txt_format.setSizeUnit(unit_type)
            label.setTextFormat(txt_format)

        label.refresh()

    def _get_activity_layer_in_project(
        self, activity_identifier: str, weighted: bool = False
    ) -> typing.Union[QgsRasterLayer, None]:
        """Retrieves the activity raster layer from the activity layer group in
        the project.

        :param activity_identifier: Unique identifier of the activity.
        :type activity_identifier: str

        :param weighted: True to search under weighted activity
        category else under the activities maps.
        category. Default is False.
        :type weighted: bool
        """
        if weighted:
            category_name = tr(ACTIVITY_WEIGHTED_GROUP_NAME)
        else:
            category_name = tr(ACTIVITY_GROUP_LAYER_NAME)

        if self._project is None:
            tr_msg = tr(
                "Project could not be recreated, unable to fetch the activity layer."
            )
            self._error_messages.append(tr_msg)
            return None

        if self._reference_layer_group is None:
            tr_msg = tr(
                "Could not find the scenario layer group, unable to fetch the activity layer."
            )
            self._error_messages.append(tr_msg)
            return None

        activity_layer_group = self._reference_layer_group.findGroup(category_name)
        if activity_layer_group is None:
            tr_msg = tr(
                f"Could not find the {category_name} layer group, unable to fetch the activity layer."
            )
            self._error_messages.append(tr_msg)
            return None

        matching_tree_layers = [
            tl
            for tl in activity_layer_group.findLayers()
            if tl.layer().customProperty(ACTIVITY_IDENTIFIER_PROPERTY, "")
            == activity_identifier
        ]
        if len(matching_tree_layers) == 0:
            tr_msg = tr(
                f"Could not find the activity layer in the {category_name} layer group."
            )
            self._error_messages.append(tr_msg)
            return None

        return matching_tree_layers[0].layer()

    def _update_main_map_legend(self):
        """Textual adjustments to the main map legend."""
        legend_item: QgsLayoutItemLegend = self._layout.itemById("legend_main_map")
        if legend_item is None:
            tr_msg = tr("Could not find the main map legend.")
            self._error_messages.append(tr_msg)
            return

        legend_item.setAutoUpdateModel(False)
        model = legend_item.model()
        activity_names = [
            activity.name.lower() for activity in self._context.scenario.activities
        ]

        # Hiding the first root group child title
        root_group = legend_item.model().rootGroup()
        root_children = root_group.children() if root_group is not None else []

        if len(root_children) > 0:
            QgsLegendRenderer.setNodeLegendStyle(
                root_children[0], QgsLegendStyle.Hidden
            )

        for tree_layer in legend_item.model().rootGroup().findLayers():
            if tree_layer.name() == self._context.output_layer_name:
                # We need to refresh the tree layer for the nodes to be loaded
                model.refreshLayerLegend(tree_layer)
                scenario_child_nodes = model.layerLegendNodes(tree_layer)
                activity_node_indices = []
                for i, child_node in enumerate(scenario_child_nodes):
                    node_name = str(child_node.data(QtCore.Qt.DisplayRole))
                    # Only show nodes for activity nodes used for the scenario
                    if node_name.lower() in activity_names:
                        activity_node_indices.append(i)

                QgsMapLayerLegendUtils.setLegendNodeOrder(
                    tree_layer, activity_node_indices
                )

                # Removing the tree layer band title
                QgsLegendRenderer.setNodeLegendStyle(tree_layer, QgsLegendStyle.Hidden)

                model.refreshLayerLegend(tree_layer)
            else:
                # Remove all other non-scenario layers
                node_index = model.node2index(tree_layer)
                if not node_index.isValid():
                    continue
                model.removeRow(node_index.row(), node_index.parent())

        # Refresh legend
        legend_item.adjustBoxSize()
        legend_item.invalidateCache()
        legend_item.update()

    def _get_table_from_id(
        self, table_id: str
    ) -> typing.Union[QgsLayoutItemManualTable, None]:
        """Get the table object from the corresponding item id or return None
        if the table was not found.
        """
        table_frame = self._layout.itemById(table_id)
        if table_frame is None:
            return None

        return table_frame.multiFrame()

    def _populate_activity_area_table(self):
        """Populate the table(s) for activities and
        corresponding areas.
        """
        self._area_calculation_progress_reference = 60
        self._area_calculation_step_increment = 20

        parent_table = self._get_table_from_id(ACTIVITY_AREA_TABLE_ID)
        if parent_table is None:
            tr_msg = tr("Could not find parent table for areas of activities.")
            self._error_messages.append(tr_msg)
            return

        num_activities = len(self._context.scenario.activities)
        if num_activities == 0:
            tr_msg = tr("No activities in the scenario.")
            self._error_messages.append(tr_msg)
            return

        if self._scenario_layer is None:
            tr_msg = tr("Scenario layer could not be set to calculate the area.")
            self._error_messages.append(tr_msg)
            return

        # Calculate pixel area
        pixel_area_info = self._pixel_area_info

        if len(pixel_area_info) == 0:
            tr_msg = tr("No activity areas from the calculation.")
            self._error_occurred = True
            self._error_messages.append(tr_msg)
            return

        # Pixel type conversion
        int_pixel_area_info = {
            int(value): area for value, area in pixel_area_info.items()
        }

        rows_data = []
        for activity in self._context.scenario.weighted_activities:
            # Activity name column
            name_cell = QgsTableCell(activity.name)
            name_cell.setBackgroundColor(QtGui.QColor("#e9e9e9"))

            # Activity area column
            if activity.style_pixel_value in int_pixel_area_info:
                area_info = int_pixel_area_info.get(activity.style_pixel_value)
            else:
                log(f"Pixel value not found in calculation")
                area_info = tr("<Pixel value not found>")

            area_cell = QgsTableCell(area_info)
            if isinstance(area_info, Number):
                number_format = QgsBasicNumericFormat()
                number_format.setThousandsSeparator(",")
                number_format.setShowTrailingZeros(True)
                number_format.setNumberDecimalPlaces(self.AREA_DECIMAL_PLACES)
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
        groups = []
        for priority_group in self._context.scenario.priority_layer_groups:
            if "name" not in priority_group or "value" not in priority_group:
                continue

            group_name = priority_group["name"]
            # Ensure there are no duplicates in the table
            if group_name in groups:
                continue

            # If value is less than or equal to zero then do not include in the table.
            value = -1
            try:
                value = int(priority_group["value"])
            except ValueError:
                continue

            if value <= 0:
                continue

            name_cell = QgsTableCell(group_name)
            value_cell = QgsTableCell(value)
            rows_data.append([name_cell, value_cell])
            groups.append(group_name)

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
        if self._process_check_cancelled_or_set_progress(0):
            return self._get_failed_result()

        self._set_project()
        if self._project is None:
            return self._get_failed_result()

        if self._process_check_cancelled_or_set_progress(5):
            return self._get_failed_result()

        if not self._load_template() or not self.output_dir:
            return self._get_failed_result()

        if self._process_check_cancelled_or_set_progress(12):
            return self._get_failed_result()

        # Update variable values
        self._variable_register.update_variables(self.layout, self._context)

        if self._process_check_cancelled_or_set_progress(15):
            return self._get_failed_result()

        # Set repeat page
        self._set_repeat_page()

        if self._process_check_cancelled_or_set_progress(20):
            return self._get_failed_result()

        if self._process_check_cancelled_or_set_progress(45):
            return self._get_failed_result()

        # Render repeat items i.e. activities
        self._render_repeat_items()

        if self._process_check_cancelled_or_set_progress(70):
            return self._get_failed_result()

        # Populate activity area table
        self._populate_activity_area_table()

        if self._process_check_cancelled_or_set_progress(80):
            return self._get_failed_result()

        # Populate table with priority weighting values
        self._populate_scenario_weighting_values()

        # Update the legend for the main map
        self._update_main_map_legend()

        # Add CPLUS report flag
        self._variable_register.set_report_flag(self._layout)

        if self._process_check_cancelled_or_set_progress(85):
            return self._get_failed_result()

        result = self._save_layout_to_file()
        if not result:
            return self._get_failed_result()

        if self._process_check_cancelled_or_set_progress(90):
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

    def export_to_pdf(self) -> bool:
        """Exports the layout to a PDF file in the output
        directory using the layout name as the file name.

        :returns: True if the layout was successfully exported else False.
        :rtype: bool
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
        """Loads the template in the report context and registers
        CPLUS variables.

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
