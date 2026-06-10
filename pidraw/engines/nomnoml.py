"""Renderer for Nomnoml diagrams — tries CLI first, falls back to native."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.core.converters import get_converter
from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderError, RenderTimeoutError

_MAX_SIZE = 500 * 1024


class NomnomlRenderer(BaseRenderer):
    """Render Nomnoml diagram source to SVG.

    Tries ``nomnoml`` CLI (npm) first; falls back to the native
    Python parser + SvgBackend pipeline if the CLI is not available
    or fails.
    """

    name = "nomnoml"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._resolved: str | None = path or self._find_nomnoml()
        self._native = None

    @staticmethod
    def _find_nomnoml() -> str | None:
        return shutil.which("nomnoml")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("nomnoml", "Nomnoml source is empty")
        if "\x00" in source:
            raise RenderError("nomnoml", "Nomnoml source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError("nomnoml", f"Nomnoml source exceeds {_MAX_SIZE // 1024} KB limit")

        if self._resolved:
            try:
                return self._render_via_cli(source)
            except (RenderError, subprocess.SubprocessError, OSError):
                pass

        return self._render_native(source)

    def _render_via_cli(self, source: str) -> str:
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_nomnoml_")
            input_path = os.path.join(tmp_dir, "input.nomnoml")
            output_path = os.path.join(tmp_dir, "output.svg")
            with open(input_path, "wb") as f:
                f.write(source.rstrip("\n").encode("utf-8").replace(b"\r\n", b"\n"))
            assert self._resolved is not None
            result = subprocess.run(
                [self._resolved, input_path, output_path],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                raise RenderError(
                    "nomnoml",
                    f"nomnoml failed (code {result.returncode}): {result.stderr.strip()}",
                )
            if not os.path.isfile(output_path):
                raise RenderError("nomnoml", "nomnoml produced no SVG output file")
            with open(output_path, "r", encoding="utf-8") as f:
                svg = f.read()
            if not svg.strip():
                raise RenderError("nomnoml", "nomnoml returned empty SVG")
            if "<svg" not in svg:
                raise RenderError("nomnoml", "nomnoml output does not contain <svg>")
            import xml.etree.ElementTree as ET
            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("nomnoml", f"nomnoml returned malformed XML: {exc}")
            return svg
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("nomnoml", 30)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("nomnoml", f"nomnoml error: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh
                sh.rmtree(tmp_dir, ignore_errors=True)

    def _render_native(self, source: str) -> str:
        converter = get_converter("nomnoml")
        if converter is None:
            raise RenderError("nomnoml", "Native Nomnoml converter not available")
        from pidraw.engines.native import NativeRenderer
        native = NativeRenderer("nomnoml")
        return native.render(source)
