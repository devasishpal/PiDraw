"""D2 renderer powered by the official ``d2`` command-line tool.

Detects ``d2`` on ``PATH``, writes source to a temporary ``.d2``
file, invokes the binary, and returns the generated SVG.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_INPUT_SIZE = 100 * 1024  # 100 KB
_RENDER_TIMEOUT = 30  # seconds
_SVG_ROOT_RE = re.compile(r"<\s*svg[\s>]", re.IGNORECASE)


def find_d2() -> str:
    """Locate the ``d2`` executable on ``PATH``.

    Returns
    -------
    str
        Absolute path to ``d2``.

    Raises
    ------
    RenderingError
        If ``d2`` cannot be found.

    """
    exe: Optional[str] = shutil.which("d2")
    if exe is None:
        raise RenderingError(
            "D2 is not installed or not on PATH. "
            "Install it from: https://d2lang.com/tour/install/"
        )
    return exe


class D2Renderer(BaseRenderer):
    """Render D2 diagram source to SVG via the official ``d2`` binary.

    The renderer shells out to ``d2`` (d2lang.com).  If the
    executable is not found on ``PATH`` a helpful error is raised
    at construction time.

    Examples
    --------
    >>> renderer = D2Renderer()
    >>> svg = renderer.render("x -> y")
    >>> svg.startswith("<svg")
    True

    """

    def __init__(self, d2_path: Optional[str] = None) -> None:
        """Initialise the renderer.

        Parameters
        ----------
        d2_path
            Explicit path to the ``d2`` executable.  When *None*
            (the default) the system ``PATH`` is searched.

        """
        self._d2_path = d2_path or find_d2()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, source: str) -> str:
        """Convert D2 source to SVG.

        Parameters
        ----------
        source
            Valid D2 diagram source code.

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

        svg = self._run_d2(source)
        self._validate_output(svg)

        return svg

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
            raise RenderingError("D2 source is empty")

        if len(source) > _MAX_INPUT_SIZE:
            raise RenderingError(
                f"D2 source exceeds maximum size of {_MAX_INPUT_SIZE} bytes"
            )

        if "\x00" in source:
            raise RenderingError("D2 source contains null bytes")

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
            raise RenderingError("D2 produced an empty SVG")

        if not _SVG_ROOT_RE.search(svg):
            raise RenderingError(
                "D2 output does not contain a valid <svg> root element"
            )

        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            raise RenderingError(
                f"D2 output is not valid XML: {exc}"
            ) from exc

    def _run_d2(self, source: str) -> str:
        """Write source to a temp ``.d2`` file and return the SVG.

        Temporary files are always cleaned up, even on failure.
        """
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

        except RenderingError:
            raise
        except subprocess.TimeoutExpired:
            raise RenderingError(
                f"D2 timed out after {_RENDER_TIMEOUT}s"
            )
        except Exception as exc:
            raise RenderingError(
                f"D2 rendering failed: {exc}"
            ) from exc
        finally:
            self._cleanup(tmp_dir)

    def _invoke_d2(self, input_path: str, output_path: str) -> None:
        """Run ``d2`` as a subprocess.

        The command is always invoked as a list to avoid shell
        injection.
        """
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
            raise RenderingError(
                f"d2 executable not found at '{self._d2_path}'"
            )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderingError(
                f"D2 exited with code {result.returncode}: {stderr}"
            )

    @staticmethod
    def _cleanup(tmp_dir: Optional[str]) -> None:
        """Remove a temporary directory tree silently."""
        if tmp_dir is not None and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass
