import unittest

from utilities_for_testing import get_qgis_app
#from qgis.core import QgsProject
#from qgis.gui import QgsMapCanvasLayer
#from qgis_interface import QgisInterface

QGIS_APP = get_qgis_app()


class CplusPluginSettingsTest(unittest.TestCase):
    def test_open_settings(self):
        print('\n\n\nOPEN SETTINGS123')

        print(str(get_qgis_app()))

        self.assertEqual(True, False)  # add assertion here

        print('\n\n\nEND')
