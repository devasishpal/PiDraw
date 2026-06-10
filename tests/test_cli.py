"""Integration tests for the PiDraw CLI."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from typer.testing import CliRunner

from pidraw.cli.main import app
from pidraw.registry import clear_registry

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_registry() -> Generator[None, None, None]:
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_output(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "pidraw v" in result.stdout


# ---------------------------------------------------------------------------
# plugins
# ---------------------------------------------------------------------------


class TestPlugins:
    def test_plugins_output(self) -> None:
        result = runner.invoke(app, ["plugins"])
        assert result.exit_code == 0
        assert "Total:" in result.stdout
        assert "registered" in result.stdout

    def test_plugins_after_registration(self) -> None:
        from pidraw.engines.base import BaseRenderer
        from pidraw.registry import register_renderer

        class FakeRenderer(BaseRenderer):
            name = "test"

            def render(self, source: str) -> str:
                return "<svg></svg>"

        register_renderer("test", FakeRenderer())
        result = runner.invoke(app, ["plugins"])
        assert result.exit_code == 0
        assert "test" in result.stdout


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------


class TestDetect:
    def _write_source(self, content: str) -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_detect_mermaid(self) -> None:
        path = self._write_source("graph TD\n    A-->B")
        try:
            result = runner.invoke(app, ["detect", path])
            assert result.exit_code == 0
            assert "Language:" in result.stdout
            assert "mermaid" in result.stdout
            assert "Confidence:" in result.stdout
            assert "Renderer:" in result.stdout
        finally:
            os.unlink(path)

    def test_detect_unknown(self) -> None:
        path = self._write_source("some random text without diagram syntax")
        try:
            result = runner.invoke(app, ["detect", path])
            assert result.exit_code == 0
            assert "unknown" in result.stdout
            assert "0%" in result.stdout
        finally:
            os.unlink(path)

    def test_detect_plantuml(self) -> None:
        path = self._write_source("@startuml\nA-->B\n@enduml")
        try:
            result = runner.invoke(app, ["detect", path])
            assert result.exit_code == 0
            assert "plantuml" in result.stdout
        finally:
            os.unlink(path)

    def test_detect_file_not_found(self) -> None:
        result = runner.invoke(app, ["detect", "nonexistent.diag"])
        assert result.exit_code != 0

    def test_detect_verbose(self) -> None:
        path = self._write_source("graph TD\n    A-->B")
        try:
            result = runner.invoke(app, ["detect", path, "--verbose"])
            assert result.exit_code == 0
            assert "Pattern:" in result.stdout or "Language:" in result.stdout
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


class TestAnalyze:
    def _write_source(self, content: str) -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_analyze_mermaid(self) -> None:
        path = self._write_source("graph TD\n    A-->B")
        try:
            result = runner.invoke(app, ["analyze", path])
            assert result.exit_code == 0
            assert "Language:" in result.stdout
            assert "mermaid" in result.stdout
            assert "Confidence:" in result.stdout
            assert "Renderer:" in result.stdout
        finally:
            os.unlink(path)

    def test_analyze_unknown(self) -> None:
        path = self._write_source("not a diagram")
        try:
            result = runner.invoke(app, ["analyze", path])
            assert result.exit_code == 0
            assert "unknown" in result.stdout
            assert "Warnings:" in result.stdout
        finally:
            os.unlink(path)

    def test_analyze_without_render(self) -> None:
        path = self._write_source("graph TD\n    A-->B")
        try:
            result = runner.invoke(app, ["analyze", path, "--no-render"])
            assert result.exit_code == 0
            assert "mermaid" in result.stdout
        finally:
            os.unlink(path)

    def test_analyze_file_not_found(self) -> None:
        result = runner.invoke(app, ["analyze", "nonexistent.diag"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# optimize
# ---------------------------------------------------------------------------


class TestOptimize:
    def _write_svg(self, content: str) -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False, encoding="utf-8")
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_optimize_basic(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><g><circle cx="10" cy="10" r="5"/></g></svg>'
        path = self._write_svg(svg)
        try:
            result = runner.invoke(app, ["optimize", path])
            assert result.exit_code == 0
            assert "<svg" in result.stdout
            assert "circle" in result.stdout
        finally:
            os.unlink(path)

    def test_optimize_with_output(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><g><circle cx="10" cy="10" r="5"/></g></svg>'
        path = self._write_svg(svg)
        out_path = os.path.join(tempfile.mkdtemp(), "out.svg")
        try:
            result = runner.invoke(app, ["optimize", path, "--output", out_path])
            assert result.exit_code == 0
            output_content = Path(out_path).read_text(encoding="utf-8")
            assert "<svg" in output_content
        finally:
            os.unlink(path)
            if os.path.isfile(out_path):
                os.unlink(out_path)
                os.rmdir(os.path.dirname(out_path))

    def test_optimize_invalid(self) -> None:
        path = self._write_svg("not svg")
        try:
            result = runner.invoke(app, ["optimize", path])
            assert result.exit_code == 1
        finally:
            os.unlink(path)

    def test_optimize_file_not_found(self) -> None:
        result = runner.invoke(app, ["optimize", "nonexistent.svg"])
        assert result.exit_code != 0

    def test_optimize_verbose(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><!-- comment --><g/></svg>'
        path = self._write_svg(svg)
        try:
            result = runner.invoke(app, ["optimize", path, "--verbose"])
            assert result.exit_code == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------


class TestBatch:
    def _write_source(self, content: str, suffix: str = ".txt") -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_batch_no_files(self) -> None:
        result = runner.invoke(app, ["batch", os.devnull])
        assert result.exit_code == 0

    def test_batch_single_file(self) -> None:
        path = self._write_source("graph TD\n    A-->B")
        try:
            result = runner.invoke(app, ["batch", path])
            assert result.exit_code == 1
        finally:
            os.unlink(path)

    def test_batch_single_file_with_output(self) -> None:
        path = self._write_source("graph TD\n    A-->B")
        out_dir = tempfile.mkdtemp()
        try:
            result = runner.invoke(app, ["batch", path, "--output-dir", out_dir])
            assert result.exit_code == 1
        finally:
            os.unlink(path)
            os.rmdir(out_dir)

    def test_batch_multiple_files(self) -> None:
        p1 = self._write_source("graph TD\n    A-->B", ".mmd")
        p2 = self._write_source("@startuml\nA-->B\n@enduml", ".puml")
        try:
            result = runner.invoke(app, ["batch", p1, p2])
            assert result.exit_code == 1
        finally:
            os.unlink(p1)
            os.unlink(p2)

    def test_batch_directory_scan(self) -> None:
        d = tempfile.mkdtemp()
        try:
            f1 = Path(d) / "test1.mmd"
            f1.write_text("graph TD\n    A-->B", encoding="utf-8")
            result = runner.invoke(app, ["batch", d])
            assert result.exit_code == 1
        finally:
            import shutil

            shutil.rmtree(d)

    def test_batch_with_workers(self) -> None:
        path = self._write_source("graph TD\n    A-->B")
        try:
            result = runner.invoke(app, ["batch", path, "--workers", "2"])
            assert result.exit_code == 1
        finally:
            os.unlink(path)

    def test_batch_with_optimize(self) -> None:
        path = self._write_source("graph TD\n    A-->B")
        try:
            result = runner.invoke(app, ["batch", path, "--optimize"])
            assert result.exit_code == 1
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


class TestRender:
    def _write_source(self, content: str, suffix: str = ".txt") -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_render_file_not_found(self) -> None:
        result = runner.invoke(app, ["render", "nonexistent.diag"])
        assert result.exit_code != 0

    def test_render_unknown_language(self) -> None:
        path = self._write_source("not a diagram at all")
        try:
            result = runner.invoke(app, ["render", path])
            assert result.exit_code == 1
        finally:
            os.unlink(path)

    def test_render_with_explicit_language(self) -> None:
        path = self._write_source("not a diagram at all")
        try:
            result = runner.invoke(app, ["render", path, "--language", "unknown"])
            assert result.exit_code != 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# help
# ---------------------------------------------------------------------------


class TestHelp:
    def test_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.stdout
        assert "render" in result.stdout
        assert "detect" in result.stdout
        assert "analyze" in result.stdout
        assert "optimize" in result.stdout
        assert "batch" in result.stdout
        assert "watch" in result.stdout
        assert "plugins" in result.stdout
        assert "version" in result.stdout

    def test_render_help(self) -> None:
        result = runner.invoke(app, ["render", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.stdout or "-o" in result.stdout

    def test_batch_help(self) -> None:
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--recursive" in result.stdout or "-r" in result.stdout

    def test_watch_help(self) -> None:
        result = runner.invoke(app, ["watch", "--help"])
        assert result.exit_code == 0
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        plain = ansi_escape.sub("", result.stdout)
        assert "--debounce" in plain
