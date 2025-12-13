# -*- coding: utf-8 -*-

from pathlib import Path
import os
from typing import List, Optional

import plotly.graph_objects as go

from qgis.core import (
    QgsBasicNumericFormat,
    QgsNumericFormatContext,
    QgsReadWriteContext,
)

from ...definitions.defaults import REPORT_FONT_NAME


def _hex_to_rgb(hexstr: str) -> tuple[float, float, float]:
    """Converts a hex color string to an sRGB tuple."""
    hexstr = hexstr.lstrip("#")
    r = int(hexstr[0:2], 16) / 255.0
    g = int(hexstr[2:4], 16) / 255.0
    b = int(hexstr[4:6], 16) / 255.0
    return r, g, b


def _rel_lum(c: tuple[float, float, float]) -> float:
    """Calculates the relative luminance of an sRGB color."""

    # WCAG relative luminance
    def f(u):
        return u / 12.92 if u <= 0.03928 else ((u + 0.055) / 1.055) ** 2.4

    r, g, b = map(f, c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _best_text_color(bg_hex: str) -> str:
    """Returns either black or white,
    depending on which has better contrast with the given background color.
    """
    L = _rel_lum(_hex_to_rgb(bg_hex))
    # Contrast ratios vs white/black: (L1+0.05)/(L2+0.05)
    contrast_white = (1.0 + 0.05) / (L + 0.05)
    contrast_black = (L + 0.05) / (0.0 + 0.05)
    return "#FFFFFF" if contrast_white >= contrast_black else "#000000"


def _format_number_locale(value: float, decimals: int = 2) -> str:
    """Formats a number according to the QGIS numeric/locale settings."""
    try:
        fmt = QgsBasicNumericFormat()
        # enable grouping and set decimals
        for name in ("setUseThousandsSeparator", "setShowThousandsSeparator"):
            if hasattr(fmt, name):
                getattr(fmt, name)(True)
                break

        # set decimal places
        if hasattr(fmt, "setNumberDecimalPlaces"):
            fmt.setNumberDecimalPlaces(decimals)

        if hasattr(fmt, "setShowTrailingZeros"):
            fmt.setShowTrailingZeros(True)

        ctx = None
        try:
            # QgsNumericFormatContext is for QGIS 3.x
            ctx = QgsNumericFormatContext()
        except Exception:
            ctx = QgsReadWriteContext()  # for older QGIS versions

        # Use the correct method name from the provided API for formatting
        if hasattr(fmt, "formatDouble"):
            return fmt.formatDouble(value, ctx)

    except Exception:
        pass

    # Fallback to standard Python formatting
    return f"{value:,.{decimals}f}"


class PieChartRenderer:
    """Renders pie charts using Plotly and saves them as an image file."""

    @staticmethod
    def render_pie_html(
        out_path: str,
        labels: List[str],
        values: List[float],
        colors_hex: Optional[List[str]] = None,
        title: Optional[str] = None,
        size_px: int = 360,
    ) -> str:
        """Renders a pie chart and saves it as a HTML file."""
        # Create output directory
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # Calculate total area and format labels with area and percentage
        total_area = sum(values)
        formatted_labels = []
        for label, value in zip(labels, values):
            percentage = (value / total_area) * 100 if total_area else 0
            formatted_text = (
                f"{label}<br>"
                f"{_format_number_locale(value, 2)} Ha<br>"
                f"({percentage:.1f}%)"
            )
            formatted_labels.append(formatted_text)
        if colors_hex:
            text_colors = [_best_text_color(c) for c in colors_hex]
        else:
            text_colors = ["#000000"] * len(values)  # default

        # Create the pie chart trace
        pie_trace = go.Pie(
            labels=labels,
            values=values,
            text=formatted_labels,
            textinfo="text",
            textposition="inside",
            insidetextorientation="horizontal",
            marker=dict(colors=colors_hex, line=dict(color="white", width=1)),
            textfont=dict(family=REPORT_FONT_NAME, color=text_colors),
        )

        # Ballpark figure to maintain 4:3 aspect ratio. Remove hardcode
        # in the future, have it calculated from item size.
        preferred_width, preferred_height = 640, 480

        # Define the layout
        layout = go.Layout(
            title=None,
            showlegend=True,
            height=preferred_height,
            width=preferred_width,
            margin=go.layout.Margin(t=10, b=10, l=10, r=10),
        )

        # Create the figure
        fig = go.Figure(data=[pie_trace], layout=layout)

        # Save the figure to as HTML
        fig.write_html(
            out_path,
            auto_open=False,
            auto_play=False,
            config={"displayModeBar": False},
        )

        return out_path
