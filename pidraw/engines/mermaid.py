"""Mermaid diagram renderer powered by the Mermaid CLI (``mmdc``).

Detects ``mmdc`` on ``PATH``, calls it via ``subprocess``, and
returns the generated SVG.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_INPUT_SIZE = 100 * 1024  # 100 KB
_RENDER_TIMEOUT = 30  # seconds
_SVG_ROOT_RE = re.compile(r"<\s*svg[\s>]", re.IGNORECASE)


class MermaidRenderer(BaseRenderer):
    """Render Mermaid diagram source to SVG via the Mermaid CLI.

    The renderer shells out to ``mmdc`` (Mermaid CLI).  If the
    executable is not found on ``PATH`` a helpful error is raised
    at construction time.

    Examples
    --------
    >>> renderer = MermaidRenderer()
    >>> svg = renderer.render("graph TD; A-->B;")
    >>> svg.startswith("<svg")
    True

    """

    def __init__(self, mmdc_path: Optional[str] = None) -> None:
        """Initialise the renderer.

        Parameters
        ----------
        mmdc_path
            Explicit path to the ``mmdc`` executable.  When *None*
            (the default) the system ``PATH`` is searched.

        """
        self._mmdc_path = mmdc_path or self._find_mmdc()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, source: str) -> str:
        """Convert Mermaid source to SVG.

        Parameters
        ----------
        source
            Valid Mermaid diagram source code.

        Returns
        -------
        str
            The rendered SVG document.

        Raises
        ------
        RenderingError
            If the source is too large, contains dangerous characters,
            the CLI fails, times out, or produces invalid output.

        """
        self._validate_source(source)

        svg = self._run_mmdc(source)
        self._validate_output(svg)

        return svg

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_mmdc() -> str:
        """Locate the ``mmdc`` executable on ``PATH``.

        Returns
        -------
        str
            Absolute path to ``mmdc``.

        Raises
        ------
        RenderingError
            If ``mmdc`` cannot be found.

        """
        exe: Optional[str] = shutil.which("mmdc")
        if exe is None:
            raise RenderingError(
                "mmdc (Mermaid CLI) is not installed or not on PATH. "
                "Install it with: npm install -g @mermaid-js/mermaid-cli"
            )
        return exe

    @staticmethod
    def _validate_source(source: str) -> None:
        """Validate diagram source before attempting to render it.

        Raises
        ------
        RenderingError
            If the source is empty, exceeds the size limit, or
            contains null bytes.

        """
        if not source.strip():
            raise RenderingError("Mermaid source is empty")

        if len(source) > _MAX_INPUT_SIZE:
            raise RenderingError(
                f"Mermaid source exceeds maximum size of {_MAX_INPUT_SIZE} bytes"
            )

        if "\x00" in source:
            raise RenderingError("Mermaid source contains null bytes")

    @staticmethod
    def _validate_output(svg: str) -> None:
        """Check that the generated output is a valid SVG document.

        Raises
        ------
        RenderingError
            If the SVG is empty or does not contain a root ``<svg>``
            element.

        """
        if not svg:
            raise RenderingError("Mermaid CLI produced an empty SVG")

        if not _SVG_ROOT_RE.search(svg):
            raise RenderingError(
                "Mermaid CLI output does not contain a valid <svg> root element"
            )

    def _run_mmdc(self, source: str) -> str:
        """Write source to a temp file, invoke mmdc, and return the SVG.

        Temporary files are always cleaned up, even on failure.
        """
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

        except RenderingError:
            raise
        except subprocess.TimeoutExpired:
            raise RenderingError(
                f"Mermaid CLI timed out after {_RENDER_TIMEOUT}s"
            )
        except Exception as exc:
            raise RenderingError(
                f"Mermaid CLI rendering failed: {exc}"
            ) from exc
        finally:
            self._cleanup(tmp_dir)

    def _invoke_mmdc(self, input_path: str, output_path: str) -> None:
        """Run the ``mmdc`` binary as a subprocess.

        The command is always invoked as a list to avoid shell
        injection.
        """
        cmd = [
            self._mmdc_path,
            "--input", input_path,
            "--output", output_path,
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
            raise RenderingError(
                f"mmdc executable not found at '{self._mmdc_path}'"
            )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderingError(
                f"Mermaid CLI exited with code {result.returncode}: {stderr}"
            )

    @staticmethod
    def _cleanup(tmp_dir: Optional[str]) -> None:
        """Remove a temporary directory tree silently."""
        if tmp_dir is not None and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass
