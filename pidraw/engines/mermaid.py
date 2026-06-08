"""Mermaid diagram renderer powered by the Mermaid CLI (``mmdc``)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError

_MAX_INPUT_SIZE = 100 * 1024
_RENDER_TIMEOUT = 30
_SVG_ROOT_RE = re.compile(r"<\s*svg[\s>]", re.IGNORECASE)

# Diagram types natively supported by the converter
_NATIVE_DIAGRAM_TYPES = {
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "erDiagram",
    "pie",
    "gantt",
}

# Diagram types that REQUIRE mmdc CLI
_CLI_ONLY_DIAGRAM_TYPES = {
    "gitgraph",
    "quadrantChart",
    "xychart",
    "timeline",
    "journey",
    "mindmap",
    "zenuml",
    "sankey",
    "requirementDiagram",
    "stateDiagram-v2",
}

_DIAGRAM_TYPE_RE = re.compile(
    r"^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram"
    r"|stateDiagram-v2|erDiagram|pie|gantt|journey|timeline|mindmap"
    r"|gitgraph|quadrantChart|xychart|zenuml|sankey|requirementDiagram)\b",
    re.MULTILINE,
)


class MermaidRenderer(BaseRenderer):
    """Render Mermaid diagram source to SVG via the Mermaid CLI."""

    name = "mermaid"
    _has_native_fallback: bool = False

    def __init__(self, mmdc_path: Optional[str] = None) -> None:
        self._mmdc_path: Optional[str] = None
        try:
            self._mmdc_path = mmdc_path or self._find_mmdc()
        except EngineNotAvailableError:
            self._mmdc_path = None
            self._has_native_fallback = True

    def render(self, source: str) -> str:
        self._validate_source(source)

        # Detect diagram type for unsupported types without CLI
        if self._mmdc_path is None and self._has_native_fallback:
            type_match = _DIAGRAM_TYPE_RE.search(source)
            if type_match:
                diagram_type = type_match.group(1)
                if diagram_type in _CLI_ONLY_DIAGRAM_TYPES or (
                    diagram_type not in _NATIVE_DIAGRAM_TYPES
                ):
                    raise RenderError(
                        "mermaid",
                        f"Diagram type {diagram_type!r} requires mmdc CLI. "
                        "Install with: npm install -g @mermaid-js/mermaid-cli",
                    )

        if self._mmdc_path is not None:
            svg = self._run_mmdc(source)
        else:
            svg = self._run_native(source)

        self._validate_output(svg)
        return svg

    @staticmethod
    def _find_mmdc() -> str:
        exe: Optional[str] = shutil.which("mmdc")
        if exe is None:
            raise EngineNotAvailableError(
                "mmdc",
                setup_command="npm install -g @mermaid-js/mermaid-cli",
            )
        return exe

    @staticmethod
    def _validate_source(source: str) -> None:
        if not source.strip():
            raise RenderError("mermaid", "Mermaid source is empty")
        if len(source) > _MAX_INPUT_SIZE:
            raise RenderError(
                "mermaid",
                f"Mermaid source exceeds maximum size of {_MAX_INPUT_SIZE} bytes",
            )
        if "\x00" in source:
            raise RenderError("mermaid", "Mermaid source contains null bytes")

    @staticmethod
    def _validate_output(svg: str) -> None:
        if not svg:
            raise RenderError("mermaid", "Mermaid CLI produced an empty SVG")
        if not _SVG_ROOT_RE.search(svg):
            raise RenderError(
                "mermaid",
                "Mermaid output does not contain a valid <svg> root element",
            )

    def _run_mmdc(self, source: str) -> str:
        tmp_dir: Optional[str] = None
        input_path: Optional[str] = None
        output_path: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_mermaid_")
            input_path = os.path.join(tmp_dir, "diagram.mmd")
            output_path = os.path.join(tmp_dir, "diagram.svg")
            with open(input_path, "w", encoding="utf-8") as fh:
                fh.write(source)
            self._invoke_mmdc(input_path, output_path)
            with open(output_path, "r", encoding="utf-8") as fh:
                return fh.read()
        except RenderError:
            raise
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("mermaid", _RENDER_TIMEOUT)
        except Exception as exc:
            raise RenderError("mermaid", f"Mermaid CLI rendering failed: {exc}")
        finally:
            self._cleanup(tmp_dir)

    def _invoke_mmdc(self, input_path: str, output_path: str) -> None:
        assert self._mmdc_path is not None
        cmd = [
            self._mmdc_path,
            "--input",
            input_path,
            "--output",
            output_path,
            "--quiet",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=_RENDER_TIMEOUT,
                check=False,
            )
        except FileNotFoundError:
            raise RenderError(
                "mermaid", f"mmdc executable not found at '{self._mmdc_path}'"
            )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderError(
                "mermaid",
                f"Mermaid CLI exited with code {result.returncode}",
                stderr=stderr,
            )

    def _run_native(self, source: str) -> str:
        """Fallback native renderer for basic diagram types when mmdc is absent."""
        from pidraw.core.converters import get_converter
        from pidraw.backend.svg import SvgBackend
        from pidraw.layout import apply_layout

        converter = get_converter("mermaid")
        if converter is None:
            raise EngineNotAvailableError(
                "mermaid (native)",
                setup_command="npm install -g @mermaid-js/mermaid-cli",
            )
        try:
            diagram = converter.parse(source)
        except Exception as exc:
            raise RenderError("mermaid", f"Native converter failed: {exc}")
        diagram = apply_layout(diagram)
        backend = SvgBackend()
        try:
            svg = backend.render(diagram)
        except Exception as exc:
            raise RenderError("mermaid", f"SvgBackend failed: {exc}")
        return svg

    @staticmethod
    def _cleanup(tmp_dir: Optional[str]) -> None:
        if tmp_dir is not None and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass
