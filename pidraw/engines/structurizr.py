"""Renderer for Structurizr DSL diagrams via structurizr-cli + native pipeline."""

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
from pidraw.exceptions import RenderingError
from pidraw.layout import apply_layout

_MAX_SIZE = 500 * 1024


class StructurizrRenderer(BaseRenderer):
    """Render Structurizr DSL architecture diagrams to SVG.

    Uses ``structurizr-cli`` to export to PlantUML, then renders
    via the native PlantUML converter + SvgBackend (no Graphviz needed).
    """

    name = "structurizr"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._resolved: str | None = path or self._find_structurizr()
        if not self._resolved:
            raise RenderingError(
                "structurizr-cli not found. "
                "Install from: https://github.com/structurizr/cli/releases"
            )

    @staticmethod
    def _find_structurizr() -> str | None:
        return shutil.which("structurizr-cli") or shutil.which("structurizr")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderingError("Structurizr source is empty")
        if "\x00" in source:
            raise RenderingError("Structurizr source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderingError(f"Structurizr source exceeds {_MAX_SIZE // 1024} KB limit")

        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_structurizr_")
            dsl_path = os.path.join(tmp_dir, "workspace.dsl")
            puml_dir = os.path.join(tmp_dir, "puml")

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
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RenderingError(
                    f"structurizr-cli failed (code {result.returncode}): {result.stderr.strip()}"
                )

            # Find the exported PlantUML file(s)
            puml_files = list(Path(puml_dir).glob("*.puml"))
            if not puml_files:
                raise RenderingError("structurizr-cli produced no PlantUML files")

            # Use the first non-key diagram
            puml_path = None
            for f in puml_files:
                if "-key" not in f.stem:
                    puml_path = f
                    break
            if puml_path is None:
                puml_path = puml_files[0]

            puml_source = puml_path.read_text(encoding="utf-8")

            # Render via native PlantUML pipeline
            converter = get_converter("plantuml")
            if converter is None:
                raise RenderingError("PlantUML converter not available")

            diagram = converter.parse(puml_source)
            diagram = apply_layout(diagram)

            backend = SvgBackend()
            svg = backend.render(diagram)

            if not svg.strip():
                raise RenderingError("Native rendering produced empty SVG")
            if "<svg" not in svg:
                raise RenderingError("Native rendering output does not contain <svg>")

            return svg

        except subprocess.TimeoutExpired:
            raise RenderingError("structurizr-cli timed out after 60s")
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"structurizr error: {exc}") from exc
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh
                sh.rmtree(tmp_dir, ignore_errors=True)
