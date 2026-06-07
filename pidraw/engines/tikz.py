"""Renderer for TikZ diagrams.

Compiles ``.tex`` via ``pdflatex`` and converts to SVG via
``pdf2svg`` or ``dvisvgm``.

Because of the heavyweight toolchain this renderer is *opt-in* by default;
use ``TikzRenderer(force=True)`` to enable during registration.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_SIZE = 100 * 1024


class TikzRenderer(BaseRenderer):
    r"""Render TikZ ``\begin{tikzpicture}`` to SVG.

    Requires ``pdflatex`` (TeX Live / MiKTeX) and either ``pdf2svg``
    or ``dvisvgm`` on ``PATH``.
    """

    name = "tikz"

    def __init__(self, path: str | None = None) -> None:
        """Initialise (path not used; toolchain auto-detected)."""
        self._path = path
        self._pdflatex = shutil.which("pdflatex")
        self._pdf2svg = shutil.which("pdf2svg")
        self._dvisvgm = shutil.which("dvisvgm")

        if not self._pdflatex:
            raise RenderingError(
                "pdflatex not found. Install TeX Live or MiKTeX."
            )
        if not self._pdf2svg and not self._dvisvgm:
            raise RenderingError(
                "Neither pdf2svg nor dvisvgm found. "
                "Install one to convert PDF/DVI to SVG."
            )

    def _build_tex(self, source: str) -> str:
        return (
            "\\documentclass[tikz]{standalone}\n"
            "\\begin{document}\n"
            f"{source}\n"
            "\\end{document}\n"
        )

    def render(self, source: str) -> str:
        """Render a TikZ picture source to SVG."""
        if not source or not source.strip():
            raise RenderingError("TikZ source is empty")
        if "\x00" in source:
            raise RenderingError("TikZ source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderingError(f"TikZ source exceeds {_MAX_SIZE // 1024} KB limit")

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
                [self._pdflatex, "-interaction=nonstopmode",
                 "-output-directory", tmp_dir, tex_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                log = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
                raise RenderingError(
                    f"pdflatex failed (code {result.returncode}):\n{log}"
                )

            if self._pdf2svg:
                svg_result = subprocess.run(
                    [self._pdf2svg, pdf_path, svg_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if svg_result.returncode != 0:
                    raise RenderingError(
                        f"pdf2svg failed (code {svg_result.returncode}): "
                        f"{svg_result.stderr.strip()}"
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
                        raise RenderingError(
                            f"dvisvgm failed (code {svg_result.returncode}): "
                            f"{svg_result.stderr.strip()}"
                        )
                else:
                    raise RenderingError("No DVI file produced by pdflatex")

            if not os.path.isfile(svg_path):
                raise RenderingError("No SVG file produced by the converter")

            with open(svg_path, "r", encoding="utf-8") as f:
                svg = f.read()

            if not svg.strip():
                raise RenderingError("TikZ converter returned empty SVG")
            if "<svg" not in svg:
                raise RenderingError("TikZ output does not contain <svg>")

            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderingError(f"TikZ converter returned malformed XML: {exc}") from exc

            return svg

        except subprocess.TimeoutExpired:
            raise RenderingError("TikZ pdflatex timed out after 60s")
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"TikZ error: {exc}") from exc
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh

                sh.rmtree(tmp_dir, ignore_errors=True)
