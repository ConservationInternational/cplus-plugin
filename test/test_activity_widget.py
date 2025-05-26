from unittest import TestCase
from unittest.mock import MagicMock
from qgis.gui import QgsMessageBar
from cplus_plugin.gui.activity_widget import ActivityContainerWidget
from cplus_plugin.models.base import Activity, NcsPathway
from cplus_plugin.gui.component_item_model import ActivityItem, NcsPathwayItem
from model_data_for_testing import get_activity, get_valid_ncs_pathway
from utilities_for_testing import get_qgis_app

QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestActivityContainerWidget(TestCase):
    """Tests for ActivityContainerWidget."""

    def setUp(self):
        self.message_bar = MagicMock(spec=QgsMessageBar)
        self.widget = ActivityContainerWidget(PARENT, message_bar=self.message_bar)

    def test_items_load(self):
        """Assert NCS pathway and activity items have already been loaded
        in their respective views.
        """
        self.assertTrue(self.widget.items_loaded)

    def test_ncs_pathways(self):
        """Assert NCS pathways retrieval."""
        self.widget.ncs_pathway_view.pathways = MagicMock(
            return_value=[get_valid_ncs_pathway()]
        )
        self.assertEqual(len(self.widget.ncs_pathways()), 1)

    def test_activities(self):
        """Assert activities retrieval."""
        self.widget.activity_view.activities = MagicMock(return_value=[get_activity()])
        self.assertEqual(len(self.widget.activities()), 1)

    def test_add_ncs_pathway(self):
        """Assert adding an NCS pathway."""
        self.widget.ncs_pathway_view.selected_items = MagicMock(
            return_value=[NcsPathwayItem(get_valid_ncs_pathway())]
        )
        self.widget.activity_view.add_ncs_pathway_items = MagicMock()
        self.widget._on_add_ncs_pathway()
        self.widget.activity_view.add_ncs_pathway_items.assert_called_once()

    def test_add_all_ncs_pathways(self):
        """Assert adding all NCS pathways."""
        self.widget.ncs_pathway_view.ncs_items = MagicMock(
            return_value=[MagicMock(), MagicMock()]
        )
        self.widget.activity_view.add_ncs_pathway_items = MagicMock()
        self.widget._on_add_all_ncs_pathways()
        self.widget.activity_view.add_ncs_pathway_items.assert_called_once()

    def test_show_message(self):
        """Assert message display functionality."""
        self.widget.show_message("Test Message")
        self.message_bar.pushMessage.assert_called_once()

    def test_ncs_validity(self):
        """Assert NCS pathway validation."""
        self.widget.ncs_pathway_view.is_valid = MagicMock(return_value=True)
        self.assertTrue(self.widget.is_ncs_valid())

    def test_activity_validity(self):
        """Assert activity validation logic."""
        activity = MagicMock()
        activity.pathways = [MagicMock()]
        self.widget.activities = MagicMock(return_value=[activity])
        self.assertTrue(self.widget.is_activity_valid())

    def test_selected_items(self):
        """Assert retrieval of selected items."""
        activity_item = ActivityItem(get_activity())
        self.widget.activity_view.selected_items = MagicMock(
            return_value=[activity_item]
        )
        self.assertEqual(len(self.widget.selected_items()), 1)

    def test_selected_activity_items(self):
        """Assert selected activity items retrieval."""
        activity_item = ActivityItem(get_activity())
        self.widget.selected_items = MagicMock(return_value=[activity_item])
        self.assertEqual(len(self.widget.selected_activity_items()), 1)
