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
import shutil
import traceback
from zipfile import ZipFile

import numpy as np
from osgeo import gdal
from scipy.ndimage import label

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
    QgsUnitTypes,
    QgsRasterBlock,
    Qgis,
    QgsRasterPipe,
    QgsRasterDataProvider,
    QgsRasterFileWriter,
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
from .models.base import ModelComponentType
from .models.constant_raster import ConstantRasterFileMetadata


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


def format_value_with_unit(value: float, metadata_id: str) -> str:
    """Format a value with an appropriate unit suffix for filename.

    The unit is determined based on the metadata_id. Common patterns:
    - Years/experience: "5years", "10years"
    - Percentage: "25pct", "50pct"
    - Weight: "10kg", "25kg"
    - Default: "12p50" (12.50 with decimal point as 'p')

    :param value: The numeric value
    :type value: float

    :param metadata_id: Metadata ID to determine the appropriate unit
    :type metadata_id: str

    :returns: Formatted string like "5years", "10pct", "25kg"
    :rtype: str
    """
    if "year" in metadata_id.lower() or "experience" in metadata_id.lower():
        return f"{int(value)}years"
    elif "percent" in metadata_id.lower() or "pct" in metadata_id.lower():
        return f"{int(value)}pct"
    elif "weight" in metadata_id.lower() or "kg" in metadata_id.lower():
        return f"{int(value)}kg"
    else:
        return f"{value:.2f}".replace(".", "p")


def get_constant_raster_dir(
    base_dir: str, component_type: ModelComponentType, metadata_id: str
) -> str:
    """Get the directory path for constant rasters.

    Creates a hierarchical directory structure:
    {base_dir}/{component_type}/{raster_type}/

    :param base_dir: Base directory (e.g., "BASE_DIR/constant_rasters")
    :type base_dir: str

    :param component_type: Type of model component (NCS_PATHWAY or ACTIVITY)
    :type component_type: ModelComponentType

    :param metadata_id: Raster type ID (e.g., "years_experience_pathway")
    :type metadata_id: str

    :returns: Full path to the constant raster directory
    :rtype: str
    """
    if component_type == ModelComponentType.NCS_PATHWAY:
        type_dir = "ncs_pathway"
    elif component_type == ModelComponentType.ACTIVITY:
        type_dir = "activity"
    else:
        type_dir = "unknown"

    raster_type = metadata_id
    if raster_type.endswith("_pathway") or raster_type.endswith("_activity"):
        raster_type = "_".join(raster_type.split("_")[:-1])

    return os.path.join(base_dir, type_dir, raster_type)


def generate_constant_raster_filename(
    component_name: str, value: float, metadata_id: str
) -> str:
    """Generate a descriptive filename for a constant raster.

    Follows the pattern: {sanitized_component_name}_{value_with_unit}.tif

    Example outputs:
    - "agroforestry_5years.tif"
    - "corn_production_25pct.tif"
    - "animal_management_10kg.tif"

    :param component_name: Name of the pathway/activity
    :type component_name: str

    :param value: The constant value for this raster
    :type value: float

    :param metadata_id: Metadata ID to determine the value unit
    :type metadata_id: str

    :returns: Safe filename with extension
    :rtype: str
    """
    safe_name = clean_filename(component_name)
    value_str = format_value_with_unit(value, metadata_id)
    return f"{safe_name}_{value_str}.tif"


def write_constant_raster_metadata_file(
    metadata: ConstantRasterFileMetadata, file_path: str
) -> str:
    """Write constant raster metadata to a text file.

    :param metadata: ConstantRasterFileMetadata instance with all metadata information
    :type metadata: ConstantRasterFileMetadata

    :param file_path: Path where the metadata file should be written
    :type file_path: str

    :returns: Path to the metadata file that was written
    :rtype: str
    """
    with open(file_path, "w") as f:
        f.write(metadata.to_text())

    return file_path


def save_constant_raster_metadata(
    metadata: ConstantRasterFileMetadata, raster_dir: str
) -> str:
    """Save metadata for a constant raster to a text file.

    Creates a .meta.txt file alongside the raster with information
    about how it was created.

    :param metadata: ConstantRasterFileMetadata with all metadata information
    :type metadata: ConstantRasterFileMetadata

    :param raster_dir: Directory where the raster file is located
    :type raster_dir: str

    :returns: Path to the metadata file
    :rtype: str
    """
    # Use raster_path from metadata if available, otherwise use component_name
    if metadata.raster_path:
        raster_basename = os.path.splitext(os.path.basename(metadata.raster_path))[0]
    else:
        # When skip_raster=True, use component_name for metadata filename
        raster_basename = clean_filename(metadata.component_name)

    metadata_subfolder = os.path.join(raster_dir, "metadata")
    os.makedirs(metadata_subfolder, exist_ok=True)

    meta_path = os.path.join(metadata_subfolder, f"{raster_basename}.txt")
    return write_constant_raster_metadata_file(metadata, meta_path)


def calculate_raster_area_by_pixel_value(
    layer: QgsRasterLayer, band_number: int = 1, feedback: QgsProcessingFeedback = None
) -> dict:
    """Calculates the area of value pixels in hectares for the given band in a
    raster layer and groups the area by the pixel value.

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

    This varies from 'calculate_raster_area_by_pixel_value' in that it
    gives the total area instead of grouping by pixel value.

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

    # Remove NoData pixels from the computation, just in case the process
    # calculation might have sneaked it in.
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
                p.mkdir(parents=True, exist_ok=True)
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

    @staticmethod
    def copy_file(file_path: str, target_dir: str, log_message: str = ""):
        """Copies file to the target directory"""
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File {file_path} does not exist")

        target_path = Path(target_dir) / p.name
        if not target_path.parent.exists():
            target_path.parent.mkdir(parents=True)

        shutil.copy(p, target_path)
        if not target_path.exists():
            raise FileNotFoundError(f"Failed to copy file to {target_dir}")
        return str(target_path)


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


def zip_shapefile(shapefile_path: str) -> str:
    """Zip shapefile to an object with same name.
    For example, the .shp filename is `test_file.shp`, then the zip file
    name would be `test_file.zip`

    :param shapefile_path: Path of the shapefile
    :type shapefile_path: str

    :return: Zip file path if the specified `shapefile_path`
        ends with .shp, return shapefile_path otherwise
    :rtype: str
    """

    if shapefile_path.endswith(".shp"):
        output_dir = os.path.dirname(shapefile_path)
        filename_without_ext = os.path.splitext(os.path.basename(shapefile_path))[0]
        zip_name = shapefile_path.replace(".shp", ".zip")
        with ZipFile(zip_name, "w") as zip:
            # writing each file one by one
            for file in [
                f
                for f in os.listdir(output_dir)
                if filename_without_ext in f and not f.endswith("zip")
            ]:
                zip.write(os.path.join(output_dir, file), file)
        return zip_name
    return shapefile_path


def compress_raster(
    input_path: str,
    output_path: str = None,
    compression_type: str = "DEFLATE",
    compress_level: int = 6,
    nodata_value: float = None,
    output_format: str = "GTiff",
    create_options: list = None,
    additional_options: list = None,
):
    """
    Compresses a raster file using GDAL and optionally replace old NoData pixel values with a new one.

    :param input_path: Path to the input raster file
    :type input_path: str

    :param output_path: Path to the input raster file. If none the ouput will saved to a temporary file
    :type output_path: str

    :param compression_type: Compression algorithm (e.g., 'DEFLATE', 'LZW', 'PACKBITS', 'JPEG', 'NONE')
    :type compression_type: str

    :param compress_level: Compression level (1-9 for DEFLATE/LZW, 1-100 for JPEG)
    :type compress_level: int

    :param nodata_value: Value to set as nodata (default: None). If None, retain the input nodatavalue
    :type nodata_value: float

    :param output_format: Output format (default: 'GTiff' for GeoTIFF)
    :type output_format: str

    :param create_options: Additional GDAL creation options as a list
    :type create_options: list

    :param additional_options: dditional GDAL options as a list
    :type additional_options: list

    :return: Path to the temporary file if successful, None if failed
    :rtype: str or None
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input raster file not found: {input_path}")

    # Create a temporary file if output_path is None:
    if not output_path:
        unique_id = str(uuid.uuid4())[:8]
        temp_file = QtCore.QTemporaryFile(
            os.path.join(
                QgsProject.instance().homePath(), f"temp_compressed_{unique_id}.tif"
            )
        )
        if not temp_file.open():
            log("Error: Could not create temporary file")
            return None

        base, ext = os.path.splitext(input_path)
        output_path = temp_file.fileName() + ext or ".tif"
        temp_file.close()

    try:
        # Load the input raster layer using GDAL
        src_ds = gdal.Open(input_path, gdal.GA_ReadOnly)
        if src_ds is None:
            raise ValueError("Unable to open raster with GDAL")

        band_count = src_ds.RasterCount
        xsize = src_ds.RasterXSize
        ysize = src_ds.RasterYSize
        dtype = src_ds.GetRasterBand(1).DataType

        compression = src_ds.GetMetadataItem("COMPRESSION", "IMAGE_STRUCTURE")
        if compression.lower() == "deflate":
            log(f"Raster {input_path} is already compressed with DEFLATE.")
            return input_path

        # Add any additional create options
        if not create_options:
            create_options = []

        # Ensure standard options are included
        create_options.extend(
            [
                f"COMPRESS={compression_type}",
                f"ZLEVEL={compress_level}",
                f"JPEG_QUALITY={compress_level}",
                f"NUM_THREADS=ALL_CPUS",
                "BIGTIFF=IF_SAFER",
                "TILED=YES",
            ]
        )

        # Set additional options if provided
        if additional_options:
            create_options.extend(additional_options)

        # Create compressed output raster
        driver = gdal.GetDriverByName(output_format)
        out_ds = driver.Create(
            output_path, xsize, ysize, band_count, dtype, create_options
        )
        out_ds.SetGeoTransform(src_ds.GetGeoTransform())
        out_ds.SetProjection(src_ds.GetProjection())

        for i in range(1, band_count + 1):
            band = src_ds.GetRasterBand(i)
            data = band.ReadAsArray()
            old_nodata = band.GetNoDataValue()

            # Replace pixel values if old NoData exists
            if nodata_value is not None and old_nodata is not None:
                data = np.where(data == old_nodata, nodata_value, data)

            out_band = out_ds.GetRasterBand(i)
            out_band.WriteArray(data)
            out_band.SetNoDataValue(nodata_value)
            out_band.FlushCache()

        # Close datasets
        src_ds = None
        # if os.path.exists(output_path):
        log(f"Successfully compressed raster saved to temporary file: {output_path}")
        return output_path
    except Exception as error:
        log(f"Error occurred during raster compression. Error code: {error}")
        return None


def raster_from_array(
    array, extent, crs, output_path=None, layer_name="Numpy Raster"
) -> QgsRasterLayer:
    """
    Create a QGIS raster layer from a numpy array

    :param array: Input numpy array (2D or 3D)
    :type array: ndarray

    :param extent: QgsRectangle with the extent in CRS coordinates
    :type extent: QgsRectangle

    :param crs: Coordinate system
    :type crs: QgsCoordinateReferenceSystem

    :param output_path: Optional path to save as GeoTIFF (if None, creates temporary layer)
    :type output_path: str

    :param layer_name: Optional name for the layer
    :type layer_name: str

    Returns:
    QgsRasterLayer
    """

    # Determine data type based on numpy array dtype
    dtype_map = {
        np.uint8: Qgis.Byte,
        np.int16: Qgis.Int16,
        np.uint16: Qgis.UInt16,
        np.int32: Qgis.Int32,
        np.uint32: Qgis.UInt32,
        np.float32: Qgis.Float32,
        np.float64: Qgis.Float64,
    }

    data_type = dtype_map.get(array.dtype.type, Qgis.Float32)

    # Get array dimensions
    if array.ndim == 2:
        height, width = array.shape
        bands = 1
        # Reshape to 3D for consistent processing
        array = array.reshape(1, height, width)
    elif array.ndim == 3:
        bands, height, width = array.shape
    else:
        raise ValueError("Array must be 2D or 3D")

    if output_path:
        # Create a raster file writer
        writer = QgsRasterFileWriter(output_path)
        writer.setOutputProviderKey("gdal")
        writer.setOutputFormat("GTiff")

        # Create the output raster
        provider = writer.createOneBandRaster(data_type, width, height, extent, crs)
    else:
        # Create a temporary memory layer
        provider = QgsRasterDataProvider("memory", "1", data_type, width, height, 1)

    # Set the data for each band
    for band in range(bands):
        # Create raster block
        block = QgsRasterBlock(data_type, width, height)

        # Convert numpy array to bytes for the block
        if array.dtype == np.float32:
            data_bytes = array[band].tobytes()
        else:
            # Ensure correct byte order
            data_bytes = array[band].astype(array.dtype.newbyteorder("=")).tobytes()

        # Write data to block
        block.setData(data_bytes)

        # Write block to provider
        provider.writeBlock(block, band + 1)

        # Set NoData value to 0
        provider.setNoDataValue(band + 1, 0)

    if output_path:
        provider.setEditable(False)
        raster_layer = QgsRasterLayer(output_path, layer_name)
    else:
        # For memory provider, we need to create a proper raster layer
        # This is a workaround since memory provider doesn't easily create layers
        uri = f"MEM::{width}:{height}:{bands}:{data_type}:[{extent.xMinimum()},{extent.yMinimum()},{extent.xMaximum()},{extent.yMaximum()}]"
        raster_layer = QgsRasterLayer(uri, layer_name, "memory")
        # Copy the data (simplified approach)
        pipe = QgsRasterPipe()
        pipe.set(provider.clone())
        raster_layer = QgsRasterLayer(pipe, layer_name)

    # Set CRS
    raster_layer.setCrs(crs)

    return raster_layer


