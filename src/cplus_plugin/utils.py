# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""


import os
import uuid
from pathlib import Path

from qgis.PyQt import QtCore, QtGui
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsDistanceArea,
    QgsMessageLog,
    QgsProcessingFeedback,
    QgsRasterLayer,
    QgsRectangle,
    QgsUnitTypes,
)

from qgis.analysis import QgsAlignRaster

from qgis import processing

from .definitions.defaults import DOCUMENTATION_SITE, REPORT_FONT_NAME, TEMPLATE_NAME
from .definitions.constants import (
    NCS_CARBON_SEGMENT,
    NCS_PATHWAY_SEGMENT,
    PRIORITY_LAYERS_SEGMENT,
)


def tr(message):
    """Get the translation for a string using Qt translation API.
    We implement this ourselves since we do not inherit QObject.

    :param message: String for translation.
    :type message: str, QString

    :returns: Translated version of message.
    :rtype: QString
    """
    # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
    return QtCore.QCoreApplication.translate("QgisCplus", message)


def log(
    message: str,
    name: str = "qgis_cplus",
    info: bool = True,
    notify: bool = True,
):
    """Logs the message into QGIS logs using qgis_cplus as the default
    log instance.
    If notify_user is True, user will be notified about the log.

    :param message: The log message
    :type message: str

    :param name: Name of te log instance, qgis_cplus is the default
    :type message: str

    :param info: Whether the message is about info or a
    warning
    :type info: bool

    :param notify: Whether to notify user about the log
    :type notify: bool
    """
    level = Qgis.Info if info else Qgis.Warning
    QgsMessageLog.logMessage(
        message,
        name,
        level=level,
        notifyUser=notify,
    )


def open_documentation(url=None):
    """Opens documentation website in the default browser

    :param url: URL link to documentation site (e.g. gh pages site)
    :type url: str

    """
    url = DOCUMENTATION_SITE if url is None else url
    result = QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
    return result


def get_report_font(size=11.0, bold=False, italic=False) -> QtGui.QFont:
    """Uses the default font family name to create a
    font for use in the report.

    :param size: The font point size, default is 11.
    :type size: float

    :param bold: True for bold font else False which is the default.
    :type bold: bool

    :param italic: True for font to be in italics else False which is the default.
    :type italic: bool

    :returns: Font to use in a report.
    :rtype: QtGui.QFont
    """
    font_weight = 50
    if bold is True:
        font_weight = 75

    return QtGui.QFont(REPORT_FONT_NAME, int(size), font_weight, italic)


def clean_filename(filename):
    """Creates a safe filename by removing operating system
    invalid filename characters.

    :param filename: File name
    :type filename: str

    :returns A clean file name
    :rtype str
    """
    characters = " %:/,\[]<>*?"

    for character in characters:
        if character in filename:
            filename = filename.replace(character, "_")

    return filename


def calculate_raster_value_area(
    layer: QgsRasterLayer, band_number: int = 1, feedback: QgsProcessingFeedback = None
) -> dict:
    """Calculates the area of value pixels for the given band in a raster layer.

    Please note that this function will run in the main application thread hence
    for best results, it is recommended to execute it in a background process
    if part of a bigger workflow.

    :param layer: Input layer whose area for value pixels is to be calculated.
    :type layer: QgsRasterLayer

    :param band_number: Band number to compute area, default is band one.
    :type band_number: int

    :param feedback: Feedback object for progress during area calculation.
    :type feedback: QgsProcessingFeedback

    :returns: A dictionary containing the pixel value as
    the key and the corresponding area in hectares as the value for all the pixels
    in the raster otherwise returns a empty dictionary if the raster is invalid
    or if it is empty.
    :rtype: float
    """
    if not layer.isValid():
        log("Invalid layer for raster area calculation.", info=False)
        return {}

    algorithm_name = "native:rasterlayeruniquevaluesreport"
    params = {
        "INPUT": layer,
        "BAND": band_number,
        "OUTPUT_TABLE": "TEMPORARY_OUTPUT",
        "OUTPUT_HTML_FILE": "[Skip output]",
    }

    algorithm_result = processing.run(algorithm_name, params, feedback=feedback)

    # Get number of pixels with values
    total_pixel_count = algorithm_result["TOTAL_PIXEL_COUNT"]
    if total_pixel_count == 0:
        log("Input layer for raster area calculation is empty.", info=False)
        return {}

    output_table = algorithm_result["OUTPUT_TABLE"]
    if output_table is None:
        log("Unique values raster table could not be retrieved.", info=False)
        return {}

    area_calc = QgsDistanceArea()
    crs = layer.crs()
    area_calc.setSourceCrs(crs, QgsCoordinateTransformContext())
    if crs is not None:
        # Use ellipsoid calculation if available
        area_calc.setEllipsoid(crs.ellipsoidAcronym())

    version = Qgis.versionInt()
    if version < 33000:
        unit_type = QgsUnitTypes.AreaUnit.AreaHectares
    else:
        unit_type = Qgis.AreaUnit.Hectares

    pixel_areas = {}
    features = output_table.getFeatures()
    for f in features:
        pixel_value = f.attribute(0)
        area = f.attribute(2)
        pixel_value_area = area_calc.convertAreaMeasurement(area, unit_type)
        pixel_areas[int(pixel_value)] = pixel_value_area

    return pixel_areas


def align_rasters(
    input_raster_source,
    reference_raster_source,
    extent,
    output_dir,
    rescale_values=False,
    resample=True,
):
    """
    Based from work on https://github.com/inasafe/inasafe/pull/2070
    Aligns the passed raster files source and save the results into new files.

    :param input_raster_source: Input layer source
    :type input_raster_source: str

    :param reference_raster_source: Reference layer source
    :type reference_raster_source: str

    :param extent: Clip extent
    :type extent: list

    :param output_dir: Output directory for the snapped
    layers
    :type output_dir: str

    :param rescale_values: Whether to rescale pixel values
    :type rescale_values: bool

    :param resample: Whether to allow values resampling
    :type resample: bool

    """
    directory = output_dir / "snap_layers"
    FileUtils.create_new_dir(directory)

    input_layer_output = f"{directory}/{uuid.uuid4()[5]}.tif"
    reference_layer_output = f"{directory}/{uuid.uuid4()[5]}.tif"

    align = QgsAlignRaster()
    lst = [
        QgsAlignRaster.Item(input_raster_source, input_layer_output),
        QgsAlignRaster.Item(reference_raster_source, reference_layer_output),
    ]

    if rescale_values:
        lst[0].rescaleValues = True
        lst[1].rescaleValues = True

    align.setRasters(lst)

    if resample:
        index = align.suggestedReferenceLayer()
    else:
        index = 1  # have to use second layer as the reference

    align.setParametersFromRaster(lst[index].inputFilename)

    tranformed_extent = QgsRectangle(extent[0], extent[1], extent[2], extent[3])
    transform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem("EPSG:4326"),
        QgsCoordinateReferenceSystem(align.destinationCRS()),
    )

    tranformed_extent = transform.transformBoundingBox(tranformed_extent)

    align.setClipExtent(tranformed_extent)

    if not align.run():
        raise Exception(align.errorMessage())

    return input_layer_output, reference_layer_output


class FileUtils:
    """
    Provides functionality for commonly used file-related operations.
    """

    @staticmethod
    def plugin_dir() -> str:
        """Returns the root directory of the plugin.

        :returns: Root directory of the plugin.
        :rtype: str
        """
        return os.path.join(os.path.dirname(os.path.realpath(__file__)))

    @staticmethod
    def get_icon(file_name: str) -> QtGui.QIcon:
        """Creates an icon based on the icon name in the 'icons' folder.

        :param file_name: File name which should include the extension.
        :type file_name: str

        :returns: Icon object matching the file name.
        :rtype: QtGui.QIcon
        """
        icon_path = os.path.normpath(f"{FileUtils.plugin_dir()}/icons/{file_name}")

        if not os.path.exists(icon_path):
            return QtGui.QIcon()

        return QtGui.QIcon(icon_path)

    @staticmethod
    def report_template_path(file_name=None) -> str:
        """Get the absolute path to the template file with the given name.
        Caller needs to verify that the file actually exists.

        :param file_name: Template file name including the extension. If
        none is specified then it will use `main.qpt` as the default
        template name.
        :type file_name: str

        :returns: The absolute path to the template file with the given name.
        :rtype: str
        """
        if file_name is None:
            file_name = TEMPLATE_NAME

        absolute_path = f"{FileUtils.plugin_dir()}/app_data/reports/{file_name}"

        return os.path.normpath(absolute_path)

    @staticmethod
    def create_ncs_pathways_dir(base_dir: str):
        """Creates an NCS subdirectory under BASE_DIR. Skips
        creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        ncs_pathway_dir = f"{base_dir}/{NCS_PATHWAY_SEGMENT}"
        message = tr(
            "Missing parent directory when creating NCS pathways subdirectory."
        )
        FileUtils.create_new_dir(ncs_pathway_dir, message)

    @staticmethod
    def create_ncs_carbon_dir(base_dir: str):
        """Creates an NCS subdirectory for carbon layers under BASE_DIR.
        Skips creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        ncs_carbon_dir = f"{base_dir}/{NCS_CARBON_SEGMENT}"
        message = tr("Missing parent directory when creating NCS carbon subdirectory.")
        FileUtils.create_new_dir(ncs_carbon_dir, message)

    def create_pwls_dir(base_dir: str):
        """Creates priority weighting layers subdirectory under BASE_DIR.
        Skips creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        pwl_dir = f"{base_dir}/{PRIORITY_LAYERS_SEGMENT}"
        message = tr(
            "Missing parent directory when creating priority weighting layers subdirectory."
        )
        FileUtils.create_new_dir(pwl_dir, message)

    @staticmethod
    def create_new_dir(directory: str, log_message: str = ""):
        """Creates new file directory if it doesn't exist"""
        p = Path(directory)
        if not p.exists():
            try:
                p.mkdir()
            except FileNotFoundError:
                log(log_message)

    @staticmethod
    def create_new_file(file_path: str, log_message: str = ""):
        """Creates new file"""
        p = Path(file_path)

        if not p.exists():
            try:
                p.touch(exits=True)
            except FileNotFoundError:
                log(log_message)
