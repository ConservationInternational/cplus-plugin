# -*- coding: utf-8 -*-
"""
CPLUS Report generator.
"""
import os
from pathlib import Path
import typing

from qgis.core import (
    Qgis,
    QgsLayoutItemPage,
    QgsLayoutExporter,
    QgsLayoutPoint,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsTask,
)

from qgis.PyQt import QtCore, QtXml

from .layout_items import CplusMapRepeatItem
from ...models.report import ReportContext, ReportResult
from ...utils import log, tr
from .variables import LayoutVariableRegister


class ReportGeneratorTask(QgsTask):
    """Proxy class for initiating the report generation process."""

    def __init__(self, description: str, context: ReportContext):
        super().__init__(description)
        self._context = context
        self._result = None
        self._generator = ReportGenerator(self._context)

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

    def __init__(self, context: ReportContext):
        self._context = context
        self._error_messages: typing.List[str] = []
        self._layout = None
        self._project = None
        self._variable_register = LayoutVariableRegister()
        self._report_output_dir = ""
        self._output_layout_path = ""
        self._repeat_page = None
        self._repeat_page_num = -1
        self._repeat_item = None

    @property
    def context(self) -> ReportContext:
        """Returns the report context used by the generator.

        :returns: Report context object used by the generator.
        :rtype: ReportContext
        """
        return self._context

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

    def duplicate_repeat_page(
        self, position: int
    ) -> typing.Union[QgsLayoutItemPage, None]:
        """Duplicates the repeat page and adds it to the layout
        at the given position.

        :param position: Zero-based position to insert the duplicated page. If
        the position is greater than the number of pages, then the
        duplicated page will be inserted at the end of the layout.
        :type position: int

        :returns: A duplicate layout page item of the repeat page or
        None if a repeat page was not found or if the layout is None.
        :rtype: QgsLayoutItemPage
        """
        if self._repeat_page is None:
            return None

        if self._layout is None:
            return None

        page_collection = self._layout.pageCollection()
        if self._repeat_page_num == -1:
            tr_msg = "Repeat page not found in page collection"
            self._error_messages.append(tr_msg)
            return None

        # Insert empty repeat page at the given position
        if position < page_collection.pageCount():
            page_collection.insertPage(self._repeat_page, position)
        else:
            # Add to the end
            position = page_collection.pageCount()
            page_collection.addPage(self._repeat_page)

        doc = QtXml.QDomDocument()
        el = doc.createElement("CopyItems")
        ctx = QgsReadWriteContext()
        repeat_page_items = page_collection.itemsOnPage(self._repeat_page_num)
        for item in repeat_page_items:
            item.writeXml(el, doc, ctx)
            doc.appendChild(el)

        # Clear element identifier references
        nodes = doc.elementsByTagName("LayoutItem")
        for n in range(nodes.count()):
            node = nodes.at(n)
            if node.isElement():
                node.toElement().removeAttribute("uuid")

        page_ref_point = page_collection.pagePositionToLayoutPosition(
            position, QgsLayoutPoint(0, 0, self._layout.units())
        )
        self._layout.addItemsFromXml(el, doc, ctx, page_ref_point, True)

        duplicated_page = page_collection.page(position)

        # Duplicate page background
        fill_symbol = self._repeat_page.pageStyleSymbol()
        duplicated_page.setPageStyleSymbol(fill_symbol.clone())

        return duplicated_page

    def _render_repeat_items(self):
        """Render implementation models in the layout based on the
        scenario result.
        """
        if self._repeat_item is None:
            tr_msg = tr(
                "Unable to render implementation models as no repeat "
                "item was found."
            )
            self._error_messages.append(tr_msg)
            return

        repeat_rect = self._repeat_item.rectWithFrame()

    def run(self) -> ReportResult:
        """Initiates the report generation process and returns
        a result which contains information on whether the
        process succeeded or failed.

        :returns: The result of the report generation process.
        :rtype: ReportResult
        """
        self._set_project()
        if self._project is None:
            return self._get_failed_result()

        if not self._load_template() or not self.output_dir:
            return self._get_failed_result()

        # Update variable values
        self._variable_register.update_variables(self.layout, self._context)

        # Set repeat page
        self._set_repeat_page()

        # Render repeat items i.e. implementation models
        self._render_repeat_items()

        # Add CPLUS report flag
        self._variable_register.set_report_flag(self._layout)

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
