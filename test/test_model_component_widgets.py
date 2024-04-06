# -*- coding: utf-8 -*-
"""
Unit tests for model component widgets.
"""

from unittest import TestCase

from qgis.PyQt import QtCore


from cplus_plugin.gui.component_item_model import NcsPathwayItem
from cplus_plugin.gui.model_component_widget import (
    ActivityComponentWidget,
    NcsComponentWidget,
)


from model_data_for_testing import (
    get_activity,
    get_test_layer,
    get_valid_ncs_pathway,
    ACTIVITY_UUID_STR,
)
from utilities_for_testing import get_qgis_app


QGIS_APP, CANVAS, IFACE, PARENT = get_qgis_app()


class TestNcsComponentWidget(TestCase):
    """Tests for NcsComponentWidget."""

    def test_add_valid_ncs_pathway(self):
        """Assert a valid NCS pathway can be added to the widget."""
        ncs = get_valid_ncs_pathway()
        ncs_widget = NcsComponentWidget(PARENT)
        result = ncs_widget.add_ncs_pathway(ncs)
        self.assertTrue(result)

    def test_get_valid_ncs_pathways(self):
        """Assert number of NcsPathway objects retrieved."""
        valid_ncs = get_valid_ncs_pathway()
        ncs_widget = NcsComponentWidget(PARENT)
        _ = ncs_widget.add_ncs_pathway(valid_ncs)
        pathways = ncs_widget.pathways()
        self.assertEqual(len(pathways), 1)

    def test_clear_ncs_pathways(self):
        """Assert NcsPathway objects are cleared."""
        valid_ncs = get_valid_ncs_pathway()
        ncs_widget = NcsComponentWidget(PARENT)
        _ = ncs_widget.add_ncs_pathway(valid_ncs)
        ncs_widget.clear()
        pathways = ncs_widget.pathways()
        self.assertEqual(len(pathways), 0)


class TestActivityComponentWidget(TestCase):
    """Tests for ActivityComponentWidget."""

    def test_add_activity(self):
        """Assert an activity object can be added
        to the widget.
        """
        activity = get_activity()
        activity_widget = ActivityComponentWidget(PARENT)
        result = activity_widget.add_activity(activity)
        self.assertTrue(result)

    def test_add_activity_with_layer(self):
        """Assert an activity object with a layer
        can be added to the widget.
        """
        activity = get_activity()
        layer = get_test_layer()
        activity_widget = ActivityComponentWidget(PARENT)
        result = activity_widget.add_activity(activity, layer)
        self.assertTrue(result)

    def test_get_activities(self):
        """Assert number of activity objects retrieved."""
        activity = get_activity()
        activity_widget = ActivityComponentWidget(PARENT)
        _ = activity_widget.add_activity(activity)
        activities = activity_widget.activities()
        self.assertEqual(len(activities), 1)

    def test_clear_activities(self):
        """Assert activities objects can be cleared."""
        activity = get_activity()
        activity_widget = ActivityComponentWidget(PARENT)
        _ = activity_widget.add_activity(activity)
        activity_widget.clear()
        activities = activity_widget.activities()
        self.assertEqual(len(activities), 0)

    def test_can_add_ncs_pathway_items(self):
        """Assert ncsPathwayItem objects can be added to the
        widget to an activity without a layer.
        """
        activity = get_activity()
        activity.clear_layer()
        activity_widget = ActivityComponentWidget(PARENT)
        _ = activity_widget.add_activity(activity)

        # Select the added activity.
        sel_model = activity_widget.selection_model
        item_model = activity_widget.item_model
        model_idx = item_model.index_by_uuid(ACTIVITY_UUID_STR)
        sel_model.select(model_idx, QtCore.QItemSelectionModel.ClearAndSelect)

        # Now we can add the NcsPathwayItem
        ncs = get_valid_ncs_pathway()
        ncs_item = NcsPathwayItem(ncs)
        result = activity_widget.add_ncs_pathway_items([ncs_item])
        self.assertTrue(result)

    def test_cannot_add_ncs_pathway_items(self):
        """Assert ncsPathwayItem objects cannot be added to the
        widget as the activity has a layer defined.
        """
        activity = get_activity()
        activity_widget = ActivityComponentWidget(PARENT)
        _ = activity_widget.add_activity(activity)

        # Select the added activity.
        sel_model = activity_widget.selection_model
        item_model = activity_widget.item_model
        model_idx = item_model.index_by_uuid(ACTIVITY_UUID_STR)
        sel_model.select(model_idx, QtCore.QItemSelectionModel.ClearAndSelect)

        # Now we can add the NcsPathwayItem
        ncs = get_valid_ncs_pathway()
        ncs_item = NcsPathwayItem(ncs)
        result = activity_widget.add_ncs_pathway_items([ncs_item])
        self.assertFalse(result)
