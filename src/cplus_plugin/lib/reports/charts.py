import plotly.graph_objects as go
import os
from typing import List, Optional

from ...definitions.defaults import REPORT_FONT_NAME


def _hex_to_rgb(hexstr: str) -> tuple[float, float, float]:
    hexstr = hexstr.lstrip("#")
    r = int(hexstr[0:2], 16) / 255.0
    g = int(hexstr[2:4], 16) / 255.0
    b = int(hexstr[4:6], 16) / 255.0
    return r, g, b


def _rel_lum(c: tuple[float, float, float]) -> float:
    # WCAG relative luminance
    def f(u): return u/12.92 if u <= 0.03928 else ((u+0.055)/1.055)**2.4
    r, g, b = map(f, c)
    return 0.2126*r + 0.7152*g + 0.0722*b


def _best_text_color(bg_hex: str) -> str:
    L = _rel_lum(_hex_to_rgb(bg_hex))
    # Contrast ratios vs white/black: (L1+0.05)/(L2+0.05)
    contrast_white = (1.0 + 0.05) / (L + 0.05)
    contrast_black = (L + 0.05) / (0.0 + 0.05)
    return "#FFFFFF" if contrast_white >= contrast_black else "#000000"


class PieChartRenderer:
    @staticmethod
    def render_pie_png(
        out_path: str,
        labels: List[str],
        values: List[float],
        colors_hex: Optional[List[str]] = None,
        title: Optional[str] = None,
        size_px: int = 360,
    ) -> str:
        # Create output directory
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # Calculate total area and format labels with area and percentage
        total_area = sum(values)
        formatted_labels = []
        for label, value in zip(labels, values):
            percentage = (value / total_area) * 100 if total_area else 0
            formatted_text = (
                f"{label}<br>"
                f"{value:.2f} Ha<br>"
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
            textinfo='text',
            textposition='inside',
            insidetextorientation='radial',
            marker=dict(
                colors=colors_hex,
                line=dict(color='white', width=1)
            ),
            textfont=dict(
                family=REPORT_FONT_NAME,
                color=text_colors
            )
        )

        # Define the layout
        layout = go.Layout(
            title=None,
            showlegend=True,
            height=size_px,
            width=size_px,
            margin=go.layout.Margin(t=50, b=50, l=50, r=50)
        )

        # Create the figure
        fig = go.Figure(data=[pie_trace], layout=layout)

        # Save the figure to a file
        fig.write_image(out_path)

        return out_path
