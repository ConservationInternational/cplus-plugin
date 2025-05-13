# -*- coding: utf-8 -*-
"""
    Plugin utilities
"""

import hashlib
import json
import math
import os
import typing
import uuid
import datetime
from pathlib import Path
from uuid import UUID
from enum import Enum

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

from .definitions.defaults import (
    DOCUMENTATION_SITE,
    REPORT_FONT_NAME,
    SCENARIO_ANALYSIS_TEMPLATE_NAME,
)
from .definitions.constants import (
    COMPARISON_REPORT_SEGMENT,
    NCS_CARBON_SEGMENT,
    NCS_PATHWAY_SEGMENT,
    NPV_PRIORITY_LAYERS_SEGMENT,
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
    if not isinstance(message, str):
        message = json.dumps(todict(message), cls=CustomJsonEncoder)
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


def calculate_raster_area_by_pixel_value(
    layer: QgsRasterLayer, band_number: int = 1, feedback: QgsProcessingFeedback = None
) -> dict:
    """Calculates the area of value pixels for the given band in a raster layer and
    groups the area by the pixel value.

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


def calculate_raster_area(
    layer: QgsRasterLayer, band_number: int = 1, feedback: QgsProcessingFeedback = None
) -> float:
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

    :returns: The total area of value pixels of the raster else -1 if the raster
    is invalid or if it is empty. Pixels with NoData value are not included
    in the computation.
    :rtype: float
    """
    area_by_pixel_value = calculate_raster_area_by_pixel_value(
        layer, band_number, feedback
    )
    if len(area_by_pixel_value) == 0:
        return -1.0

    # Remove NoData pixels from the computation, just in case.
    if layer.dataProvider().sourceHasNoDataValue(band_number):
        no_data_value = layer.dataProvider().sourceNoDataValue(band_number)
        if no_data_value in area_by_pixel_value:
            del area_by_pixel_value[no_data_value]

    return float(sum(area_by_pixel_value.values()))


def generate_random_color() -> QtGui.QColor:
    """Generate a random color object using a system-seeded
    deterministic approach.

    :returns: A random generated color.
    :rtype: QColor
    """
    return QtGui.QColor.fromRgb(QtCore.QRandomGenerator.global_().generate())


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


def contains_font_family(font_family: str) -> bool:
    """Checks if the specified font family exists in the font database.

    :param font_family: Name of the font family to check.
    :type font_family: str

    :returns: True if the font family exists, else False.
    :rtype: bool
    """
    font_families = QtGui.QFontDatabase().families()
    matching_fonts = [family for family in font_families if font_family in family]

    return True if len(matching_fonts) > 0 else False


def install_font(dir_name: str) -> bool:
    """Installs the font families in the specified folder name under
    the plugin's 'fonts' folder.

    :param dir_name: Directory name, under the 'fonts' folder, which
    contains the font families to be installed.
    :type dir_name: str

    :returns: True if the font(s) were successfully installed, else
    False if the directory name does not exist or if the given font
    families already exist in the application's font database.
    :rtype: bool
    """
    font_family_dir = os.path.normpath(f"{FileUtils.get_fonts_dir()}/{dir_name}")
    if not os.path.exists(font_family_dir):
        tr_msg = tr("font directory does not exist.")
        log(message=f"'{dir_name}' {tr_msg}", info=False)

        return False

    status = True
    font_paths = Path(font_family_dir).glob("**/*")
    font_extensions = [".otf", ".ttf"]
    for font_path in font_paths:
        if font_path.suffix not in font_extensions:
            continue
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path.as_posix())
        if font_id == -1 and status:
            tr_msg = "font could not be installed."
            log(message=f"'{font_path}' {tr_msg}", info=False)
            status = False

    return status


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
    def get_fonts_dir() -> str:
        """Returns the fonts directory in the plugin.

        :returns: Fonts directory.
        :rtype: str
        """
        return f"{FileUtils.plugin_dir()}/data/fonts"

    @staticmethod
    def get_icon_path(file_name: str) -> str:
        """Gets the full path of the icon with the given name.

        :param file_name: File name which should include the extension.
        :type file_name: str

        :returns: The full path to the icon in the plugin.
        :rtype: str
        """
        return os.path.normpath(f"{FileUtils.plugin_dir()}/icons/{file_name}")

    @staticmethod
    def get_icon(file_name: str) -> QtGui.QIcon:
        """Creates an icon based on the icon name in the 'icons' folder.

        :param file_name: File name which should include the extension.
        :type file_name: str

        :returns: Icon object matching the file name.
        :rtype: QtGui.QIcon
        """
        icon_path = FileUtils.get_icon_path(file_name)

        if not os.path.exists(icon_path):
            return QtGui.QIcon()

        return QtGui.QIcon(icon_path)

    @staticmethod
    def get_pixmap(file_name: str) -> QtGui.QPixmap:
        """Creates a pixmap based on the file name in the 'icons' folder.

        :param file_name: File name which should include the extension.
        :type file_name: str

        :returns: Pixmap object matching the file name.
        :rtype: QtGui.QPixmap
        """
        pixmap_path = os.path.normpath(f"{FileUtils.plugin_dir()}/icons/{file_name}")

        if not os.path.exists(pixmap_path):
            return QtGui.QPixmap()

        return QtGui.QPixmap(pixmap_path)

    @staticmethod
    def report_template_path(file_name=None) -> str:
        """Get the absolute path to the template file with the given name.
        Caller needs to verify that the file actually exists.

        :param file_name: Template file name including the extension. If
        none is specified then it will use `scenario_analysis_default.qpt` as the default
        template name.
        :type file_name: str

        :returns: The absolute path to the template file with the given name.
        :rtype: str
        """
        if file_name is None:
            file_name = SCENARIO_ANALYSIS_TEMPLATE_NAME

        absolute_path = f"{FileUtils.plugin_dir()}/data/report_templates/{file_name}"

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
    def create_npv_pwls_dir(base_dir: str):
        """Creates an NPV PWL subdirectory under PWL child directory in the
        base directory. Skips creation of the subdirectory if it already
        exists.
        """
        if not Path(base_dir).is_dir():
            return

        npv_pwl_dir = (
            f"{base_dir}/{PRIORITY_LAYERS_SEGMENT}/{NPV_PRIORITY_LAYERS_SEGMENT}"
        )
        message = tr("Missing parent directory when creating NPV PWLs subdirectory.")
        FileUtils.create_new_dir(npv_pwl_dir, message)

    @staticmethod
    def create_comparison_reports_dir(base_dir: str):
        """Creates a comparison reports subdirectory under the base directory.
        Skips creation of the subdirectory if it already exists.
        """
        if not Path(base_dir).is_dir():
            return

        comparison_reports_dir = f"{base_dir}/{COMPARISON_REPORT_SEGMENT}"
        message = tr(
            "Missing parent directory when creating comparison reports subdirectory."
        )
        FileUtils.create_new_dir(comparison_reports_dir, message)

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
            return str(obj)
        if isinstance(obj, datetime.datetime):
            # if the obj is uuid, we simply return the value of uuid
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def todict(obj, classkey=None):
    """
    Convert any object to dictionary
    """

    if isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, dict):
        data = {}
        for k, v in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict(
            [
                (key, todict(value, classkey))
                for key, value in obj.__dict__.items()
                if not callable(value) and not key.startswith("_")
            ]
        )
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


