"""Tests for the Mermaid CLI-based renderer."""

from __future__ import annotations

import subprocess
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from pidraw.engines.mermaid import MermaidRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError
from pidraw.registry import clear_registry, register_renderer

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def mock_mmdc_path() -> Generator[None, None, None]:
    with patch.object(MermaidRenderer, "_find_mmdc", return_value="/usr/bin/mmdc"):
        yield


@pytest.fixture
def renderer(mock_mmdc_path: Any) -> MermaidRenderer:
    return MermaidRenderer()


# ------------------------------------------------------------------
# Construction
# ------------------------------------------------------------------

class TestConstruction:
    def test_find_mmdc_raises_when_missing(self) -> None:
        with patch("pidraw.engines.mermaid.shutil.which", return_value=None):
            with pytest.raises(EngineNotAvailableError, match="mmdc"):
                MermaidRenderer._find_mmdc()

    def test_explicit_path_used(self) -> None:
        r = MermaidRenderer(mmdc_path="/custom/mmdc")
        assert r._mmdc_path == "/custom/mmdc"


# ------------------------------------------------------------------
# Input validation
# ------------------------------------------------------------------

class TestInputValidation:
    def test_empty_source_raises(self, renderer: MermaidRenderer) -> None:
        with pytest.raises(RenderError, match="empty"):
            renderer.render("")

    def test_whitespace_only_raises(self, renderer: MermaidRenderer) -> None:
        with pytest.raises(RenderError, match="empty"):
            renderer.render("   \n  \n  ")

    def test_null_bytes_raises(self, renderer: MermaidRenderer) -> None:
        with pytest.raises(RenderError, match="null bytes"):
            renderer.render("graph TD;\x00A-->B;")

    def test_oversized_source_raises(self, renderer: MermaidRenderer) -> None:
        big = "A" * (100 * 1024 + 1)
        with pytest.raises(RenderError, match="exceeds maximum size"):
            renderer.render(big)


# ------------------------------------------------------------------
# Output validation
# ------------------------------------------------------------------

class TestOutputValidation:
    def test_empty_svg_raises(self, renderer: MermaidRenderer) -> None:
        with patch.object(renderer, "_run_mmdc", return_value=""):
            with pytest.raises(RenderError, match="empty SVG"):
                renderer.render("graph TD; A-->B;")

    def test_non_svg_output_raises(self, renderer: MermaidRenderer) -> None:
        with patch.object(renderer, "_run_mmdc", return_value="<html></html>"):
            with pytest.raises(RenderError, match="valid <svg>"):
                renderer.render("graph TD; A-->B;")


# ------------------------------------------------------------------
# mmdc subprocess invocation
# ------------------------------------------------------------------

def _completed(
    returncode: int = 0, stderr: str = "",
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        args=["mmdc"], returncode=returncode,
        stdout=b"", stderr=stderr.encode("utf-8"),
    )


class TestMmdcInvocation:
    def test_successful_render(self, renderer: MermaidRenderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with (
            patch(
                "pidraw.engines.mermaid.tempfile.mkdtemp",
                return_value="/tmp/pidraw_test",
            ) as mock_mkdtemp,
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.mermaid.subprocess.run") as mock_run,
            patch("pidraw.engines.mermaid.os.path.isdir", return_value=True),
            patch("pidraw.engines.mermaid.shutil.rmtree") as mock_rmtree,
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg: MagicMock = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = fake_svg
            mock_open.side_effect = [
                MagicMock(),
                mock_file_svg,
            ]

            result = renderer.render("graph TD; A-->B;")

            assert result == fake_svg
            mock_mkdtemp.assert_called_once()
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "/usr/bin/mmdc"
            assert "--input" in cmd
            assert "--output" in cmd
            assert "--quiet" in cmd
            mock_rmtree.assert_called_once_with("/tmp/pidraw_test")

    def test_mmdc_returns_nonzero(self, renderer: MermaidRenderer) -> None:
        with (
            patch("pidraw.engines.mermaid.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open"),
            patch("pidraw.engines.mermaid.subprocess.run") as mock_run,
            patch("pidraw.engines.mermaid.shutil.rmtree"),
        ):
            mock_run.return_value = _completed(1, "Syntax error in diagram")

            with pytest.raises(RenderError, match="exited with code"):
                renderer.render("graph TD; INVALID;")

    def test_mmdc_times_out(self, renderer: MermaidRenderer) -> None:
        _timeout = subprocess.TimeoutExpired(cmd="mmdc", timeout=30)
        with (
            patch("pidraw.engines.mermaid.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open"),
            patch("pidraw.engines.mermaid.subprocess.run", side_effect=_timeout),
            patch("pidraw.engines.mermaid.shutil.rmtree"),
        ):
            with pytest.raises(RenderTimeoutError, match="timed out"):
                renderer.render("graph TD; A-->B;")

    def test_mmdc_binary_missing(self, renderer: MermaidRenderer) -> None:
        with (
            patch("pidraw.engines.mermaid.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open"),
            patch("pidraw.engines.mermaid.subprocess.run", side_effect=FileNotFoundError),
            patch("pidraw.engines.mermaid.shutil.rmtree"),
        ):
            with pytest.raises(RenderError, match="not found"):
                renderer.render("graph TD; A-->B;")

    def test_cleanup_on_failure(self, renderer: MermaidRenderer) -> None:
        _timeout = subprocess.TimeoutExpired(cmd="mmdc", timeout=30)
        with (
            patch("pidraw.engines.mermaid.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open"),
            patch("pidraw.engines.mermaid.subprocess.run", side_effect=_timeout),
            patch("pidraw.engines.mermaid.os.path.isdir", return_value=True),
            patch("pidraw.engines.mermaid.shutil.rmtree") as mock_rmtree,
        ):
            with pytest.raises(RenderTimeoutError):
                renderer.render("graph TD; A-->B;")
            mock_rmtree.assert_called_once_with("/tmp/pidraw_test")

    def test_cleanup_on_success(self, renderer: MermaidRenderer) -> None:
        with (
            patch("pidraw.engines.mermaid.tempfile.mkdtemp", return_value="/tmp/pidraw_test"),
            patch("builtins.open") as mock_open,
            patch("pidraw.engines.mermaid.subprocess.run") as mock_run,
            patch("pidraw.engines.mermaid.os.path.isdir", return_value=True),
            patch("pidraw.engines.mermaid.shutil.rmtree") as mock_rmtree,
        ):
            mock_run.return_value = _completed(0)
            mock_file_svg: MagicMock = MagicMock()
            mock_file_svg.__enter__.return_value.read.return_value = "<svg></svg>"
            mock_open.side_effect = [MagicMock(), mock_file_svg]

            renderer.render("graph TD; A-->B;")
            mock_rmtree.assert_called_once_with("/tmp/pidraw_test")


# ------------------------------------------------------------------
# Auto-registration
# ------------------------------------------------------------------

class TestAutoRegistration:
    def test_mermaid_renderer_can_be_registered(self) -> None:
        clear_registry()
        register_renderer("mermaid", MermaidRenderer(mmdc_path="/fake/mmdc"))
        from pidraw.registry import get_renderer
        r = get_renderer("mermaid")
        assert isinstance(r, MermaidRenderer)

    def test_render_via_registry(self) -> None:
        clear_registry()
        r = MermaidRenderer(mmdc_path="/fake/mmdc")
        register_renderer("mermaid", r)

        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch.object(r, "_run_mmdc", return_value=fake_svg):
            from pidraw.renderer import render as public_render
            result = public_render("graph TD; A-->B;")
            assert result.svg == fake_svg
