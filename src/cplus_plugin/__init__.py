# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QgisCplus

 A QGIS plugin that enables usage of the CPLUS framework in land-use planning.
                             -------------------
        begin                : 2021-11-15
        copyright            : (C) 2021 by Kartoza
        email                : info@kartoza.com
        git sha              : $Format:%H$
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
import os
import sys
import site
from pathlib import Path

LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "lib"))
if LIB_DIR not in sys.path:
    sys.path.append(LIB_DIR)


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load QgisCplus class
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """

    from .main import QgisCplus

    return QgisCplus(iface)
