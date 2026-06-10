"""Graphviz renderer powered by the ``dot`` command-line tool.

Detects ``dot`` on ``PATH``, feeds it DOT source through stdin,
and returns the generated SVG from stdout.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError

_MAX_INPUT_SIZE = 100 * 1024
_RENDER_TIMEOUT = 30
_SVG_ROOT_RE = re.compile(r"<\s*svg[\s>]", re.IGNORECASE)


class GraphvizRenderer(BaseRenderer):
    """Render Graphviz DOT source to SVG via the ``dot`` executable.

    The renderer pipes DOT source through ``dot -Tsvg``.  If the
    executable is not found on ``PATH`` a helpful error is raised
    at construction time.
    """

    name = "graphviz"

    def __init__(self, dot_path: Optional[str] = None) -> None:
        self._dot_path: Optional[str] = None
        try:
            self._dot_path = dot_path or self._find_dot()
        except EngineNotAvailableError:
            pass

    def render(self, source: str) -> str:
        self._validate_source(source)
        if self._dot_path is not None:
            svg = self._run_dot(source)
        else:
            svg = self._run_native(source)
        self._validate_output(svg)
        return svg

    @staticmethod
    def _find_dot() -> str:
        exe: Optional[str] = shutil.which("dot")
        if exe is None:
            raise EngineNotAvailableError(
                "Graphviz 'dot'",
                setup_command="Install Graphviz from https://graphviz.org/download/",
            )
        return exe

    @staticmethod
    def _validate_source(source: str) -> None:
        if not source.strip():
            raise RenderError("graphviz", "Graphviz DOT source is empty")
        if len(source) > _MAX_INPUT_SIZE:
            raise RenderError(
                "graphviz",
                f"Graphviz DOT source exceeds maximum size of {_MAX_INPUT_SIZE} bytes",
            )
        if "\x00" in source:
            raise RenderError("graphviz", "Graphviz DOT source contains null bytes")

    @staticmethod
    def _validate_output(svg: str) -> None:
        if not svg:
            raise RenderError("graphviz", "Graphviz dot produced an empty SVG")
        if not _SVG_ROOT_RE.search(svg):
            raise RenderError(
                "graphviz",
                "Graphviz dot output does not contain a valid <svg> root element",
            )
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            raise RenderError("graphviz", f"Graphviz dot output is not valid XML: {exc}")

    def _run_native(self, source: str) -> str:
        """Fallback native renderer when dot CLI is absent or fails."""
        from pidraw.backend.svg import SvgBackend
        from pidraw.core.converters import get_converter
        from pidraw.layout import apply_layout

        converter = get_converter("graphviz")
        if converter is None:
            raise EngineNotAvailableError(
                "graphviz (native)",
                setup_command="Install Graphviz from https://graphviz.org/download/",
            )
        try:
            diagram = converter.parse(source)
        except Exception as exc:
            raise RenderError("graphviz", f"Native converter failed: {exc}")
        diagram = apply_layout(diagram)
        backend = SvgBackend()
        try:
            svg = backend.render(diagram)
        except Exception as exc:
            raise RenderError("graphviz", f"SvgBackend failed: {exc}")
        return svg

    def _run_dot(self, source: str) -> str:
        cmd = [self._dot_path, "-Tsvg"]

        try:
            result = subprocess.run(
                cmd,
                input=source.encode("utf-8"),
                capture_output=True,
                timeout=_RENDER_TIMEOUT,
                check=False,
            )
        except FileNotFoundError:
            raise RenderError(
                "graphviz", f"dot executable not found at '{self._dot_path}'"
            )
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("graphviz", _RENDER_TIMEOUT)
        except Exception as exc:
            raise RenderError("graphviz", f"Graphviz dot rendering failed: {exc}")

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderError(
                "graphviz",
                f"Graphviz dot exited with code {result.returncode}",
                stderr=stderr,
            )

        svg = result.stdout.decode("utf-8", errors="replace")
        return svg
