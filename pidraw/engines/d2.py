"""D2 renderer powered by the official ``d2`` command-line tool."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError

_MAX_INPUT_SIZE = 100 * 1024
_RENDER_TIMEOUT = 30
_SVG_ROOT_RE = re.compile(r"<\s*svg[\s>]", re.IGNORECASE)


def find_d2() -> str:
    """Locate the ``d2`` executable on ``PATH``."""
    exe: str | None = shutil.which("d2")
    if exe is None:
        raise EngineNotAvailableError(
            "D2",
            setup_command="Install D2 from https://d2lang.com/tour/install/",
        )
    return exe


class D2Renderer(BaseRenderer):
    """Render D2 diagram source to SVG via the official ``d2`` binary."""

    name = "d2"

    def __init__(self, d2_path: Optional[str] = None) -> None:
        self._d2_path: Optional[str] = None
        try:
            self._d2_path = d2_path or self._find_d2()
        except EngineNotAvailableError:
            pass

    def render(self, source: str) -> str:
        self._validate_source(source)
        if self._d2_path is not None:
            svg = self._run_d2(source)
        else:
            svg = self._run_native(source)
        self._validate_output(svg)
        return svg

    @staticmethod
    def _find_d2() -> str:
        exe: Optional[str] = shutil.which("d2")
        if exe is None:
            raise EngineNotAvailableError(
                "D2",
                setup_command="Install D2 from https://d2lang.com/tour/install/",
            )
        return exe

    @staticmethod
    def _validate_source(source: str) -> None:
        if not source.strip():
            raise RenderError("d2", "D2 source is empty")
        if len(source) > _MAX_INPUT_SIZE:
            raise RenderError("d2", f"D2 source exceeds maximum size of {_MAX_INPUT_SIZE} bytes")
        if "\x00" in source:
            raise RenderError("d2", "D2 source contains null bytes")

    @staticmethod
    def _validate_output(svg: str) -> None:
        if not svg:
            raise RenderError("d2", "D2 produced an empty SVG")
        if not _SVG_ROOT_RE.search(svg):
            raise RenderError("d2", "D2 output does not contain a valid <svg> root element")
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            raise RenderError("d2", f"D2 output is not valid XML: {exc}")

    def _run_native(self, source: str) -> str:
        """Fallback native renderer when d2 CLI is absent or fails."""
        from pidraw.backend.svg import SvgBackend
        from pidraw.core.converters import get_converter
        from pidraw.layout import apply_layout

        converter = get_converter("d2")
        if converter is None:
            raise EngineNotAvailableError(
                "d2 (native)",
                setup_command="Install D2 from https://d2lang.com/tour/install/",
            )
        try:
            diagram = converter.parse(source)
        except Exception as exc:
            raise RenderError("d2", f"Native converter failed: {exc}")
        diagram = apply_layout(diagram)
        backend = SvgBackend()
        try:
            svg = backend.render(diagram)
        except Exception as exc:
            raise RenderError("d2", f"SvgBackend failed: {exc}")
        return svg

    def _run_d2(self, source: str) -> str:
        tmp_dir: Optional[str] = None
        input_path: Optional[str] = None
        output_path: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_d2_")
            input_path = os.path.join(tmp_dir, "diagram.d2")
            output_path = os.path.join(tmp_dir, "diagram.svg")
            with open(input_path, "w", encoding="utf-8") as fh:
                fh.write(source)
            self._invoke_d2(input_path, output_path)
            with open(output_path, "r", encoding="utf-8") as fh:
                return fh.read()
        except RenderError:
            raise
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("d2", _RENDER_TIMEOUT)
        except Exception as exc:
            raise RenderError("d2", f"D2 rendering failed: {exc}")
        finally:
            self._cleanup(tmp_dir)

    def _invoke_d2(self, input_path: str, output_path: str) -> None:
        cmd = [
            self._d2_path,
            "--format=svg",
            input_path,
            output_path,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=_RENDER_TIMEOUT,
                check=False,
            )
        except FileNotFoundError:
            raise RenderError("d2", f"d2 executable not found at '{self._d2_path}'")

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderError("d2", f"D2 exited with code {result.returncode}", stderr=stderr)

    @staticmethod
    def _cleanup(tmp_dir: Optional[str]) -> None:
        if tmp_dir is not None and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass
