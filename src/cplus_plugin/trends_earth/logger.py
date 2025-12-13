import typing

import qgis.core
from qgis.core import Qgis


def log(message: str, level: typing.Optional[int] = 0):
    # Convert int level to Qgis.MessageLevel enum for QGIS 4 compatibility
    if isinstance(level, int):
        level_map = {
            0: Qgis.MessageLevel.Info if hasattr(Qgis, 'MessageLevel') else Qgis.Info,
            1: Qgis.MessageLevel.Warning if hasattr(Qgis, 'MessageLevel') else Qgis.Warning,
            2: Qgis.MessageLevel.Critical if hasattr(Qgis, 'MessageLevel') else Qgis.Critical,
            3: Qgis.MessageLevel.Success if hasattr(Qgis, 'MessageLevel') else Qgis.Success,
        }
        level = level_map.get(level, Qgis.MessageLevel.Info if hasattr(Qgis, 'MessageLevel') else Qgis.Info)
    qgis.core.QgsMessageLog.logMessage(message, tag="trends.earth", level=level)
