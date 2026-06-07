"""Renderer for Markmap mindmap diagrams via headless Chromium."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_SIZE = 500 * 1024
_SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "scripts")


class MarkmapRenderer(BaseRenderer):
    """Render Markdown mindmap source to SVG.

    Uses the ``markmap`` CLI to generate offline HTML, then extracts
    the rendered SVG via headless Chromium (Playwright).
    """

    name = "markmap"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._markmap: str | None = path or shutil.which("markmap")
        self._node: str | None = shutil.which("node")
        self._script = os.path.join(_SCRIPT_DIR, "markmap_render.js")

        if not self._markmap:
            raise RenderingError(
                "markmap CLI not found. Install with: npm install -g markmap-cli"
            )
        if not self._node:
            raise RenderingError("Node.js is required for markmap rendering")
        if not os.path.isfile(self._script):
            raise RenderingError(f"markmap render script not found: {self._script}")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderingError("Markmap source is empty")
        if "\x00" in source:
            raise RenderingError("Markmap source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderingError(f"Markmap source exceeds {_MAX_SIZE // 1024} KB limit")

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
                raise RenderingError(
                    f"markmap render failed (code {result.returncode}): "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )

            if not os.path.isfile(output_path):
                raise RenderingError("markmap render produced no SVG file")

            with open(output_path, "r", encoding="utf-8") as f:
                svg = f.read()
                svg = svg.lstrip("\ufeff")

            if not svg.strip():
                raise RenderingError("markmap render returned empty SVG")
            if "<svg" not in svg or len(svg) < 500:
                raise RenderingError("markmap render returned incomplete SVG")

            import xml.etree.ElementTree as ET
            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderingError(f"markmap returned malformed SVG: {exc}") from exc

            return svg

        except subprocess.TimeoutExpired:
            raise RenderingError("markmap render timed out after 60s")
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"markmap error: {exc}") from exc
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh
                sh.rmtree(tmp_dir, ignore_errors=True)
