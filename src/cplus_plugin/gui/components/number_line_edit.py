"""
Line edit that allows the formatting of number values using QgsBasicNumericFormat.
"""

import numbers
import typing

from qgis.core import QgsBasicNumericFormat, QgsNumericFormatContext

from qgis.PyQt import QtCore, QtGui, QtWidgets


class NumberFormattableLineEdit(QtWidgets.QLineEdit):
    """Line edit that allows the formatting of number values
    using QgsBasicNumericFormat.
    """

    DISPLAY_DECIMAL_PLACES = 2

    # Signal emitted after value has been updated - contains None or
    # a float value
    value_updated = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._value = None

        # Flag to indicate whether the text is set
        # internally by this class.
        self._internal_update = False

        # Set validator
        self._validator = QtGui.QDoubleValidator()
        self._validator.setDecimals(self.DISPLAY_DECIMAL_PLACES)
        self.setValidator(self._validator)

        # Set display formatter
        self._formatter = QgsBasicNumericFormat()
        self._formatter.setShowThousandsSeparator(True)
        self._formatter.setNumberDecimalPlaces(self.DISPLAY_DECIMAL_PLACES)

        self.editingFinished.connect(self._on_editing_finished)

    @property
    def value(self) -> typing.Optional[float]:
        """Gets the absolute value used in the control.

        :returns: Absolute value used in the widget or None if
        not yet specified or if the control is empty.
        :rtype: float
        """
        return self._value

    @value.setter
    def value(self, value: float):
        """Sets the absolute value to be used in the control.

        This will validate whether the value is a number. If not,
        it will not be applied.

        :param value: Value to be used in the control.
        :type value: float
        """
        if not isinstance(value, numbers.Number):
            return

        self._value = value
        self._update_displayed_text()

    @property
    def decimal_places(self) -> int:
        """Returns the maximum number of decimal places to show.

        The default is two decimal places.

        :returns: The maximum number of decimal places to show.
        :rtype: int
        """
        return self._formatter.numberDecimalPlaces()

    @decimal_places.setter
    def decimal_places(self, places: int):
        """Sets the maximum number of decimal places to show.

        :param places: Maximum of decimal places to show.
        :type places: int
        """
        if places == self.decimal_places:
            return

        self._formatter.setNumberDecimalPlaces(places)
        self._validator.setDecimals(places)

        self._update_displayed_text()

    def _update_displayed_text(self):
        """Updates the displayed value based on the formatter
        configuration.
        """
        if self._value is None:
            self.clear()

        else:
            display_value = self._formatter.formatDouble(
                self._value, QgsNumericFormatContext()
            )
            super().setText(display_value)

        self.value_updated.emit(self._value)

    def _on_editing_finished(self):
        """Slot raised when enter/return is pressed or control loses focus.

        This captures the input text for setting the value.
        """
        if not self.isModified():
            return

        # Prevent signal from being triggered twice (QT bug).
        self.setModified(False)

        value = self.text().strip()

        if self.hasAcceptableInput():
            self._value = float(value)
        else:
            # If no value specified, set internal value to None
            if not value:
                self._value = None

        self._update_displayed_text()

    def setText(self, text: str):
        """Override default implementation to ensure input text is a
        numeric representation.

        :param text: Input text.
        :type text: str
        """
        if not text.strip():
            self._value = None
        else:
            try:
                self._value = float(text)
            except ValueError:
                return

        self._update_displayed_text()

    def focusInEvent(self, event: QtGui.QFocusEvent):
        """Behaviour when the control has focus.

        :param event: Contains focus parameters.
        :type event: QtGui.QFocusEvent
        """
        super().focusInEvent(event)

        if self.isReadOnly():
            return

        if self._value is None:
            return

        # Display the absolute value without formatting.
        display_value = round(self._value, self._formatter.numberDecimalPlaces())
        super().setText(str(display_value))
        self.selectAll()
