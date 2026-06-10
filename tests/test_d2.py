"""Tests for the D2 renderer."""
from __future__ import annotations

import subprocess
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from pidraw.engines.d2 import D2Renderer, find_d2
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError
from pidraw.registry import clear_registry, register_renderer


@pytest.fixture
def mock_d2_path() -> Generator[None, None, None]:
    with patch("pidraw.engines.d2.shutil.which", return_value="/usr/bin/d2"):
        yield


@pytest.fixture
def renderer(mock_d2_path: Any) -> D2Renderer:
    return D2Renderer()


class TestFindD2:
    def test_find_d2_missing(self) -> None:
        with patch("pidraw.engines.d2.shutil.which", return_value=None):
            with pytest.raises(EngineNotAvailableError):
                find_d2()

    def test_find_d2_found(self) -> None:
        with patch("pidraw.engines.d2.shutil.which", return_value="/usr/bin/d2"):
            assert find_d2() == "/usr/bin/d2"


class TestConstruction:
    def test_find_d2_raises_when_missing(self) -> None:
        with patch("pidraw.engines.d2.shutil.which", return_value=None):
            r = D2Renderer()
            assert r._d2_path is None  # falls back to native

    def test_explicit_path_used(self) -> None:
        r = D2Renderer(d2_path="/custom/d2")
        assert r._d2_path == "/custom/d2"


class TestInputValidation:
    def test_empty_source_raises(self, renderer: D2Renderer) -> None:
        with pytest.raises(RenderError, match="empty"):
            renderer.render("")

    def test_whitespace_only_raises(self, renderer: D2Renderer) -> None:
        with pytest.raises(RenderError, match="empty"):
            renderer.render("   \n  \n  ")

    def test_null_bytes_raises(self, renderer: D2Renderer) -> None:
        with pytest.raises(RenderError, match="null bytes"):
            renderer.render("x -> y\x00")

    def test_oversized_source_raises(self, renderer: D2Renderer) -> None:
        big = "A" * (100 * 1024 + 1)
        with pytest.raises(RenderError, match="exceeds maximum size"):
            renderer.render(big)


class TestOutputValidation:
    def test_empty_output_raises(self, renderer: D2Renderer) -> None:
        with patch.object(renderer, "_run_d2", return_value=""):
            with pytest.raises(RenderError, match="empty SVG"):
                renderer.render("x -> y")

    def test_non_svg_output_raises(self, renderer: D2Renderer) -> None:
        with patch.object(renderer, "_run_d2", return_value="<html></html>"):
            with pytest.raises(RenderError, match="valid <svg>"):
                renderer.render("x -> y")

    def test_malformed_xml_raises(self, renderer: D2Renderer) -> None:
        with patch.object(renderer, "_run_d2", return_value="<svg><broken></svg>"):
            with pytest.raises(RenderError, match="valid XML"):
                renderer.render("x -> y")


def _completed(
    returncode: int = 0, stderr: str = "",
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        args=["d2"], returncode=returncode,
        stdout=b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
        stderr=stderr.encode("utf-8"),
    )


