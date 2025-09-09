# lib/reports/charts.py
from __future__ import annotations
from typing import List, Optional
import os
from qgis.PyQt.QtGui import QImage, QPainter, QColor, QPen, QFont
from qgis.PyQt.QtCore import QRectF, Qt


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
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        img = QImage(size_px, size_px, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, True)

        # title area
        title_h = 28 if title else 0
        rect = QRectF(6, 6, size_px - 12, size_px - 12 - title_h)

        # palette (fallback)
        base = [
            "#2196f3", "#4caf50", "#ffc107", "#f44336", "#9c27b0",
            "#795548", "#009688", "#3f51b5", "#cddc39", "#ff9800"
        ]
        cols = colors_hex or base

        total = sum(values) or 1.0
        start = 0.0
        for i, v in enumerate(values):
            frac = (v / total) if total else 0.0
            span = 360.0 * frac
            color = QColor(cols[i % len(cols)])
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawPie(rect, int(start * 16), int(span * 16))
            start += span

        # title
        if title:
            p.setPen(QPen(QColor(35, 35, 35)))
            f = QFont()
            f.setBold(True)
            f.setPointSize(10)
            p.setFont(f)
            p.drawText(QRectF(0, rect.bottom()+2, size_px, title_h),
                       Qt.AlignHCenter | Qt.AlignTop, title)

        p.end()
        img.save(out_path, "PNG")
        return out_path
