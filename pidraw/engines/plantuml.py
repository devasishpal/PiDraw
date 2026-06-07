"""PlantUML renderer powered by the PlantUML CLI or Java jar.

Detects the ``plantuml`` executable or ``java`` + ``plantuml.jar``
on the system, writes source to a temporary ``.puml`` file, invokes
PlantUML, and returns the generated SVG.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_INPUT_SIZE = 100 * 1024  # 100 KB
_RENDER_TIMEOUT = 60  # seconds (PlantUML can be slower for complex diagrams)
_SVG_ROOT_RE = re.compile(r"<\s*svg[\s>]", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Utility functions (public for downstream discovery)
# ---------------------------------------------------------------------------

_PLANTUML_ENV_VAR = "PLANTUML_JAR"

_COMMON_JAR_PATHS: List[str] = [
    "/usr/local/lib/plantuml.jar",
    "/usr/share/plantuml/plantuml.jar",
    "/opt/plantuml/plantuml.jar",
    str(Path.home() / "plantuml.jar"),
    str(Path.home() / ".local" / "share" / "plantuml" / "plantuml.jar"),
]


def find_java() -> str:
    """Locate the ``java`` executable on ``PATH``.

    Returns
    -------
    str
        Absolute path to ``java``.

    Raises
    ------
    RenderingError
        If ``java`` cannot be found.

    """
    exe: Optional[str] = shutil.which("java")
    if exe is None:
        raise RenderingError(
            "Java is not installed or not on PATH. "
            "Install Java Runtime Environment (JRE) 8 or later."
        )
    return exe


def find_jar() -> str:
    """Locate the ``plantuml.jar`` on the filesystem.

    Checks the ``PLANTUML_JAR`` environment variable first, then
    searches a set of common installation paths.

    Returns
    -------
    str
        Absolute path to ``plantuml.jar``.

    Raises
    ------
    RenderingError
        If the jar cannot be found.

    """
    jar: Optional[str] = os.environ.get(_PLANTUML_ENV_VAR)
    if jar is not None and os.path.isfile(jar):
        return jar

    for candidate in _COMMON_JAR_PATHS:
        if os.path.isfile(candidate):
            return candidate

    raise RenderingError(
        f"plantuml.jar not found. Set the {_PLANTUML_ENV_VAR} environment "
        "variable to the jar path, or install PlantUML via:\n"
        "  brew install plantuml\n"
        "  apt install plantuml\n"
        "  choco install plantuml\n"
        "Or download from: https://plantuml.com/download"
    )


def find_plantuml() -> str:
    """Locate the ``plantuml`` executable on ``PATH``.

    Some package managers install a native ``plantuml`` wrapper
    script (e.g. Homebrew, Debian).

    Returns
    -------
    str
        Absolute path to ``plantuml``.

    Raises
    ------
    RenderingError
        If the executable cannot be found.

    """
    exe: Optional[str] = shutil.which("plantuml")
    if exe is None:
        raise RenderingError(
            "PlantUML executable not found on PATH. "
            "Install it via your package manager or set PLANTUML_JAR."
        )
    return exe


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class PlantUMLRenderer(BaseRenderer):
    r"""Render PlantUML source to SVG via ``plantuml`` or ``java -jar``.

    The renderer supports two execution modes:

    1. **Native executable** — the ``plantuml`` binary on ``PATH``
       (available via Homebrew, APT, Chocolatey, etc.).
    2. **Java jar** — ``java -jar plantuml.jar`` when the native
       binary is not available.

    Detection order: native executable ``→`` ``PLANTUML_JAR`` env
    var ``→`` common jar locations.

    Examples
    --------
    >>> renderer = PlantUMLRenderer()
    >>> svg = renderer.render("@startuml\\nA -> B\\n@enduml")
    >>> svg.startswith("<svg")
    True

    """

    def __init__(
        self,
        plantuml_path: Optional[str] = None,
        java_path: Optional[str] = None,
        jar_path: Optional[str] = None,
    ) -> None:
        """Initialise the renderer.

        Parameters
        ----------
        plantuml_path
            Explicit path to the ``plantuml`` executable.
        java_path
            Explicit path to the ``java`` executable (used with
            *jar_path*).
        jar_path
            Explicit path to ``plantuml.jar`` (used with *java_path*).

        """
        self._cmd: List[str] = self._resolve_command(plantuml_path, java_path, jar_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, source: str) -> str:
        """Convert PlantUML source to SVG.

        Parameters
        ----------
        source
            Valid PlantUML source code (with ``@startuml`` / ``@enduml``
            or other ``@start*`` / ``@end*`` delimiters).

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

        svg = self._run_plantuml(source)
        self._validate_output(svg)

        return svg

    # ------------------------------------------------------------------
    # Command resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_command(
        plantuml_path: Optional[str] = None,
        java_path: Optional[str] = None,
        jar_path: Optional[str] = None,
    ) -> List[str]:
        """Determine the command prefix to invoke PlantUML.

        Returns a list suitable for ``subprocess.run``, e.g.
        ``["plantuml"]`` or ``["java", "-jar", "/path/jar"]``.
        """
        # 1. Explicit plantuml binary
        if plantuml_path is not None:
            return [plantuml_path]

        # 2. Try native plantuml on PATH
        resolved = shutil.which("plantuml")
        if resolved is not None:
            return [resolved]

        # 3. Explicit java + jar
        if java_path is not None and jar_path is not None:
            return [java_path, "-jar", jar_path]

        # 4. Auto-detect java + jar
        try:
            j = find_java()
            jar = find_jar()
            return [j, "-jar", jar]
        except RenderingError:
            raise RenderingError(
                "PlantUML renderer requires either:\n"
                "  1. 'plantuml' executable on PATH, or\n"
                "  2. Java + plantuml.jar (set PLANTUML_JAR env var)\n"
                "Install: https://plantuml.com/download"
            )

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
            raise RenderingError("PlantUML source is empty")

        if len(source) > _MAX_INPUT_SIZE:
            raise RenderingError(
                f"PlantUML source exceeds maximum size of {_MAX_INPUT_SIZE} bytes"
            )

        if "\x00" in source:
            raise RenderingError("PlantUML source contains null bytes")

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
            raise RenderingError("PlantUML produced an empty SVG")

        if not _SVG_ROOT_RE.search(svg):
            raise RenderingError(
                "PlantUML output does not contain a valid <svg> root element"
            )

        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            raise RenderingError(
                f"PlantUML output is not valid XML: {exc}"
            ) from exc

    def _run_plantuml(self, source: str) -> str:
        """Write source to a temp ``.puml`` file and return the SVG.

        Temporary files are always cleaned up, even on failure.
        """
        tmp_dir: Optional[str] = None
        input_path: Optional[str] = None

        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_plantuml_")
            input_path = os.path.join(tmp_dir, "diagram.puml")

            with open(input_path, "w", encoding="utf-8") as fh:
                fh.write(source)

            self._invoke_plantuml(input_path)

            output_path = input_path.replace(".puml", ".svg")
            if not os.path.isfile(output_path):
                raise RenderingError(
                    f"PlantUML did not produce the expected SVG file: {output_path}"
                )

            with open(output_path, "r", encoding="utf-8") as fh:
                return fh.read()

        except RenderingError:
            raise
        except subprocess.TimeoutExpired:
            raise RenderingError(
                f"PlantUML timed out after {_RENDER_TIMEOUT}s"
            )
        except Exception as exc:
            raise RenderingError(
                f"PlantUML rendering failed: {exc}"
            ) from exc
        finally:
            self._cleanup(tmp_dir)

    def _invoke_plantuml(self, input_path: str) -> None:
        """Run PlantUML as a subprocess.

        The command is always constructed as a list to avoid shell
        injection.
        """
        cmd: List[str] = self._cmd + [
            "-tsvg",
            "-quiet",
            "-charset", "UTF-8",
            input_path,
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
                f"PlantUML executable not found at '{self._cmd[0]}'"
            )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderingError(
                f"PlantUML exited with code {result.returncode}: {stderr}"
            )

    @staticmethod
    def _cleanup(tmp_dir: Optional[str]) -> None:
        """Remove a temporary directory tree silently."""
        if tmp_dir is not None and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass
