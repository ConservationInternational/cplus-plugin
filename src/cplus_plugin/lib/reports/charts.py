import plotly.graph_objects as go
import os
from typing import List, Optional

from ...definitions.defaults import REPORT_FONT_NAME


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

        # Create the pie chart trace
        pie_trace = go.Pie(
            labels=labels,
            values=values,
            textinfo='percent+label',
            textposition='outside',
            insidetextorientation='radial',
            marker=dict(colors=colors_hex),
            textfont=dict(family=REPORT_FONT_NAME)
        )

        # Define the layout
        layout = go.Layout(
            title={
                'text': title,
                'x': 0.5,
                'font': {
                    'family': REPORT_FONT_NAME,
                }
            },
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
