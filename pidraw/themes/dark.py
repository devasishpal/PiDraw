from __future__ import annotations

from pidraw.core.models import ArrowStyle, Diagram, EdgeStyle, FontWeight, Style, TextAlign
from pidraw.themes.base import Theme, register_theme


@register_theme("dark")
class DarkTheme(Theme):
    name = "dark"

    def apply(self, diagram: Diagram) -> Diagram:
        diagram.style = self.style()
        for node in diagram.all_nodes():
            if node.style is None:
                node.style = Style(
                    fill_color="#2d2d2d",
                    stroke_color="#666666",
                    text_color="#e0e0e0",
                )
        return diagram

    def style(self) -> Style:
        return Style(
            stroke_color="#888888",
            stroke_width=2.0,
            stroke_style=EdgeStyle.SOLID,
            fill_color="#1e1e1e",
            fill_opacity=1.0,
            padding=12.0,
            corner_radius=4.0,
            font_family="sans-serif",
            font_size=14.0,
            font_weight=FontWeight.NORMAL,
            text_align=TextAlign.CENTER,
            text_color="#e0e0e0",
            shadow=False,
            arrow_end=ArrowStyle.TRIANGLE_FILLED,
            arrow_size=10.0,
        )
