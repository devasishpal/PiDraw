from __future__ import annotations

from pidraw.backend.svg import SvgBackend
from pidraw.core.converters import get_converter
from pidraw.core.models import Diagram
from pidraw.layout import apply_layout
from pidraw.themes import get_theme


class ExportPipeline:
    def __init__(
        self,
        theme_name: str = "light",
        layout: bool = True,
        optimize: bool = False,
    ) -> None:
        self._theme_name = theme_name
        self._do_layout = layout
        self._do_optimize = optimize

    def execute(self, source: str, language: str) -> str:
        converter = get_converter(language)
        if converter is None:
            raise ValueError(f"No converter for language: {language}")

        diagram = converter.parse(source)
        return self._render_diagram(diagram)

    def execute_from_diagram(self, diagram: Diagram) -> str:
        return self._render_diagram(diagram)

    def _render_diagram(self, diagram: Diagram) -> str:
        if self._do_layout:
            diagram = apply_layout(diagram)

        theme = get_theme(self._theme_name)
        if theme is not None:
            diagram = theme.apply(diagram)

        backend = SvgBackend(theme={"background": self._resolve_background()})
        svg = backend.render(diagram)

        if self._do_optimize:
            from pidraw.optimizer import optimize_svg

            result = optimize_svg(svg)
            svg = result.svg

        return svg

    def _resolve_background(self) -> str | None:
        return None


def render_native(
    source: str,
    language: str,
    *,
    theme: str = "light",
    layout: bool = True,
    optimize: bool = False,
) -> str:
    pipeline = ExportPipeline(
        theme_name=theme,
        layout=layout,
        optimize=optimize,
    )
    return pipeline.execute(source, language)


def render_native_from_diagram(
    diagram: Diagram,
    *,
    theme: str = "light",
    optimize: bool = False,
) -> str:
    pipeline = ExportPipeline(
        theme_name=theme,
        layout=True,
        optimize=optimize,
    )
    return pipeline.execute_from_diagram(diagram)
