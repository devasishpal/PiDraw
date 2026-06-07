from __future__ import annotations

from pidraw.core.models import ArrowStyle, Diagram, EdgeStyle, FontWeight, Style, TextAlign
from pidraw.themes.base import Theme, register_theme


@register_theme("minimal")
class MinimalTheme(Theme):
    name = "minimal"

    def apply(self, diagram: Diagram) -> Diagram:
        diagram.style = self.style()
        for node in diagram.all_nodes():
            if node.style is None:
                node.style = Style(
                    fill_color="#fafafa",
                    stroke_color="#999999",
                )
            if node.shape is not None:
                node.style.corner_radius = 2.0
        return diagram

    def style(self) -> Style:
        return Style(
            stroke_color="#aaaaaa",
            stroke_width=1.0,
            stroke_style=EdgeStyle.SOLID,
            fill_color="#fafafa",
            fill_opacity=1.0,
            padding=8.0,
            corner_radius=2.0,
            font_family="helvetica, arial, sans-serif",
            font_size=12.0,
            font_weight=FontWeight.NORMAL,
            text_align=TextAlign.CENTER,
            text_color="#555555",
            shadow=False,
            arrow_end=ArrowStyle.TRIANGLE,
            arrow_size=8.0,
        )
