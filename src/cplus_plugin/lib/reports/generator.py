# -*- coding: utf-8 -*-
"""
CPLUS Report generator.
"""
import os
from pathlib import Path
import typing

from qgis.core import (
    Qgis,
    QgsLayoutExporter,
    QgsPrintLayout,
    QgsProject,
    QgsReadWriteContext,
    QgsTask,
)

from qgis.PyQt import QtCore, QtXml

from ...conf import Settings, settings_manager
from ...definitions.constants import OUTPUTS_SEGMENT
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

        # Save active project instance to file and have it
        # recreated by the generator since QgsProject
        # instances are not thread safe.
        proj_file = QtCore.QTemporaryFile()
        if proj_file.open():
            file_path = proj_file.fileName()
            project_file_path = f"{file_path}.qgz"
            storage_type = QgsProject.instance().filePathStorage()
            QgsProject.instance().setFilePathStorage(Qgis.FilePathType.Absolute)
            result = QgsProject.instance().write(project_file_path)
            QgsProject.instance().setFilePathStorage(storage_type)
            if result:
                self._context.project_file = project_file_path

        # Set base name for the layout and PDF file suffixed with a number
        # depending on the number of runs.
        layout_manager = QgsProject.instance().layoutManager()
        counter = 1
        scenario_name = self._context.scenario.name
        while True:
            layout_name = f"{scenario_name} {counter!s}"
            matching_layout = layout_manager.layoutByName(layout_name)
            if matching_layout is None:
                self._context.name = layout_name
                break
            counter += 1

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
            layout = self._generator.layout
            if layout is None:
                return

            # Force ownership to main thread by cloning layout
            reference_layout = layout.clone()
            QgsProject.instance().layoutManager().addLayout(reference_layout)

        else:
            log(
                f"Error occurred when generating the "
                f"report for {self._context.scenario.name} "
                f"scenario. See details below:"
            )
            for err in self.result.messages:
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
        self._output_dir = ""

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
        if not self._output_dir:
            base_dir = settings_manager.get_value(Settings.BASE_DIR, "")
            if not base_dir:
                tr_msg = tr("Base directory has not yet been specified.")
                self._error_messages.append(tr_msg)
                return ""

            if not Path(base_dir).exists():
                tr_msg = tr("Base directory does not exist")
                self._error_messages.append(f"{tr_msg} {base_dir}.")
                return ""

            if not os.access(base_dir, os.W_OK):
                tr_msg = tr("No permission to write to base directory")
                self._error_messages.append(f"{tr_msg} {base_dir}.")
                return ""

            # Create outputs directory
            p = Path(f"{base_dir}/{OUTPUTS_SEGMENT}")
            if not p.exists():
                try:
                    p.mkdir()
                except FileNotFoundError:
                    tr_msg = (
                        "Missing parent directory when creating "
                        "outputs subdirectory in the base directory."
                    )
                    self._error_messages.append(tr_msg)
                    return ""

            scenario_id = str(self._context.scenario.uuid)

            # Create scenario directory
            p = Path(f"{base_dir}/{OUTPUTS_SEGMENT}/{scenario_id}")
            if not p.exists():
                try:
                    p.mkdir()
                except FileNotFoundError:
                    tr_msg = (
                        "Missing parent directory when creating "
                        "subdirectory for scenario"
                    )
                    self._error_messages.append(f"{tr_msg} {scenario_id}.")
                    return ""

            # Create reports directory
            output_dir = f"{base_dir}/{OUTPUTS_SEGMENT}/" f"{scenario_id}/reports"

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

                self._output_dir = output_dir

        return self._output_dir

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

        # Add CPLUS report flag
        self._variable_register.set_report_flag(self._layout)

        self._export_to_pdf()

        return ReportResult(
            True,
            self._context.scenario.uuid,
            self.output_dir,
            tuple(self._error_messages),
            self._context.name,
        )

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
        p = Path(self._context.template_path)
        if not p.exists():
            tr_msg = tr("Template file does not exist")
            self._error_messages.append(f"{tr_msg} {self._context.template_path}.")
            return False

        template_file = QtCore.QFile(self._context.template_path)
        doc = QtXml.QDomDocument()
        doc_status = True
        try:
            if not template_file.open(QtCore.QIODevice.ReadOnly):
                tr_msg = tr("Unable to read template file")
                self._error_messages.append(f"{tr_msg} {self._context.template_path}.")
                doc_status = False

            if doc_status:
                if not doc.setContent(template_file):
                    tr_msg = tr("Failed to parse template file contents")
                    self._error_messages.append(
                        f"{tr_msg} {self._context.template_path}."
                    )
                    doc_status = False
        finally:
            template_file.close()

        if not doc_status:
            return False

        self._layout = QgsPrintLayout(self._project)
        _, load_status = self._layout.loadFromTemplate(doc, QgsReadWriteContext())
        if not load_status:
            tr_msg = tr("Could not load template from")
            self._error_messages.append(f"{tr_msg} {self._context.template_path}.")
            return False

        self._variable_register.register_variables(self._layout)

        self._layout.setName(self._context.name)

        return True
