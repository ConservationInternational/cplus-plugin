# -*- coding: utf-8 -*-
"""
CPLUS Report generator.
"""
import typing

from qgis.core import QgsPrintLayout

from ...models.report import ReportContext, ReportResult


class ReportGenerator:
    """Generator for CPLUS reports."""

    def __init__(self, context: ReportContext):
        self._context = context

    @property
    def context(self) -> ReportContext:
        """Returns the report context used by the generator.

        :returns: Report context object used by the generator.
        :rtype: ReportContext
        """
        return self._context

    def run(self) -> ReportResult:
        """Initiates the report generation process and returns
        a result which contains information on whether the
        process succeeded or failed.

        :returns: The result of the report generation process.
        :rtype: ReportResult
        """
        pass

    def _load_template(self, template_name=None) -> QgsPrintLayout:
        """Loads the template with the given file name in the
        app_data directory and returns the corresponding layout
        object.

        :param template_name: Template name as defined in the
        app_data/reports directory.
        :type template_name: str

        :returns: The layout object corresponding to the template
        file else None if the file does not exist or could not be
        loaded.
        :rtype: QgsPrintLayout
        """
        pass
