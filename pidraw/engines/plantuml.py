"""PlantUML renderer powered by the PlantUML CLI or Java jar."""

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
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError

_MAX_INPUT_SIZE = 100 * 1024
_RENDER_TIMEOUT = 60
_SVG_ROOT_RE = re.compile(r"<\s*svg[\s>]", re.IGNORECASE)

_PLANTUML_ENV_VAR = "PLANTUML_JAR"

_COMMON_JAR_PATHS: List[str] = [
    "/usr/local/lib/plantuml.jar",
    "/usr/share/plantuml/plantuml.jar",
    "/opt/plantuml/plantuml.jar",
    str(Path.home() / "plantuml.jar"),
    str(Path.home() / ".local" / "share" / "plantuml" / "plantuml.jar"),
]


def find_java() -> str:
    """Locate the ``java`` executable on ``PATH``."""
    exe: str | None = shutil.which("java")
    if exe is None:
        raise EngineNotAvailableError(
            "java",
            setup_command="Install Java Runtime Environment (JRE) 8 or later.",
        )
    return exe


def find_jar() -> str:
    """Locate the ``plantuml.jar`` on the filesystem."""
    jar: str | None = os.environ.get(_PLANTUML_ENV_VAR)
    if jar is not None and os.path.isfile(jar):
        return jar
    for candidate in _COMMON_JAR_PATHS:
        if os.path.isfile(candidate):
            return candidate
    raise EngineNotAvailableError(
        "plantuml.jar",
        setup_command="pip install pidraw[plantuml] or install plantuml JAR from https://plantuml.com/download",
    )


def find_plantuml() -> str:
    """Locate the ``plantuml`` executable on ``PATH``."""
    exe: str | None = shutil.which("plantuml")
    if exe is None:
        raise EngineNotAvailableError(
            "plantuml",
            setup_command="Install PlantUML via your package manager or set PLANTUML_JAR.",
        )
    return exe


class PlantUMLRenderer(BaseRenderer):
    name = "plantuml"

    def __init__(
        self,
        plantuml_path: Optional[str] = None,
        java_path: Optional[str] = None,
        jar_path: Optional[str] = None,
    ) -> None:
        self._cmd: Optional[List[str]] = None
        try:
            self._cmd = self._resolve_command(plantuml_path, java_path, jar_path)
        except EngineNotAvailableError:
            pass

    def render(self, source: str) -> str:
        self._validate_source(source)
        if self._cmd is not None:
            svg = self._run_plantuml(source)
        else:
            svg = self._run_native(source)
        self._validate_output(svg)
        return svg

    @staticmethod
    def _resolve_command(
        plantuml_path: Optional[str] = None,
        java_path: Optional[str] = None,
        jar_path: Optional[str] = None,
    ) -> List[str]:
        if plantuml_path is not None:
            return [plantuml_path]
        resolved = shutil.which("plantuml")
        if resolved is not None:
            return [resolved]
        if java_path is not None and jar_path is not None:
            return [java_path, "-jar", jar_path]
        java = shutil.which("java")
        if java is not None:
            jar: Optional[str] = os.environ.get(_PLANTUML_ENV_VAR)
            if jar is not None and os.path.isfile(jar):
                return [java, "-jar", jar]
            for candidate in _COMMON_JAR_PATHS:
                if os.path.isfile(candidate):
                    return [java, "-jar", candidate]
        raise EngineNotAvailableError(
            "plantuml",
            setup_command="pip install pidraw[plantuml] or install plantuml JAR from https://plantuml.com/download",
        )

    def _run_native(self, source: str) -> str:
        """Fallback native renderer when PlantUML CLI is absent or fails."""
        from pidraw.backend.svg import SvgBackend
        from pidraw.core.converters import get_converter
        from pidraw.layout import apply_layout

        converter = get_converter("plantuml")
        if converter is None:
            raise EngineNotAvailableError(
                "plantuml (native)",
                setup_command="Install PlantUML from https://plantuml.com/download",
            )
        try:
            diagram = converter.parse(source)
        except Exception as exc:
            raise RenderError("plantuml", f"Native converter failed: {exc}")
        diagram = apply_layout(diagram)
        backend = SvgBackend()
        try:
            svg = backend.render(diagram)
        except Exception as exc:
            raise RenderError("plantuml", f"SvgBackend failed: {exc}")
        return svg

    @staticmethod
    def _validate_source(source: str) -> None:
        if not source.strip():
            raise RenderError("plantuml", "PlantUML source is empty")
        if len(source) > _MAX_INPUT_SIZE:
            raise RenderError(
                "plantuml",
                f"PlantUML source exceeds maximum size of {_MAX_INPUT_SIZE} bytes",
            )
        if "\x00" in source:
            raise RenderError("plantuml", "PlantUML source contains null bytes")

    @staticmethod
    def _validate_output(svg: str) -> None:
        if not svg:
            raise RenderError("plantuml", "PlantUML produced an empty SVG")
        if not _SVG_ROOT_RE.search(svg):
            raise RenderError(
                "plantuml",
                "PlantUML output does not contain a valid <svg> root element",
            )
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            raise RenderError("plantuml", f"PlantUML output is not valid XML: {exc}")

    def _run_plantuml(self, source: str) -> str:
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
                raise RenderError(
                    "plantuml",
                    f"PlantUML did not produce the expected SVG file: {output_path}",
                )
            with open(output_path, "r", encoding="utf-8") as fh:
                return fh.read()
        except RenderError:
            raise
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("plantuml", _RENDER_TIMEOUT)
        except Exception as exc:
            raise RenderError("plantuml", f"PlantUML rendering failed: {exc}")
        finally:
            self._cleanup(tmp_dir)

    def _invoke_plantuml(self, input_path: str) -> None:
        assert self._cmd is not None
        cmd: List[str] = self._cmd + [
            "-tsvg",
            "-quiet",
            "-charset",
            "UTF-8",
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
            raise RenderError("plantuml", f"PlantUML executable not found at '{self._cmd[0]}'")

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RenderError(
                "plantuml",
                f"PlantUML exited with code {result.returncode}",
                stderr=stderr,
            )

    @staticmethod
    def _cleanup(tmp_dir: Optional[str]) -> None:
        if tmp_dir is not None and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass
