"""Renderer for Vega-Lite schemas.

Uses ``vl-convert-python`` if available, otherwise falls back to
the ``vl2svg`` CLI (npm).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_SIZE = 500 * 1024


class VegaLiteRenderer(BaseRenderer):
    """Render Vega-Lite specification JSON to SVG."""

    name = "vega-lite"

    def __init__(self, path: str | None = None) -> None:
        """Initialise with optional explicit path or vl-convert-python."""
        self._path = path
        self._vl_convert = None
        try:
            import vl_convert as _vlc  # type: ignore[import-not-found]

            self._vl_convert = _vlc
        except ImportError:
            pass

        if not self._vl_convert:
            self._resolved: str | None = path or self._find_vl2svg()
            if not self._resolved:
                raise RenderingError(
                    "Neither vl-convert-python nor vl2svg found. "
                    "Install one: pip install vl-convert-python  OR  npm install -g vega-lite-cli"
                )
        else:
            self._resolved = None

    @staticmethod
    def _find_vl2svg() -> str | None:
        return shutil.which("vl2svg")

    def render(self, source: str) -> str:
        """Render a Vega-Lite specification JSON to SVG."""
        if not source or not source.strip():
            raise RenderingError("Vega-Lite source is empty")
        if "\x00" in source:
            raise RenderingError("Vega-Lite source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderingError(f"Vega-Lite source exceeds {_MAX_SIZE // 1024} KB limit")

        try:
            spec = json.loads(source)
        except json.JSONDecodeError as exc:
            raise RenderingError(f"Vega-Lite source is not valid JSON: {exc}") from exc

        return (
            self._render_via_python(spec)
            if self._vl_convert
            else self._render_via_cli(source)
        )

    def _render_via_python(self, spec: dict[str, object]) -> str:
        assert self._vl_convert is not None
        try:
            svg = str(self._vl_convert.vegalite_to_svg(spec))
            if not svg or "<svg" not in svg:
                raise RenderingError("vl-convert returned invalid SVG")
            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderingError(
                    f"vl-convert returned malformed XML: {exc}"
                ) from exc
            return svg
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"vl-convert failed: {exc}") from exc

    def _render_via_cli(self, source: str) -> str:
        assert self._resolved is not None
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_vegalite_")
            input_path = os.path.join(tmp_dir, "spec.vl.json")

            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)

            result = subprocess.run(
                [self._resolved, input_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RenderingError(
                    f"vl2svg failed (code {result.returncode}): {result.stderr.strip()}"
                )

            svg = result.stdout
            if not svg.strip():
                raise RenderingError("vl2svg returned empty SVG")
            if "<svg" not in svg:
                raise RenderingError("vl2svg output does not contain <svg>")

            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderingError(f"vl2svg returned malformed XML: {exc}") from exc

            return svg

        except subprocess.TimeoutExpired:
            raise RenderingError("vl2svg timed out after 30s")
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"vl2svg error: {exc}") from exc
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh

                sh.rmtree(tmp_dir, ignore_errors=True)