def get_layer_type(file_path: str):
    """
    Get layer type code from file path
    """
    file_name, file_extension = os.path.splitext(file_path)
    if file_extension.lower() in [".tif", ".tiff"]:
        return 0
    elif file_extension.lower() in [".geojson", ".zip", ".shp"]:
        return 1
    else:
        return -1


def function_help_to_html(
    function_name: str,
    description: str,
    arguments: typing.List[tuple] = None,
    examples: typing.List[tuple] = None,
) -> str:
    """Creates a HTML string containing the detailed help of an expression function.

    The specific HTML formatting is deduced from the code here:
    https://github.com/qgis/QGIS/blob/master/src/core/expression/qgsexpression.cpp#L565

    :param function_name: Name of the expression function.
    :type function_name: str

    :param description: Detailed description of the function.
    :type description: str

    :param arguments: List containing the arguments. Each argument should consist of a
    tuple containing three elements i.e. argument name, description and bool where True
    will indicate the argument is optional. Take note of the order as mandatory
    arguments should be first in the list.
    :type arguments: typing.List[tuple]

    :param examples: Examples of using the function. Each item in the list should be
    a tuple containing an example expression and the corresponding return value.
    :type examples: typing.List[tuple]

    :returns: The expression function's help in HTML for use in, for example, an
    expression builder.
    :rtype: str
    """
    if arguments is None:
        arguments = []

    if examples is None:
        examples = []

    html_segments = []

    # Title
    html_segments.append(f"<h3>function {function_name}</h3>\n")

    # Description
    html_segments.append(f'<div class="description"><p>{description}</p></div>')

    # Syntax
    html_segments.append(
        f'<h4>Syntax</h4>\n<div class="syntax">\n<code>'
        f'<span class="functionname">{function_name}</span>'
        f"("
    )

    has_optional = False
    separator = ""
    for arg in arguments:
        arg_name = arg[0]
        arg_mandatory = arg[2]
        if not has_optional and arg_mandatory:
            html_segments.append("[")
            has_optional = True

        html_segments.append(separator)
        html_segments.append(f'<span class="argument">{arg_name}</span>')

        if arg_mandatory:
            html_segments.append("]")

        separator = ","

    html_segments.append(")</code>")

    if has_optional:
        html_segments.append("<br/><br/>[ ] marks optional components")

    # Arguments
    if len(arguments) > 0:
        html_segments.append('<h4>Arguments</h4>\n<div class="arguments">\n<table>')
        for arg in arguments:
            arg_name = arg[0]
            arg_description = arg[1]
            html_segments.append(
                f'<tr><td class="argument">{arg_name}</td><td>{arg_description}</td></tr>'
            )

        html_segments.append("</table>\n</div>\n")

    # Examples
    if len(examples) > 0:
        html_segments.append('<h4>Examples</h4>\n<div class="examples">\n<ul>\n')
        for example in examples:
            expression = example[0]
            return_value = example[1]
            html_segments.append(
                f"<li><code>{expression}</code> &rarr; <code>{return_value}</code>"
            )

        html_segments.append("</ul>\n</div>\n")

    return "".join(html_segments)


def convert_size(size_bytes):
    """Convert byte size to human readable text.

    :param size_bytes: byte sizse
    :type size_bytes: int
    :return: human readable text
    :rtype: str
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
