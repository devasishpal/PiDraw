"""Renderer for Markmap mindmap diagrams — tries CLI first, falls back to native."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.core.converters import get_converter
from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError

_MAX_SIZE = 500 * 1024
_SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "scripts")


class MarkmapRenderer(BaseRenderer):
    """Render Markdown mindmap source to SVG.

    Tries ``markmap`` CLI (npm) + headless Chromium first; falls back
    to the native Python parser + TreeLayout + SvgBackend pipeline
    if the CLI is not available or fails.
    """

    name = "markmap"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._markmap: str | None = path or shutil.which("markmap")
        self._node: str | None = shutil.which("node")
        self._script = os.path.join(_SCRIPT_DIR, "markmap_render.js")
        self._native = None

        if not self._markmap:
            raise EngineNotAvailableError(
                "markmap",
                setup_command="npm install -g markmap-cli",
            )
        if not self._node:
            raise EngineNotAvailableError(
                "node",
                setup_command="Install Node.js from https://nodejs.org",
            )
        if not os.path.isfile(self._script):
            raise RenderError("markmap", f"markmap render script not found: {self._script}")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("markmap", "Markmap source is empty")
        if "\x00" in source:
            raise RenderError("markmap", "Markmap source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError("markmap", f"Markmap source exceeds {_MAX_SIZE // 1024} KB limit")

        if self._markmap and self._node:
            try:
                return self._render_via_cli(source)
            except (RenderError, subprocess.SubprocessError, OSError):
                pass

        return self._render_native(source)

    def _render_via_cli(self, source: str) -> str:
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_markmap_")
            input_path = os.path.join(tmp_dir, "input.md")
            output_path = os.path.join(tmp_dir, "output.svg")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)

            assert self._node is not None
            result = subprocess.run(
                [self._node, self._script, input_path, output_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RenderError(
                    "markmap",
                    f"markmap render failed (code {result.returncode}): "
                    f"{result.stderr.strip() or result.stdout.strip()}",
                )

            if not os.path.isfile(output_path):
                raise RenderError("markmap", "markmap render produced no SVG file")

            with open(output_path, "r", encoding="utf-8") as f:
                svg = f.read()
                svg = svg.lstrip("\ufeff")

            if not svg.strip():
                raise RenderError("markmap", "markmap render returned empty SVG")
            if "<svg" not in svg or len(svg) < 500:
                raise RenderError("markmap", "markmap render returned incomplete SVG")

            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("markmap", f"markmap returned malformed SVG: {exc}")

            return svg

        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("markmap", 60)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("markmap", f"markmap error: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh

                sh.rmtree(tmp_dir, ignore_errors=True)

    def _render_native(self, source: str) -> str:
        converter = get_converter("markmap")
        if converter is None:
            raise RenderError("markmap", "Native Markmap converter not available")
        from pidraw.engines.native import NativeRenderer

        native = NativeRenderer("markmap")
        return native.render(source)
