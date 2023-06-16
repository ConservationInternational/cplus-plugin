# -*- coding: utf-8 -*-
"""
Container widget for configuring the implementation widget.
"""


import os

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets
)

from qgis.PyQt.uic import loadUiType

from.model_component_widget import ModelComponentWidget

from ..utils import FileUtils


WidgetUi, _ = loadUiType(
    os.path.join(
        os.path.dirname(__file__),
        "../ui/implementation_model_container_widget.ui"
    )
)


class ImplementationModelContainerWidget(QtWidgets.QWidget, WidgetUi):
    """Widget for configuring the implementation model."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.btn_add_one.setIcon(FileUtils.get_icon("play.svg"))
        self.btn_add_one.setToolTip(self.tr("Add selected NCS pathway"))

        self.btn_add_all.setIcon(FileUtils.get_icon("forward.svg"))
        self.btn_add_all.setToolTip(self.tr("Add all NCS pathways"))

        # NCS pathway view
        self.ncs_pathway_view = ModelComponentWidget()
        self.ncs_pathway_view.title = self.tr("NCS Pathways")
        self.ncs_layout.addWidget(self.ncs_pathway_view)

        # Implementation model view
        self.implementation_model_view = ModelComponentWidget()
        self.ipm_layout.addWidget(self.implementation_model_view)
        self.implementation_model_view.title = self.tr(
            "Implementation Models"
        )

