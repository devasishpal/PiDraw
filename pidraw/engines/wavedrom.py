"""Renderer for WaveDrom timing diagrams — tries CLI first, falls back to native."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderError, RenderTimeoutError

_MAX_SIZE = 500 * 1024


class WaveDromRenderer(BaseRenderer):
    """Render WaveDrom timing/waveform diagrams to SVG.

    Tries ``wavedrom-cli`` (npm) first; falls back to native Python
    renderer if the CLI is not available.
    """

    name = "wavedrom"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._resolved: str | None = path or self._find_wavedrom()
        self._native = None
        if not self._resolved:
            from pidraw.engines.wavedrom_native import WaveDromNativeRenderer

            self._native = WaveDromNativeRenderer()

    @staticmethod
    def _find_wavedrom() -> str | None:
        return shutil.which("wavedrom-cli")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("wavedrom", "WaveDrom source is empty")
        if "\x00" in source:
            raise RenderError("wavedrom", "WaveDrom source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError("wavedrom", f"WaveDrom source exceeds {_MAX_SIZE // 1024} KB limit")

        if self._native is not None:
            return self._native.render(source)

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
                raise RenderError(
                    "wavedrom",
                    f"wavedrom-cli failed (code {result.returncode}): {result.stderr.strip()}",
                )
            if not os.path.isfile(output_path):
                raise RenderError("wavedrom", "wavedrom-cli produced no SVG output file")
            with open(output_path, "r", encoding="utf-8") as f:
                svg = f.read()
            if not svg.strip():
                raise RenderError("wavedrom", "wavedrom-cli returned empty SVG")
            if "<svg" not in svg:
                raise RenderError("wavedrom", "wavedrom-cli output does not contain <svg>")
            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("wavedrom", f"wavedrom-cli returned malformed XML: {exc}")
            return svg
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("wavedrom", 30)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("wavedrom", f"wavedrom-cli error: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh

                sh.rmtree(tmp_dir, ignore_errors=True)
