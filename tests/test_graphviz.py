"""Tests for the Graphviz dot-based renderer."""
from __future__ import annotations

import subprocess
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from pidraw.engines.graphviz import GraphvizRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError
from pidraw.registry import clear_registry, register_renderer


@pytest.fixture
def mock_dot_path() -> Generator[None, None, None]:
    with patch("pidraw.engines.graphviz.shutil.which", return_value="/usr/bin/dot"):
        yield


@pytest.fixture
def renderer(mock_dot_path: Any) -> GraphvizRenderer:
    return GraphvizRenderer()


class TestConstruction:
    def test_find_dot_raises_when_missing(self) -> None:
        with patch("pidraw.engines.graphviz.shutil.which", return_value=None):
            with pytest.raises(EngineNotAvailableError):
                GraphvizRenderer()

    def test_explicit_path_used(self) -> None:
        r = GraphvizRenderer(dot_path="/custom/dot")
        assert r._dot_path == "/custom/dot"


class TestInputValidation:
    def test_empty_source_raises(self, renderer: GraphvizRenderer) -> None:
        with pytest.raises(RenderError, match="empty"):
            renderer.render("")

    def test_whitespace_only_raises(self, renderer: GraphvizRenderer) -> None:
        with pytest.raises(RenderError, match="empty"):
            renderer.render("   \n  \n  ")

    def test_null_bytes_raises(self, renderer: GraphvizRenderer) -> None:
        with pytest.raises(RenderError, match="null bytes"):
            renderer.render("digraph G { A -> B }\x00")

    def test_oversized_source_raises(self, renderer: GraphvizRenderer) -> None:
        big = "A" * (100 * 1024 + 1)
        with pytest.raises(RenderError, match="exceeds maximum size"):
            renderer.render(big)


class TestOutputValidation:
    def test_empty_output_raises(self, renderer: GraphvizRenderer) -> None:
        with patch.object(renderer, "_run_dot", return_value=""):
            with pytest.raises(RenderError, match="empty SVG"):
                renderer.render("digraph G { A -> B }")

    def test_non_svg_output_raises(self, renderer: GraphvizRenderer) -> None:
        with patch.object(renderer, "_run_dot", return_value="<html></html>"):
            with pytest.raises(RenderError, match="valid <svg>"):
                renderer.render("digraph G { A -> B }")

    def test_malformed_xml_raises(self, renderer: GraphvizRenderer) -> None:
        with patch.object(renderer, "_run_dot", return_value="<svg><broken></svg>"):
            with pytest.raises(RenderError, match="valid XML"):
                renderer.render("digraph G { A -> B }")


def _completed(
    returncode: int = 0, stderr: str = "",
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        args=["dot"], returncode=returncode,
        stdout=b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
        stderr=stderr.encode("utf-8"),
    )


class TestDotInvocation:
    def test_simple_directed_graph(self, renderer: GraphvizRenderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(0)
            result = renderer.render("digraph G { A -> B }")
            assert result == fake_svg

    def test_simple_undirected_graph(self, renderer: GraphvizRenderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(0)
            result = renderer.render("graph G { A -- B }")
            assert result == fake_svg

    def test_graph_with_clusters(self, renderer: GraphvizRenderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(0)
            result = renderer.render(
                "digraph G {\n  subgraph cluster_0 { A -> B }\n  subgraph cluster_1 { C -> D }\n}"
            )
            assert result == fake_svg

    def test_graph_with_styling(self, renderer: GraphvizRenderer) -> None:
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(0)
            result = renderer.render(
                "digraph G {\n  A [color=red]\n  B [style=filled, fillcolor=blue]\n  A -> B [label=hello]\n}"
            )
            assert result == fake_svg

    def test_dot_returns_nonzero(self, renderer: GraphvizRenderer) -> None:
        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(1, "Syntax error in DOT")
            with pytest.raises(RenderError, match="exited with code"):
                renderer.render("digraph G { INVALID }")

    def test_dot_times_out(self, renderer: GraphvizRenderer) -> None:
        _timeout = subprocess.TimeoutExpired(cmd="dot", timeout=30)
        with patch("pidraw.engines.graphviz.subprocess.run", side_effect=_timeout):
            with pytest.raises(RenderTimeoutError):
                renderer.render("digraph G { A -> B }")

    def test_dot_binary_missing(self, renderer: GraphvizRenderer) -> None:
        with patch("pidraw.engines.graphviz.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RenderError, match="not found"):
                renderer.render("digraph G { A -> B }")


class TestAutoRegistration:
    def test_graphviz_renderer_can_be_registered(self) -> None:
        clear_registry()
        register_renderer("graphviz", GraphvizRenderer(dot_path="/fake/dot"))
        from pidraw.registry import get_renderer
        r = get_renderer("graphviz")
        assert isinstance(r, GraphvizRenderer)

    def test_render_via_registry(self) -> None:
        clear_registry()
        r = GraphvizRenderer(dot_path="/fake/dot")
        register_renderer("graphviz", r)
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch.object(r, "_run_dot", return_value=fake_svg):
            from pidraw.renderer import render as public_render
            result = public_render("digraph { A -> B }")
            assert result.svg == fake_svg

    def test_detection_integration(self) -> None:
        clear_registry()
        r = GraphvizRenderer(dot_path="/fake/dot")
        register_renderer("graphviz", r)
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"
        with patch.object(r, "_run_dot", return_value=fake_svg):
            from pidraw.renderer import render as public_render
            for source in [
                "digraph G { A -> B }",
                "graph G { A -- B }",
                "strict digraph G { A -> B }",
                "strict graph G { A -- B }",
                "digraph { A -> B }",
            ]:
                result = public_render(source)
                assert result.svg == fake_svg, f"Failed for: {source}"
