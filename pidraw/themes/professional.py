from __future__ import annotations

from pidraw.core.models import ArrowStyle, Diagram, EdgeStyle, FontWeight, Style, TextAlign
from pidraw.themes.base import Theme, register_theme


@register_theme("professional")
class ProfessionalTheme(Theme):
    name = "professional"

    def apply(self, diagram: Diagram) -> Diagram:
        diagram.style = self.style()
        colors = ["#4a90d9", "#50b86c", "#e8a838", "#d95050", "#9b59b6"]
        for i, node in enumerate(diagram.all_nodes()):
            if node.style is None:
                node.style = Style(
                    fill_color=colors[i % len(colors)],
                    fill_opacity=0.12,
                    stroke_color=colors[i % len(colors)],
                    stroke_width=2.0,
                    text_color="#2c3e50",
                )
        return diagram

    def style(self) -> Style:
        return Style(
            stroke_color="#4a90d9",
            stroke_width=2.0,
            stroke_style=EdgeStyle.SOLID,
            fill_color="#ffffff",
            fill_opacity=1.0,
            padding=14.0,
            corner_radius=6.0,
            font_family="'Segoe UI', system-ui, sans-serif",
            font_size=14.0,
            font_weight=FontWeight.NORMAL,
            text_align=TextAlign.CENTER,
            text_color="#2c3e50",
            shadow=True,
            shadow_offset=3.0,
            shadow_color="rgba(0,0,0,0.1)",
            arrow_end=ArrowStyle.TRIANGLE_FILLED,
            arrow_size=10.0,
        )
