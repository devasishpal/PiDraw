"""Renderer for Structurizr DSL diagrams — tries CLI first, falls back to native."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from pidraw.backend.svg import SvgBackend
from pidraw.core.converters import get_converter
from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderError, RenderTimeoutError
from pidraw.layout import apply_layout

_MAX_SIZE = 500 * 1024


class StructurizrRenderer(BaseRenderer):
    """Render Structurizr DSL architecture diagrams to SVG.

    Tries ``structurizr-cli`` (Java) first to export to PlantUML;
    falls back to the native Python DSL parser if the CLI is not
    available or fails.
    """

    name = "structurizr"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._resolved: str | None = path or self._find_structurizr()
        self._native = None

    @staticmethod
    def _find_structurizr() -> str | None:
        return shutil.which("structurizr-cli") or shutil.which("structurizr")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("structurizr", "Structurizr source is empty")
        if "\x00" in source:
            raise RenderError("structurizr", "Structurizr source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError(
                "structurizr", f"Structurizr source exceeds {_MAX_SIZE // 1024} KB limit"
            )

        if self._resolved:
            try:
                return self._render_via_cli(source)
            except (RenderError, subprocess.SubprocessError, OSError):
                pass

        return self._render_native(source)

    def _render_via_cli(self, source: str) -> str:
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_structurizr_")
            dsl_path = os.path.join(tmp_dir, "workspace.dsl")
            puml_dir = os.path.join(tmp_dir, "puml")
            os.makedirs(puml_dir, exist_ok=True)
            with open(dsl_path, "w", encoding="utf-8") as fh:
                fh.write(source)
            assert self._resolved is not None
            result = subprocess.run(
                [
                    self._resolved, "export",
                    "-w", dsl_path,
                    "-f", "plantuml",
                    "-o", puml_dir,
                ],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise RenderError(
                    "structurizr",
                    f"structurizr-cli failed (code {result.returncode}): {result.stderr.strip()}",
                )
            puml_files = list(Path(puml_dir).glob("*.puml"))
            if not puml_files:
                raise RenderError("structurizr", "structurizr-cli produced no PlantUML files")
            puml_path = None
            for f in puml_files:
                if "-key" not in f.stem:
                    puml_path = f
                    break
            if puml_path is None:
                puml_path = puml_files[0]
            puml_source = puml_path.read_text(encoding="utf-8")
            converter = get_converter("plantuml")
            if converter is None:
                raise RenderError("structurizr", "PlantUML converter not available")
            diagram = converter.parse(puml_source)
            diagram = apply_layout(diagram)
            backend = SvgBackend()
            svg = backend.render(diagram)
            if not svg.strip():
                raise RenderError("structurizr", "Native rendering produced empty SVG")
            if "<svg" not in svg:
                raise RenderError("structurizr", "Native rendering output does not contain <svg>")
            return svg
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("structurizr", 60)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("structurizr", f"structurizr-cli error: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh
                sh.rmtree(tmp_dir, ignore_errors=True)

    def _render_native(self, source: str) -> str:
        converter = get_converter("structurizr")
        if converter is None:
            raise RenderError("structurizr", "Native Structurizr converter not available")
        try:
            diagram = converter.parse(source)
        except Exception as exc:
            raise RenderError("structurizr", f"Native parser failed: {exc}")
        diagram = apply_layout(diagram)
        backend = SvgBackend()
        try:
            svg = backend.render(diagram)
        except Exception as exc:
            raise RenderError("structurizr", f"SvgBackend failed: {exc}")
        if not svg.strip():
            raise RenderError("structurizr", "Native rendering produced empty SVG")
        if "<svg" not in svg:
            raise RenderError("structurizr", "Native rendering output does not contain <svg>")
        return svg
