from __future__ import annotations

from pidraw.core.models import ArrowStyle, Diagram, EdgeStyle, FontWeight, Style, TextAlign
from pidraw.themes.base import Theme, register_theme


@register_theme("blueprint")
class BlueprintTheme(Theme):
    name = "blueprint"

    def apply(self, diagram: Diagram) -> Diagram:
        diagram.style = self.style()
        for node in diagram.all_nodes():
            if node.style is None:
                node.style = Style(
                    fill_color="#e8f0fe",
                    stroke_color="#1a73e8",
                    stroke_width=1.5,
                )
            if node.shape is not None:
                node.style.corner_radius = 2.0
        return diagram

    def style(self) -> Style:
        return Style(
            stroke_color="#1a73e8",
            stroke_width=1.5,
            stroke_style=EdgeStyle.SOLID,
            fill_color="#e8f0fe",
            fill_opacity=0.5,
            padding=10.0,
            corner_radius=2.0,
            font_family="'Courier New', monospace",
            font_size=13.0,
            font_weight=FontWeight.NORMAL,
            text_align=TextAlign.CENTER,
            text_color="#174ea6",
            shadow=False,
            arrow_end=ArrowStyle.TRIANGLE_FILLED,
            arrow_size=9.0,
        )