def array_from_raster(input_layer: QgsRasterLayer):
    """
    Read a raster and return the pixel values as numpy array

    :param input_layer: Input raster layer
    :type input_layer: QgsRasterLayer

    :return: Pixel values as numpy array
    :rtype: ndarray

    """
    provider = input_layer.dataProvider()
    extent = provider.extent()
    height, width = input_layer.height(), input_layer.width()
    block = provider.block(1, extent, width, height)  # assuming single band raster
    array = np.zeros((height, width), dtype=np.float32)
    for i in range(height):
        for j in range(width):
            array[i, j] = block.value(i, j)

    return array


def create_connectivity_raster(
    input_raster_path: str,
    output_raster_path: str,
    connectivity_type: int = 8,
    min_patch_area: float = None,
    area_unit: str = "ha",
):
    """
    Computes the pixel connectivity of a given binary raster

    :param input_raster_path: Input layer path
    :type input_raster_path: str

    :param output_raster_path: Output layer path
    :type output_raster_path: str

    :param connectivity_type: Number of pixels reachable from the
        specified pixel in 4- or 8-directional adjacency
        For 4-directional connectivity → N, S, E, W adjacency
        For 8-directional connectivity → N, S, E, W, NE, NW, SE, SW adjacency
        Default to 8
    :type connectivity_type: int

    :param min_patch_area: Minimum patch size, default to None
    :type min_patch_area: float | None

    :param area_unit: Unit of the patch size i.e ha or m2, defaulto to ha
    :type area_unit: str
    """

    logs = []

    try:
        # -----------------------
        # 1. Load raster
        # -----------------------
        input_layer = QgsRasterLayer(input_raster_path, "raster")
        if not input_layer.isValid():
            logs.append(f"Invalid raster {input_raster_path}")
            return False, logs

        arr = array_from_raster(input_layer)
        height, width = input_layer.height(), input_layer.width()

        provider = input_layer.dataProvider()
        if provider.sourceHasNoDataValue(1):
            # Convert NoData value to 0
            nodata_value = provider.sourceNoDataValue(1)
            arr[arr == nodata_value] = 0.0

        # Expecting a normalized raster 0-1. Convert any value greater than 1 to 0
        arr[arr > 1] = 0.0

        # Convert to binary to ignore resistance caused by varying pixel values
        arr = (arr > 0).astype(np.uint8)

        # Just need gdal to get the raster GeoTransform.
        # Cannot directly get it from qgis rasterlayer because layer.rasterUnitsPerPixelY() is absolute
        # gt = [extent.xMinimum(), layer.rasterUnitsPerPixelX(), 0, extent.yMaximum(), 0, layer.rasterUnitsPerPixelY()]
        gdal_ds = gdal.Open(input_raster_path)
        gt = gdal_ds.GetGeoTransform()
        gdal_ds = None

        # pixel size in map units (assume square pixels)
        px_w = abs(gt[1])
        px_h = abs(gt[5]) if gt[5] != 0 else px_w

        # use average pixel size (map units) for distance scaling
        pixel_size = math.sqrt(px_w * px_h)

        # Minimum number of pixels to discriminate
        MIN_SIZE_PENALTY_K = 100
        EPS = 1e-12

        # -----------------------
        # 2. Determine the number of pixels for the minimum patch area
        # -----------------------

        if min_patch_area:
            pixel_area_m2 = abs(px_w * px_h)
            if area_unit.lower() == "ha":
                min_patch_area_m2 = min_patch_area * 10000.0
            elif area_unit.lower() == "m2":
                min_patch_area_m2 = min_patch_area
            else:
                logs.append("Patch Area Unit must be 'ha' or 'm2'")
                return False, logs

            MIN_SIZE_PENALTY_K = int(math.ceil(min_patch_area_m2 / pixel_area_m2))

        # -----------------------
        # 3. Compute connected clusters
        # -----------------------
        if connectivity_type == 4:
            struct = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
        else:
            struct = np.ones((3, 3), dtype=np.uint8)

        labeled, n_labels = label(arr == 1, structure=struct)

        cluster_size_array = np.zeros_like(labeled, dtype=np.int32)
        centroid_mean_dist_array = np.zeros_like(labeled, dtype=np.float32)
        raw_score_array = np.zeros_like(labeled, dtype=np.float32)

        # precompute pixel coordinates in map units
        rows, cols = np.indices((height, width))

        # centroid coords = pixel center: x = gt[0] + (col + 0.5)*gt[1] + (row + 0.5)*gt[2] (usually gt[2]==0)
        # y = gt[3] + (col + 0.5)*gt[4] + (row + 0.5)*gt[5] (usually gt[4]==0)

        xs = gt[0] + (cols + 0.5) * gt[1] + (rows + 0.5) * gt[2]
        ys = gt[3] + (cols + 0.5) * gt[4] + (rows + 0.5) * gt[5]

        # iterate clusters
        cluster_scores = []
        for lbl in range(1, n_labels + 1):
            mask = labeled == lbl
            S = int(mask.sum())
            cluster_size_array[mask] = S

            # coordinates of pixels in map units (N x 2)
            xs_pix = xs[mask].astype(float)
            ys_pix = ys[mask].astype(float)
            pts = np.column_stack((xs_pix, ys_pix))

            if S == 1:
                # Single pixel: distance = 0
                mean_dist = 0.0
            else:
                # centroid
                centroid = pts.mean(axis=0)
                # compute distances from pixels to cluster centroid (map units)
                dists = np.linalg.norm(pts - centroid, axis=1)
                mean_dist = float(dists.mean())

            centroid_mean_dist_array[mask] = mean_dist

            # estimate cluster radius from area: pixel_area * S
            pixel_area = abs(gt[1] * gt[5]) if gt[5] != 0 else (px_w * px_h)
            cluster_area = S * pixel_area
            if cluster_area <= 0:
                r_est = pixel_size / 2.0
            else:
                r_est = math.sqrt(cluster_area / math.pi)

            denom = r_est if r_est > 0 else (pixel_size / 2.0)
            compactness = math.exp(-(mean_dist / (denom + EPS)))

            k = float(MIN_SIZE_PENALTY_K)
            size_penalty = 1.0 / (1.0 + math.exp(-(S - k) / (k + EPS)))  # ranges ~0..1

            raw_score = S * compactness * size_penalty

            raw_score_array[mask] = raw_score
            cluster_scores.append(raw_score)

        if len(cluster_scores) == 0:
            logs.append(f"No clusters found for raster {input_raster_path}")
            return False, logs

        # Normalize raw_score_array over pixels that belong to clusters
        mask_clusters = cluster_size_array > 0
        raw_vals = raw_score_array[mask_clusters]
        min_raw = float(np.nanmin(raw_vals))
        max_raw = float(np.nanmax(raw_vals))
        if abs(max_raw - min_raw) < EPS:
            norm_score_array = np.zeros_like(raw_score_array, dtype=np.float32)
            norm_score_array[mask_clusters] = 1.0
        else:
            norm_score_array = np.zeros_like(raw_score_array, dtype=np.float32)
            norm_score_array[mask_clusters] = (
                raw_score_array[mask_clusters] - min_raw
            ) / (max_raw - min_raw)

        # Ignore clusters with pixels less than MIN_SIZE_PENALTY_K
        # norm_score_array[cluster_size_array < MIN_SIZE_PENALTY_K] = 0

        output_layer = raster_from_array(
            norm_score_array,
            input_layer.extent(),
            input_layer.crs(),
            output_raster_path,
        )
        if output_layer and output_layer.isValid():
            return True, logs

    except Exception as e:
        logs.append(f"Problem occured when creating connectivity layer, {str(e)}.")
        logs.append(traceback.format_exc())

    return False, logs
