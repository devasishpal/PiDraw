"""Renderer for Vega visualisation schemas via ``vg2svg`` CLI (npm)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError

_MAX_SIZE = 500 * 1024


class VegaRenderer(BaseRenderer):
    """Render Vega specification JSON to SVG."""

    name = "vega"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._resolved: str | None = None
        self._vl_convert = None
        try:
            import vl_convert as _vlc
            self._vl_convert = _vlc
        except ImportError:
            pass
        if not self._vl_convert:
            self._resolved = path or self._find_vg2svg()
            if not self._resolved:
                raise EngineNotAvailableError(
                    "vg2svg",
                    setup_command="pip install vl-convert-python  OR  npm install -g vega-cli",
                )

    @staticmethod
    def _find_vg2svg() -> str | None:
        return shutil.which("vg2svg")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("vega", "Vega source is empty")
        if "\x00" in source:
            raise RenderError("vega", "Vega source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError("vega", f"Vega source exceeds {_MAX_SIZE // 1024} KB limit")

        if self._resolved is not None:
            return self._render_via_cli(source)
        return self._render_via_python(source)

    def _render_via_python(self, source: str) -> str:
        assert self._vl_convert is not None
        try:
            import json
            spec = json.loads(source)
            svg = str(self._vl_convert.vega_to_svg(spec))
            if not svg or "<svg" not in svg:
                raise RenderError("vega", "vl-convert returned invalid SVG")
            import xml.etree.ElementTree as ET
            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("vega", f"vl-convert returned malformed XML: {exc}")
            return svg
        except json.JSONDecodeError as exc:
            raise RenderError("vega", f"Vega source is not valid JSON: {exc}")
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("vega", f"vl-convert failed: {exc}")

    def _render_via_cli(self, source: str) -> str:
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_vega_")
            input_path = os.path.join(tmp_dir, "spec.json")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)
            assert self._resolved is not None
            result = subprocess.run(
                [self._resolved, input_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                raise RenderError(
                    "vega",
                    f"vg2svg failed (code {result.returncode}): {result.stderr.strip()}",
                )
            svg = result.stdout or ""
            if not svg.strip():
                raise RenderError("vega", "vg2svg returned empty SVG")
            if "<svg" not in svg:
                raise RenderError("vega", "vg2svg output does not contain <svg>")
            import xml.etree.ElementTree as ET
            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("vega", f"vg2svg returned malformed XML: {exc}")
            return svg
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("vega", 30)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("vega", f"vg2svg error: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh
                sh.rmtree(tmp_dir, ignore_errors=True)
