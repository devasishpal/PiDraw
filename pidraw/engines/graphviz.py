"""Graphviz renderer powered by the ``dot`` command-line tool.

Detects ``dot`` on ``PATH``, feeds it DOT source through stdin,
and returns the generated SVG from stdout.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_INPUT_SIZE = 100 * 1024  # 100 KB
_RENDER_TIMEOUT = 30  # seconds
_SVG_ROOT_RE = re.compile(r"<\s*svg[\s>]", re.IGNORECASE)


class GraphvizRenderer(BaseRenderer):
    """Render Graphviz DOT source to SVG via the ``dot`` executable.

    The renderer pipes DOT source through ``dot -Tsvg``.  If the
    executable is not found on ``PATH`` a helpful error is raised
    at construction time.

    Examples
    --------
    >>> renderer = GraphvizRenderer()
    >>> svg = renderer.render("digraph { A -> B }")
    >>> svg.startswith("<svg")
    True

    """

    def __init__(self, dot_path: Optional[str] = None) -> None:
        """Initialise the renderer.

        Parameters
        ----------
        dot_path
            Explicit path to the ``dot`` executable.  When *None*
            (the default) the system ``PATH`` is searched.

        """
        self._dot_path = dot_path or self._find_dot()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, source: str) -> str:
        """Convert DOT source to SVG.

        Parameters
        ----------
        source
            Valid Graphviz DOT source code.

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

        svg = self._run_dot(source)
        self._validate_output(svg)

        return svg

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_dot() -> str:
        """Locate the ``dot`` executable on ``PATH``.

        Returns
        -------
        str
            Absolute path to ``dot``.

        Raises
        ------
        RenderingError
            If ``dot`` cannot be found.

        """
        exe: Optional[str] = shutil.which("dot")
        if exe is None:
            raise RenderingError(
                "Graphviz 'dot' is not installed or not on PATH. "
                "Install it from: https://graphviz.org/download/"
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
            raise RenderingError("Graphviz DOT source is empty")

        if len(source) > _MAX_INPUT_SIZE:
            raise RenderingError(
                f"Graphviz DOT source exceeds maximum size of {_MAX_INPUT_SIZE} bytes"
            )

        if "\x00" in source:
            raise RenderingError("Graphviz DOT source contains null bytes")

    @staticmethod
    def _validate_output(svg: str) -> None:
        """Check that the generated output is a valid SVG document.

        Validates the presence of an ``<svg>`` root element and
        attempts to parse the output as well-formed XML.

        Raises
        ------
        RenderingError
            If the SVG is empty, does not contain a root ``<svg>``
            element, or cannot be parsed as XML.

        """
        if not svg:
            raise RenderingError("Graphviz dot produced an empty SVG")

        if not _SVG_ROOT_RE.search(svg):
            raise RenderingError(
                "Graphviz dot output does not contain a valid <svg> root element"
            )

        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            raise RenderingError(
                f"Graphviz dot output is not valid XML: {exc}"
            ) from exc

    def _run_dot(self, source: str) -> str:
        """Pipe DOT source through ``dot -Tsvg`` and return the SVG.

        The DOT source is sent via stdin — no temporary files are
        needed.  Stderr is captured so syntax errors can be reported.
        """
        cmd = [self._dot_path, "-Tsvg"]

        try:
            result = subprocess.run(
                cmd,
                input=source.encode("utf-8"),
                capture_output=True,
                timeout=_RENDER_TIMEOUT,
                check=False,
            )
        except FileNotFoundError:
            raise RenderingError(
                f"dot executable not found at '{self._dot_path}'"
            )
        except subprocess.TimeoutExpired:
            raise RenderingError(
                f"Graphviz dot timed out after {_RENDER_TIMEOUT}s"
            )

        except Exception as exc:
            raise RenderingError(
                f"Graphviz dot rendering failed: {exc}"
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderingError(
                f"Graphviz dot exited with code {result.returncode}: {stderr}"
            )

        svg = result.stdout.decode("utf-8", errors="replace")
        return svg
