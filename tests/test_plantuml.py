"""Tests for the PlantUML renderer."""

from __future__ import annotations

import os
import subprocess
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from pidraw.engines.plantuml import PlantUMLRenderer, find_jar, find_java, find_plantuml
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError
from pidraw.registry import clear_registry, register_renderer

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def mock_cmd() -> Generator[None, None, None]:
    with patch.object(PlantUMLRenderer, "_resolve_command", return_value=["/usr/bin/plantuml"]):
        yield


@pytest.fixture
def renderer(mock_cmd: Any) -> PlantUMLRenderer:
    return PlantUMLRenderer()


# ------------------------------------------------------------------
# Utility function tests
# ------------------------------------------------------------------


class TestFindUtils:
    def test_find_java_missing(self) -> None:
        with patch("pidraw.engines.plantuml.shutil.which", return_value=None):
            with pytest.raises(EngineNotAvailableError, match="java"):
                find_java()

    def test_find_java_found(self) -> None:
        with patch("pidraw.engines.plantuml.shutil.which", return_value="/usr/bin/java"):
            assert find_java() == "/usr/bin/java"

    def test_find_plantuml_missing(self) -> None:
        with patch("pidraw.engines.plantuml.shutil.which", return_value=None):
            with pytest.raises(EngineNotAvailableError, match="plantuml"):
                find_plantuml()

    def test_find_plantuml_found(self) -> None:
        with patch("pidraw.engines.plantuml.shutil.which", return_value="/usr/bin/plantuml"):
            assert find_plantuml() == "/usr/bin/plantuml"

    def test_find_jar_env_var(self) -> None:
        with (
            patch.dict(os.environ, {"PLANTUML_JAR": "/opt/plantuml.jar"}),
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
        ):
            assert find_jar() == "/opt/plantuml.jar"

    def test_find_jar_env_var_not_found(self) -> None:
        with (
            patch.dict(os.environ, {"PLANTUML_JAR": "/nonexistent.jar"}),
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=False),
        ):
            with pytest.raises(EngineNotAvailableError, match="plantuml.jar"):
                find_jar()

    def test_find_jar_common_paths(self) -> None:
        def fake_isfile(path: str) -> bool:
            return path == "/usr/local/lib/plantuml.jar"

        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pidraw.engines.plantuml.os.path.isfile", side_effect=fake_isfile),
        ):
            assert find_jar() == "/usr/local/lib/plantuml.jar"

    def test_find_jar_nothing_found(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=False),
        ):
            with pytest.raises(EngineNotAvailableError, match="plantuml.jar"):
                find_jar()


# ------------------------------------------------------------------
# Command resolution
# ------------------------------------------------------------------


class TestCommandResolution:
    def test_explicit_plantuml_path(self) -> None:
        cmd = PlantUMLRenderer._resolve_command(plantuml_path="/custom/plantuml")
        assert cmd == ["/custom/plantuml"]

    def test_explicit_java_jar(self) -> None:
        cmd = PlantUMLRenderer._resolve_command(
            java_path="/usr/bin/java",
            jar_path="/opt/plantuml.jar",
        )
        assert cmd == ["/usr/bin/java", "-jar", "/opt/plantuml.jar"]

    def test_native_plantuml_on_path(self) -> None:
        with patch("pidraw.engines.plantuml.shutil.which", return_value="/usr/bin/plantuml"):
            cmd = PlantUMLRenderer._resolve_command()
            assert cmd == ["/usr/bin/plantuml"]

    def test_auto_java_jar(self) -> None:
        def _which(cmd: str) -> str | None:
            return "/usr/bin/java" if cmd == "java" else None

        with (
            patch("pidraw.engines.plantuml.shutil.which", side_effect=_which),
            patch.dict(os.environ, {"PLANTUML_JAR": "/opt/plantuml.jar"}),
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
        ):
            cmd = PlantUMLRenderer._resolve_command()
            assert cmd == ["/usr/bin/java", "-jar", "/opt/plantuml.jar"]

    def test_nothing_found(self) -> None:
        with patch("pidraw.engines.plantuml.shutil.which", return_value=None):
            with pytest.raises(EngineNotAvailableError, match="plantuml"):
                PlantUMLRenderer._resolve_command()


# ------------------------------------------------------------------
# Construction
# ------------------------------------------------------------------


class TestConstruction:
    def test_explicit_plantuml_path(self) -> None:
        r = PlantUMLRenderer(plantuml_path="/custom/plantuml")
        assert r._cmd == ["/custom/plantuml"]

    def test_explicit_java_jar(self) -> None:
        r = PlantUMLRenderer(java_path="/usr/bin/java", jar_path="/opt/p.jar")
        assert r._cmd == ["/usr/bin/java", "-jar", "/opt/p.jar"]


# ------------------------------------------------------------------
# Input validation
# ------------------------------------------------------------------


class TestInputValidation:
    def test_empty_source_raises(self, renderer: PlantUMLRenderer) -> None:
        with pytest.raises(RenderError, match="empty"):
            renderer.render("")

    def test_whitespace_only_raises(self, renderer: PlantUMLRenderer) -> None:
        with pytest.raises(RenderError, match="empty"):
            renderer.render("   \n  \n  ")

    def test_null_bytes_raises(self, renderer: PlantUMLRenderer) -> None:
        with pytest.raises(RenderError, match="null bytes"):
            renderer.render("@startuml\x00\nA -> B\n@enduml")

    def test_oversized_source_raises(self, renderer: PlantUMLRenderer) -> None:
        big = "A" * (100 * 1024 + 1)
        with pytest.raises(RenderError, match="exceeds maximum size"):
            renderer.render(big)


# ------------------------------------------------------------------
# Output validation
# ------------------------------------------------------------------


class TestOutputValidation:
    def test_empty_output_raises(self, renderer: PlantUMLRenderer) -> None:
        with patch.object(renderer, "_run_plantuml", return_value=""):
            with pytest.raises(RenderError, match="empty SVG"):
                renderer.render("@startuml\nA -> B\n@enduml")

    def test_non_svg_output_raises(self, renderer: PlantUMLRenderer) -> None:
        with patch.object(renderer, "_run_plantuml", return_value="<html></html>"):
            with pytest.raises(RenderError, match="valid <svg>"):
                renderer.render("@startuml\nA -> B\n@enduml")

    def test_malformed_xml_raises(self, renderer: PlantUMLRenderer) -> None:
        bad_svg = "<svg><unclosed></svg>"
        with patch.object(renderer, "_run_plantuml", return_value=bad_svg):
            with pytest.raises(RenderError, match="valid XML"):
                renderer.render("@startuml\nA -> B\n@enduml")


# ------------------------------------------------------------------
# PlantUML subprocess invocation
# ------------------------------------------------------------------


def _completed(
    returncode: int = 0,
    stderr: str = "",
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        args=["plantuml"],
        returncode=returncode,
        stdout=b"",
        stderr=stderr.encode("utf-8"),
    )


class TestPlantUMLInvocation:
    def test_sequence_diagram(self, renderer: PlantUMLRenderer) -> None:
        """@startuml / @enduml with sequence diagram."""
        source = "@startuml\nAlice -> Bob: hello\n@enduml"
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with (
            patch(
                "pidraw.engines.plantuml.tempfile.mkdtemp",
                return_value="/tmp/pidraw_pu_test",
            ) as mock_mkdtemp,
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.plantuml.subprocess.run") as mock_run,
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
            patch("pidraw.engines.plantuml.os.path.isdir", return_value=True),
            patch("pidraw.engines.plantuml.shutil.rmtree") as mock_rmtree,
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg: MagicMock = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [
                MagicMock(),
                mock_file_svg,
            ]

            result = renderer.render(source)

            assert result == fake_svg
            mock_mkdtemp.assert_called_once()
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "/usr/bin/plantuml"
            assert "-tsvg" in cmd
            assert "-quiet" in cmd
            assert "-charset" in cmd
            assert "UTF-8" in cmd
            assert cmd[-1].endswith("diagram.puml")
            mock_rmtree.assert_called_once_with("/tmp/pidraw_pu_test")

    def test_class_diagram(self, renderer: PlantUMLRenderer) -> None:
        source = "@startuml\nclass Animal\n@enduml"
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.plantuml.subprocess.run") as mock_run,
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
            patch("pidraw.engines.plantuml.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]

            result = renderer.render(source)
            assert result == fake_svg

    def test_er_diagram(self, renderer: PlantUMLRenderer) -> None:
        source = "@startuml\nentity Order {\n  id: int\n}\n@enduml"
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.plantuml.subprocess.run") as mock_run,
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
            patch("pidraw.engines.plantuml.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]

            result = renderer.render(source)
            assert result == fake_svg

    def test_activity_diagram(self, renderer: PlantUMLRenderer) -> None:
        source = "@startuml\n:Hello;\n:World;\n@enduml"
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.plantuml.subprocess.run") as mock_run,
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
            patch("pidraw.engines.plantuml.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]

            result = renderer.render(source)
            assert result == fake_svg

    def test_mindmap(self, renderer: PlantUMLRenderer) -> None:
        source = "@startmindmap\n* Root\n** Leaf\n@endmindmap"
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.plantuml.subprocess.run") as mock_run,
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
            patch("pidraw.engines.plantuml.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]

            result = renderer.render(source)
            assert result == fake_svg

    def test_svg_file_not_found(self, renderer: PlantUMLRenderer) -> None:
        source = "@startuml\nA -> B\n@enduml"

        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open"),
            patch("pidraw.engines.plantuml.subprocess.run") as mock_run,
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=False),
            patch("pidraw.engines.plantuml.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(0)

            with pytest.raises(RenderError, match="did not produce"):
                renderer.render(source)

    def test_plantuml_returns_nonzero(self, renderer: PlantUMLRenderer) -> None:
        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open"),
            patch("pidraw.engines.plantuml.subprocess.run") as mock_run,
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
            patch("pidraw.engines.plantuml.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(1, "Syntax error")

            with pytest.raises(RenderError, match="exited with code"):
                renderer.render("@startuml\ninvalid\n@enduml")

    def test_plantuml_times_out(self, renderer: PlantUMLRenderer) -> None:
        _timeout = subprocess.TimeoutExpired(cmd="plantuml", timeout=60)
        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open"),
            patch("pidraw.engines.plantuml.subprocess.run", side_effect=_timeout),
            patch("pidraw.engines.plantuml.shutil.rmtree"),
        ):
            with pytest.raises(RenderTimeoutError, match="timed out"):
                renderer.render("@startuml\nA -> B\n@enduml")

    def test_plantuml_binary_missing(self, renderer: PlantUMLRenderer) -> None:
        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open"),
            patch("pidraw.engines.plantuml.subprocess.run", side_effect=FileNotFoundError),
            patch("pidraw.engines.plantuml.shutil.rmtree"),
        ):
            with pytest.raises(RenderError, match="not found"):
                renderer.render("@startuml\nA -> B\n@enduml")

    def test_cleanup_on_failure(self, renderer: PlantUMLRenderer) -> None:
        _timeout = subprocess.TimeoutExpired(cmd="plantuml", timeout=60)
        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open"),
            patch("pidraw.engines.plantuml.subprocess.run", side_effect=_timeout),
            patch("pidraw.engines.plantuml.os.path.isdir", return_value=True),
            patch("pidraw.engines.plantuml.shutil.rmtree") as mock_rmtree,
        ):
            with pytest.raises(RenderTimeoutError):
                renderer.render("@startuml\nA -> B\n@enduml")
            mock_rmtree.assert_called_once_with("/tmp/pu_test")

    def test_cleanup_on_success(self, renderer: PlantUMLRenderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with (
            patch("pidraw.engines.plantuml.tempfile.mkdtemp", return_value="/tmp/pu_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.plantuml.subprocess.run") as mock_run,
            patch("pidraw.engines.plantuml.os.path.isfile", return_value=True),
            patch("pidraw.engines.plantuml.os.path.isdir", return_value=True),
            patch("pidraw.engines.plantuml.shutil.rmtree") as mock_rmtree,
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]

            renderer.render("@startuml\nA -> B\n@enduml")
            mock_rmtree.assert_called_once_with("/tmp/pu_test")


# ------------------------------------------------------------------
# Auto-registration
# ------------------------------------------------------------------


class TestAutoRegistration:
    def test_plantuml_renderer_can_be_registered(self) -> None:
        clear_registry()
        register_renderer("plantuml", PlantUMLRenderer(plantuml_path="/fake/plantuml"))
        from pidraw.registry import get_renderer

        r = get_renderer("plantuml")
        assert isinstance(r, PlantUMLRenderer)

    def test_render_via_registry(self) -> None:
        clear_registry()
        r = PlantUMLRenderer(plantuml_path="/fake/plantuml")
        register_renderer("plantuml", r)

        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch.object(r, "_run_plantuml", return_value=fake_svg):
            from pidraw.renderer import render as public_render

            result = public_render("@startuml\nA -> B\n@enduml")
            assert result.svg == fake_svg

    def test_detection_integration(self) -> None:
        """End-to-end: @startuml source is detected and rendered."""
        clear_registry()
        r = PlantUMLRenderer(plantuml_path="/fake/plantuml")
        register_renderer("plantuml", r)

        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch.object(r, "_run_plantuml", return_value=fake_svg):
            from pidraw.renderer import render as public_render

            for source in [
                "@startuml\nA -> B\n@enduml",
                "@startmindmap\n* Root\n@endmindmap",
                "@startgantt\n[Task] lasts 1 day\n@endgantt",
                "@startsalt\n{\nJust text\n}\n@endsalt",
                "@startjson\n{}\n@endjson",
                "@startyaml\nkey: val\n@endyaml",
            ]:
                result = public_render(source)
                assert result.svg == fake_svg, f"Failed for: {source[:30]}..."
