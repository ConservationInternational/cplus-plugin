# -*- coding: utf-8 -*-
"""
Contains item models for view widgets such as NCS pathway or IM views.
"""
import typing

from qgis.PyQt import (
    QtCore,
    QtGui,
    QtWidgets
)

from ..models.base import (
    LayerType,
    NcsPathway
)


class NcsPathwayItem(QtGui.QStandardItem):
    """Model item for an NCS pathway object."""

    def __int__(self, *args, **kwargs):
        super().__init(*args, **kwargs)

        self._ncs_pathway = kwargs.pop("ncs", None)
        if self._ncs_pathway is not None:
            self.update(self._ncs_pathway)

    def update(self, ncs: NcsPathway):
        """Update the NCS pathway-related properties of the item."""
        if ncs is None:
            return

        self._ncs_pathway = ncs
        self.setText(ncs.name)

    @property
    def ncs_pathway(self) -> typing.Union[NcsPathway, None]:
        """Returns the underlying :ref:`NcsPathway` object.

        :returns: Referenced :ref:`NcsPathway` object.
        :rtype: NcsPathway
        """
        return self._ncs_pathway

    @property
    def uuid(self) -> str:
        """Returns the UUID of the item.

        :returns: UUID of the item.
        :rtype: str
        """
        if self._ncs_pathway is None:
            return ""

        return str(self._ncs_pathway.uuid)

    @property
    def description(self) -> str:
        """Returns the description of the item.

        :returns: Description of the item.
        :rtype: str
        """
        if self._ncs_pathway is None:
            return ""

        return str(self._ncs_pathway.description)

    def is_valid(self) -> bool:
        """Checks if the map layer of the underlying :ref:`NcsPathway` is valid.

        :returns: True if the map layer is valid, else False if map layer is
        invalid or of None type.
        :rtype: bool
        """
        if self._ncs_pathway is None:
            return False

        return self._ncs_pathway.is_valid()
