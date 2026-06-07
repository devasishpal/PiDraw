"""Renderer for WaveDrom timing diagrams via ``wavedrom-cli`` (npm)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_SIZE = 100 * 1024


class WaveDromRenderer(BaseRenderer):
    """Render WaveDrom timing/waveform diagrams to SVG."""

    name = "wavedrom"

    def __init__(self, path: str | None = None) -> None:
        """Initialise with optional explicit path to wavedrom-cli."""
        self._path = path
        self._resolved: str | None = path or self._find_wavedrom()
        if not self._resolved:
            raise RenderingError(
                "wavedrom-cli not found. Install with: npm install -g wavedrom-cli"
            )

    @staticmethod
    def _find_wavedrom() -> str | None:
        return shutil.which("wavedrom-cli")

    def render(self, source: str) -> str:
        """Render a WaveDrom timing diagram source to SVG."""
        if not source or not source.strip():
            raise RenderingError("WaveDrom source is empty")
        if "\x00" in source:
            raise RenderingError("WaveDrom source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderingError(f"WaveDrom source exceeds {_MAX_SIZE // 1024} KB limit")

        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_wavedrom_")
            input_path = os.path.join(tmp_dir, "input.json")
            output_path = os.path.join(tmp_dir, "output.svg")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)

            assert self._resolved is not None
            result = subprocess.run(
                [self._resolved, "-i", input_path, "-s", output_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RenderingError(
                    f"wavedrom-cli failed (code {result.returncode}): {result.stderr.strip()}"
                )

            if not os.path.isfile(output_path):
                raise RenderingError("wavedrom-cli produced no SVG output file")

            with open(output_path, "r", encoding="utf-8") as f:
                svg = f.read()

            if not svg.strip():
                raise RenderingError("wavedrom-cli returned empty SVG")
            if "<svg" not in svg:
                raise RenderingError("wavedrom-cli output does not contain <svg>")

            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderingError(f"wavedrom-cli returned malformed XML: {exc}") from exc

            return svg

        except subprocess.TimeoutExpired:
            raise RenderingError("wavedrom-cli timed out after 30s")
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"wavedrom-cli error: {exc}") from exc
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh

                sh.rmtree(tmp_dir, ignore_errors=True)
