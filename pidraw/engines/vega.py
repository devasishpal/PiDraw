"""Renderer for Vega visualisation schemas via ``vg2svg`` CLI (npm)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_SIZE = 500 * 1024


class VegaRenderer(BaseRenderer):
    """Render Vega specification JSON to SVG."""

    name = "vega"

    def __init__(self, path: str | None = None) -> None:
        """Initialise with optional explicit path to vg2svg."""
        self._path = path
        self._resolved: str | None = path or self._find_vg2svg()
        if not self._resolved:
            raise RenderingError(
                "vg2svg not found. Install with: npm install -g vega-cli"
            )

    @staticmethod
    def _find_vg2svg() -> str | None:
        return shutil.which("vg2svg")

    def render(self, source: str) -> str:
        """Render a Vega specification JSON to SVG."""
        if not source or not source.strip():
            raise RenderingError("Vega source is empty")
        if "\x00" in source:
            raise RenderingError("Vega source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderingError(f"Vega source exceeds {_MAX_SIZE // 1024} KB limit")

        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_vega_")
            input_path = os.path.join(tmp_dir, "spec.json")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)

            assert self._resolved is not None
            result = subprocess.run(
                [self._resolved, input_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RenderingError(
                    f"vg2svg failed (code {result.returncode}): {result.stderr.strip()}"
                )

            svg = result.stdout or ""
            if not svg.strip():
                raise RenderingError("vg2svg returned empty SVG")
            if "<svg" not in svg:
                raise RenderingError("vg2svg output does not contain <svg>")

            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderingError(f"vg2svg returned malformed XML: {exc}") from exc

            return svg

        except subprocess.TimeoutExpired:
            raise RenderingError("vg2svg timed out after 30s")
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"vg2svg error: {exc}") from exc
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh

                sh.rmtree(tmp_dir, ignore_errors=True)
