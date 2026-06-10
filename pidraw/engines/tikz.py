"""Renderer for TikZ diagrams via pdflatex + pdf2svg or native fallback."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderError, RenderTimeoutError

_MAX_SIZE = 100 * 1024


class TikzRenderer(BaseRenderer):
    r"""Render TikZ ``\begin{tikzpicture}`` to SVG.

    Prefers ``pdflatex`` + ``pdf2svg``/``dvisvgm`` for full TikZ support.
    Falls back to a native converter (common TikZ subset) when LaTeX
    tools are not available.
    """

    name = "tikz"
    _has_native_fallback: bool = False

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._pdflatex = shutil.which("pdflatex")
        self._pdf2svg = shutil.which("pdf2svg")
        self._dvisvgm = shutil.which("dvisvgm")

        if not self._pdflatex or not (self._pdf2svg or self._dvisvgm):
            self._pdflatex = None
            self._has_native_fallback = True

    def _build_tex(self, source: str) -> str:
        return (
            "\\documentclass[tikz]{standalone}\n"
            "\\begin{document}\n"
            f"{source}\n"
            "\\end{document}\n"
        )

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("tikz", "TikZ source is empty")
        if "\x00" in source:
            raise RenderError("tikz", "TikZ source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError("tikz", f"TikZ source exceeds {_MAX_SIZE // 1024} KB limit")

        if self._has_native_fallback:
            return self._run_native(source)

        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_tikz_")
            tex_path = os.path.join(tmp_dir, "diagram.tex")
            pdf_path = os.path.join(tmp_dir, "diagram.pdf")
            svg_path = os.path.join(tmp_dir, "diagram.svg")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(self._build_tex(source))

            assert self._pdflatex is not None
            result = subprocess.run(
                [
                    self._pdflatex,
                    "-interaction=nonstopmode",
                    "-output-directory",
                    tmp_dir,
                    tex_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                log = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
                raise RenderError("tikz", f"pdflatex failed (code {result.returncode}):\n{log}")

            if self._pdf2svg:
                svg_result = subprocess.run(
                    [self._pdf2svg, pdf_path, svg_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if svg_result.returncode != 0:
                    raise RenderError(
                        "tikz",
                        f"pdf2svg failed (code {svg_result.returncode}): {svg_result.stderr.strip()}",
                    )
            elif self._dvisvgm:
                dvi_path = pdf_path.replace(".pdf", ".dvi")
                if os.path.isfile(dvi_path):
                    svg_result = subprocess.run(
                        [self._dvisvgm, "--no-fonts", dvi_path, "-o", svg_path],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if svg_result.returncode != 0:
                        raise RenderError(
                            "tikz",
                            f"dvisvgm failed (code {svg_result.returncode}): {svg_result.stderr.strip()}",
                        )
                else:
                    raise RenderError("tikz", "No DVI file produced by pdflatex")

            if not os.path.isfile(svg_path):
                raise RenderError("tikz", "No SVG file produced by the converter")

            with open(svg_path, "r", encoding="utf-8") as f:
                svg = f.read()

            if not svg.strip():
                raise RenderError("tikz", "TikZ converter returned empty SVG")
            if "<svg" not in svg:
                raise RenderError("tikz", "TikZ output does not contain <svg>")

            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("tikz", f"TikZ converter returned malformed XML: {exc}")

            return svg
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("tikz", 60)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("tikz", f"TikZ error: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh

                sh.rmtree(tmp_dir, ignore_errors=True)

    def _run_native(self, source: str) -> str:
        """Native TikZ fallback using converter + SvgBackend."""
        from pidraw.backend.svg import SvgBackend
        from pidraw.core.converters import get_converter
        from pidraw.layout import apply_layout

        converter = get_converter("tikz")
        if converter is None:
            raise RenderError("tikz", "No TikZ converter available")
        try:
            diagram = converter.parse(source)
        except Exception as exc:
            raise RenderError("tikz", f"TikZ native converter failed: {exc}")
        diagram = apply_layout(diagram)
        backend = SvgBackend()
        try:
            svg = backend.render(diagram)
        except Exception as exc:
            raise RenderError("tikz", f"SvgBackend failed for TikZ: {exc}")
        return svg
