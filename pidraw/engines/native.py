"""Native renderer — uses converter + SvgBackend instead of external CLI tools."""

from __future__ import annotations

from pidraw.backend.svg import SvgBackend
from pidraw.core.converters import get_converter
from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError
from pidraw.layout import apply_layout


class NativeRenderer(BaseRenderer):
    """Renderer that uses the native converter + SvgBackend pipeline.

    Works for any language that has a registered converter, without
    requiring external CLI tools.
    """

    name: str = ""

    def __init__(self, language: str) -> None:
        converter = get_converter(language)
        if converter is None:
            raise RenderingError(f"No converter registered for language: {language}")
        self._language = language
        self._converter = converter

    def render(self, source: str) -> str:
        try:
            diagram = self._converter.parse(source)
        except Exception as exc:
            raise RenderingError(f"{self._language} converter failed: {exc}") from exc

        diagram = apply_layout(diagram)

        backend = SvgBackend()
        try:
            svg = backend.render(diagram)
        except Exception as exc:
            raise RenderingError(f"SvgBackend failed for {self._language}: {exc}") from exc

        return svg