class TestD2Invocation:
    def test_simple_diagram(self, renderer: D2Renderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with (
            patch("pidraw.engines.d2.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.d2.subprocess.run") as mock_run,
            patch("pidraw.engines.d2.os.path.isdir", return_value=True),
            patch("pidraw.engines.d2.shutil.rmtree") as mock_rmtree,
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg: MagicMock = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]
            result = renderer.render("x -> y")
            assert result == fake_svg
            mock_rmtree.assert_called_once_with("/tmp/pidraw_test")

    def test_nested_container(self, renderer: D2Renderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with (
            patch("pidraw.engines.d2.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.d2.subprocess.run") as mock_run,
            patch("pidraw.engines.d2.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg: MagicMock = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]
            result = renderer.render("mycontainer: {\n    a -> b\n}")
            assert result == fake_svg

    def test_with_style(self, renderer: D2Renderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with (
            patch("pidraw.engines.d2.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.d2.subprocess.run") as mock_run,
            patch("pidraw.engines.d2.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg: MagicMock = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]
            result = renderer.render("style: {\n    stroke: red\n}")
            assert result == fake_svg

    def test_d2_returns_nonzero(self, renderer: D2Renderer) -> None:
        with (
            patch("pidraw.engines.d2.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open"),
            patch("pidraw.engines.d2.subprocess.run") as mock_run,
            patch("pidraw.engines.d2.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(1, "Syntax error")
            with pytest.raises(RenderError, match="exited with code"):
                renderer.render("x -> y")

    def test_d2_times_out(self, renderer: D2Renderer) -> None:
        _timeout = subprocess.TimeoutExpired(cmd="d2", timeout=30)
        with (
            patch("pidraw.engines.d2.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open"),
            patch("pidraw.engines.d2.subprocess.run", side_effect=_timeout),
            patch("pidraw.engines.d2.shutil.rmtree"),
        ):
            with pytest.raises(RenderTimeoutError):
                renderer.render("x -> y")

    def test_d2_binary_missing(self, renderer: D2Renderer) -> None:
        with (
            patch("pidraw.engines.d2.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open"),
            patch("pidraw.engines.d2.subprocess.run", side_effect=FileNotFoundError),
            patch("pidraw.engines.d2.shutil.rmtree"),
        ):
            with pytest.raises(RenderError, match="not found"):
                renderer.render("x -> y")

    def test_cleanup_on_failure(self, renderer: D2Renderer) -> None:
        _timeout = subprocess.TimeoutExpired(cmd="d2", timeout=30)
        with (
            patch("pidraw.engines.d2.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open"),
            patch("pidraw.engines.d2.subprocess.run", side_effect=_timeout),
            patch("pidraw.engines.d2.os.path.isdir", return_value=True),
            patch("pidraw.engines.d2.shutil.rmtree") as mock_rmtree,
        ):
            with pytest.raises(RenderTimeoutError):
                renderer.render("x -> y")
            mock_rmtree.assert_called_once_with("/tmp/pidraw_test")

    def test_cleanup_on_success(self, renderer: D2Renderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with (
            patch("pidraw.engines.d2.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.d2.subprocess.run") as mock_run,
            patch("pidraw.engines.d2.os.path.isdir", return_value=True),
            patch("pidraw.engines.d2.shutil.rmtree") as mock_rmtree,
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg: MagicMock = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [MagicMock(), mock_file_svg]
            renderer.render("x -> y")
            mock_rmtree.assert_called_once_with("/tmp/pidraw_test")


class TestAutoRegistration:
    def test_d2_renderer_can_be_registered(self) -> None:
        clear_registry()
        register_renderer("d2", D2Renderer(d2_path="/fake/d2"))
        from pidraw.registry import get_renderer
        r = get_renderer("d2")
        assert isinstance(r, D2Renderer)

    def test_render_via_registry(self) -> None:
        clear_registry()
        r = D2Renderer(d2_path="/fake/d2")
        register_renderer("d2", r)
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch.object(r, "_run_d2", return_value=fake_svg):
            from pidraw.renderer import render as public_render
            result = public_render("x -> y")
            assert result.svg == fake_svg

    def test_detection_integration(self) -> None:
        clear_registry()
        r = D2Renderer(d2_path="/fake/d2")
        register_renderer("d2", r)
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch.object(r, "_run_d2", return_value=fake_svg):
            from pidraw.renderer import render as public_render
            for source in [
                "x -> y",
                "a <-> b",
                "direction: right\nx -> y",
                "mycontainer: {\n    a -> b\n}",
                "style: {\n    stroke: red\n}",
            ]:
                result = public_render(source)
                assert result.svg == fake_svg, f"Failed for: {source[:40]}..."
