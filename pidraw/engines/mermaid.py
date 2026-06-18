"""Mermaid diagram renderer with native fallback then mmdc CLI fallback."""

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

_EMPTY_SVG_RE = re.compile(r"<g\s+id\s*=\s*[\"']nodes[\"']\s*/>", re.IGNORECASE)

_TAG_RE = re.compile(r"<[^>]+>")


def _truncate_source(source: str, max_len: int = 120) -> str:
    """Truncate source for display in placeholder SVG, removing tags."""
    s = _TAG_RE.sub("", source).strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _sanitize_xml(text: str) -> str:
    """Minimal XML-escaping for SVG text content."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# Diagram types natively supported by the converter
_NATIVE_DIAGRAM_TYPES = {
    "flowchart",
    "graph",
    "sequencediagram",
    "classdiagram",
    "statediagram",
    "statediagram-v2",
    "erdiagram",
    "pie",
    "gantt",
}

# Diagram types that REQUIRE mmdc CLI
_CLI_ONLY_DIAGRAM_TYPES = {
    "gitgraph",
    "quadrantchart",
    "xychart",
    "timeline",
    "journey",
    "mindmap",
    "zenuml",
    "sankey",
    "requirementdiagram",
}

_DIAGRAM_TYPE_RE = re.compile(
    r"^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram"
    r"|stateDiagram-v2|erDiagram|pie|gantt|journey|timeline|mindmap"
    r"|gitgraph|quadrantChart|xychart|zenuml|sankey|requirementDiagram)\b",
    re.MULTILINE | re.IGNORECASE,
)


class MermaidRenderer(BaseRenderer):
    """Render Mermaid diagram source to SVG via native converter or mmdc CLI."""

    name = "mermaid"
    _has_mmdc: bool = False

    def __init__(self, mmdc_path: Optional[str] = None) -> None:
        self._mmdc_path: Optional[str] = None
        try:
            self._mmdc_path = mmdc_path or self._find_mmdc()
            self._has_mmdc = True
        except EngineNotAvailableError:
            self._mmdc_path = None

    def render(self, source: str) -> str:
        self._validate_source(source)

        type_match = _DIAGRAM_TYPE_RE.search(source)
        diagram_type = type_match.group(1) if type_match else ""

        # Always try native first (no deps, fast) for ALL types
        svg = self._try_native_safe(source)

        # Check if native output is empty or invalid
        if svg is None or self._is_empty_svg(svg):
            # Fall back to mmdc if available
            if self._has_mmdc:
                try:
                    mmdc_svg = self._run_mmdc(source)
                    self._validate_output(mmdc_svg)
                    svg = mmdc_svg
                except (RenderError, RenderTimeoutError):
                    pass  # keep native svg (even if empty/valid-but-degenerate)
            else:
                svg = None

        # If we still have nothing, produce a placeholder SVG
        if svg is None:
            label = _sanitize_xml(_truncate_source(source, 120))
            type_label = _sanitize_xml(diagram_type or "mermaid")
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg"'
                f' width="400" height="120" viewBox="0 0 400 120">'
                f'<rect width="100%" height="100%" fill="#f8f9fa" rx="8"/>'
                f'<text x="200" y="40" text-anchor="middle"'
                f' font-family="sans-serif" font-size="14" fill="#555">'
                f'[Mermaid: {type_label}]</text>'
                f'<text x="200" y="65" text-anchor="middle"'
                f' font-family="monospace" font-size="11" fill="#888">'
                f'{label}</text>'
                f'</svg>'
            )

        return svg

    def _try_native_safe(self, source: str) -> str | None:
        """Run native converter, returning None on any failure."""
        try:
            svg = self._run_native(source)
            self._validate_output(svg)
            return svg
        except (RenderError, RenderTimeoutError):
            return None

    @staticmethod
    def _is_empty_svg(svg: str) -> bool:
        """Detect if SVG has no visible content (empty nodes/edges)."""
        m = _EMPTY_SVG_RE.search(svg)
        if m:
            return True
        return len(svg) < 200

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
            raise RenderError("mermaid", f"mmdc executable not found at '{self._mmdc_path}'")

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderError(
                "mermaid",
                f"Mermaid CLI exited with code {result.returncode}",
                stderr=stderr,
            )

    def _run_native(self, source: str) -> str:
        from pidraw.backend.svg import SvgBackend
        from pidraw.core.converters import get_converter
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
