# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""


import hashlib
import json
import os
import uuid
import datetime
from pathlib import Path
from uuid import UUID

from qgis.PyQt import QtCore, QtGui
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsDistanceArea,
    QgsMessageLog,
    QgsProcessingFeedback,
    QgsProject,
    QgsProcessing,
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


def write_to_file(message, file_path):
    with open(file_path, "w+") as f:
        f.write(message)


def open_documentation(url=None):
    """Opens documentation website in the default browser

    :param url: URL link to documentation site (e.g. gh pages site)
    :type url: str

    """
    url = DOCUMENTATION_SITE if url is None else url
    result = QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
    return result


def get_plugin_version() -> [str, None]:
    """Returns the current plugin version
    as saved in the metadata.txt plugin file.

    :returns version: Plugin version
    :rtype version: str
    """
    metadata_file = Path(__file__).parent.resolve() / "metadata.txt"

    with open(metadata_file, "r") as f:
        for line in f.readlines():
            if line.startswith("version"):
                version = line.strip().split("=")[1]
                return version
    return None


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
        "OUTPUT_HTML_FILE": QgsProcessing.TEMPORARY_OUTPUT,
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
        pixel_areas[pixel_value] = pixel_value_area

    return pixel_areas


def transform_extent(extent, source_crs, dest_crs):
    """Transforms the passed extent into the destination crs

     :param extent: Target extent
    :type extent: QgsRectangle

    :param source_crs: Source CRS of the passed extent
    :type source_crs: QgsCoordinateReferenceSystem

    :param dest_crs: Destination CRS
    :type dest_crs: QgsCoordinateReferenceSystem
    """

    transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
    transformed_extent = transform.transformBoundingBox(extent)

    return transformed_extent


def align_rasters(
    input_raster_source,
    reference_raster_source,
    extent=None,
    output_dir=None,
    rescale_values=False,
    resample_method=0,
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

    :param output_dir: Absolute path of the output directory for the snapped
    layers
    :type output_dir: str

    :param rescale_values: Whether to rescale pixel values
    :type rescale_values: bool

    :param resample_method: Method to use when resampling
    :type resample_method: QgsAlignRaster.ResampleAlg

    """

    try:
        snap_directory = os.path.join(output_dir, "snap_layers")

        FileUtils.create_new_dir(snap_directory)

        input_path = Path(input_raster_source)

        input_layer_output = os.path.join(
            f"{snap_directory}", f"{input_path.stem}_{str(uuid.uuid4())[:4]}.tif"
        )

        FileUtils.create_new_file(input_layer_output)

        align = QgsAlignRaster()
        lst = [
            QgsAlignRaster.Item(input_raster_source, input_layer_output),
        ]

        resample_method_value = QgsAlignRaster.ResampleAlg.RA_NearestNeighbour

        try:
            resample_method_value = QgsAlignRaster.ResampleAlg(int(resample_method))
        except Exception as e:
            log(f"Problem creating a resample value when snapping, {e}")

        if rescale_values:
            lst[0].rescaleValues = rescale_values

        lst[0].resample_method = resample_method_value

        align.setRasters(lst)
        align.setParametersFromRaster(reference_raster_source)

        layer = QgsRasterLayer(input_raster_source, "input_layer")

        extent = transform_extent(
            layer.extent(),
            QgsCoordinateReferenceSystem(layer.crs()),
            QgsCoordinateReferenceSystem(align.destinationCrs()),
        )

        align.setClipExtent(extent)

        log(f"Snapping clip extent {layer.extent().asWktPolygon()} \n")

        if not align.run():
            log(
                f"Problem during snapping for {input_raster_source} and "
                f"{reference_raster_source}, {align.errorMessage()}"
            )
            raise Exception(align.errorMessage())
    except Exception as e:
        log(
            f"Problem occured when snapping, {str(e)}."
            f" Update snap settings and re-run the analysis"
        )

        return None, None

    log(
        f"Finished snapping"
        f" original layer - {input_raster_source},"
        f"snapped output - {input_layer_output} \n"
    )

    return input_layer_output, None


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

        absolute_path = f"{FileUtils.plugin_dir()}/data/reports/{file_name}"

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
            except (FileNotFoundError, OSError):
                log(log_message)

    @staticmethod
    def create_new_file(file_path: str, log_message: str = ""):
        """Creates new file"""
        p = Path(file_path)

        if not p.exists():
            try:
                p.touch(exist_ok=True)
            except FileNotFoundError:
                log(log_message)


class CustomJsonEncoder(json.JSONEncoder):
    """
    Custom JSON encoder which handles UUID and datetime
    """

    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return obj.hex
        if isinstance(obj, datetime.datetime):
            # if the obj is uuid, we simply return the value of uuid
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def todict(obj, classkey=None):
    """
    Convert any object to dictionary
    """

    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
            for key, value in obj.__dict__.items()
            if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj


def md5(fname):
    """
    Get md5 checksum off a file
    """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
