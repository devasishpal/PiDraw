"""Renderer for BPMN diagrams via ``bpmn-to-svg`` CLI (npm)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError

_MAX_SIZE = 100 * 1024


class BPMNRenderer(BaseRenderer):
    """Render BPMN 2.0 XML/JSON diagrams to SVG."""

    name = "bpmn"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._resolved: str | None = path or self._find_bpmn()
        if not self._resolved:
            raise EngineNotAvailableError(
                "bpmn-to-svg",
                setup_command="npm install -g bpmn-to-svg",
            )

    @staticmethod
    def _find_bpmn() -> str | None:
        return shutil.which("bpmn-to-svg") or shutil.which("bpmn-svg")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("bpmn", "BPMN source is empty")
        if "\x00" in source:
            raise RenderError("bpmn", "BPMN source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError("bpmn", f"BPMN source exceeds {_MAX_SIZE // 1024} KB limit")

        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_bpmn_")
            ext = ".json" if source.strip().startswith("{") else ".bpmn"
            input_path = os.path.join(tmp_dir, f"input{ext}")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)
            assert self._resolved is not None
            cmd = [self._resolved, "generate", "--input", input_path, "--output-dir", tmp_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RenderError(
                    "bpmn",
                    f"bpmn-to-svg failed (code {result.returncode}): {result.stderr.strip()}",
                )
            svg_files = [f for f in os.listdir(tmp_dir) if f.endswith(".svg")]
            if not svg_files:
                raise RenderError("bpmn", "bpmn-to-svg produced no SVG output file")
            output_path = os.path.join(tmp_dir, svg_files[0])
            with open(output_path, "r", encoding="utf-8") as f:
                svg = f.read()
            if not svg.strip():
                raise RenderError("bpmn", "bpmn-to-svg returned empty SVG")
            if "<svg" not in svg:
                raise RenderError("bpmn", "bpmn-to-svg output does not contain <svg>")
            import xml.etree.ElementTree as ET
            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("bpmn", f"bpmn-to-svg returned malformed XML: {exc}")
            return svg
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("bpmn", 60)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("bpmn", f"bpmn-to-svg error: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh
                sh.rmtree(tmp_dir, ignore_errors=True)
