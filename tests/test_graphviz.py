"""Tests for the Graphviz dot renderer."""

from __future__ import annotations

import subprocess
from typing import Any, Generator
from unittest.mock import patch

import pytest

from pidraw.engines.graphviz import GraphvizRenderer
from pidraw.exceptions import RenderingError
from pidraw.registry import clear_registry, register_renderer

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def mock_dot_path() -> Generator[None, None, None]:
    with patch.object(GraphvizRenderer, "_find_dot", return_value="/usr/bin/dot"):
        yield


@pytest.fixture
def renderer(mock_dot_path: Any) -> GraphvizRenderer:
    return GraphvizRenderer()


# ------------------------------------------------------------------
# Construction
# ------------------------------------------------------------------

class TestConstruction:
    def test_find_dot_raises_when_missing(self) -> None:
        with patch("pidraw.engines.graphviz.shutil.which", return_value=None):
            with pytest.raises(RenderingError, match="not installed"):
                GraphvizRenderer()

    def test_explicit_path_used(self) -> None:
        r = GraphvizRenderer(dot_path="/custom/dot")
        assert r._dot_path == "/custom/dot"


# ------------------------------------------------------------------
# Input validation
# ------------------------------------------------------------------

class TestInputValidation:
    def test_empty_source_raises(self, renderer: GraphvizRenderer) -> None:
        with pytest.raises(RenderingError, match="empty"):
            renderer.render("")

    def test_whitespace_only_raises(self, renderer: GraphvizRenderer) -> None:
        with pytest.raises(RenderingError, match="empty"):
            renderer.render("   \n  \n  ")

    def test_null_bytes_raises(self, renderer: GraphvizRenderer) -> None:
        with pytest.raises(RenderingError, match="null bytes"):
            renderer.render("digraph {\x00 A -> B }")

    def test_oversized_source_raises(self, renderer: GraphvizRenderer) -> None:
        big = "A" * (100 * 1024 + 1)
        with pytest.raises(RenderingError, match="exceeds maximum size"):
            renderer.render(big)


# ------------------------------------------------------------------
# Output validation
# ------------------------------------------------------------------

class TestOutputValidation:
    def test_empty_output_raises(self, renderer: GraphvizRenderer) -> None:
        with patch.object(renderer, "_run_dot", return_value=""):
            with pytest.raises(RenderingError, match="empty SVG"):
                renderer.render("digraph { A -> B }")

    def test_non_svg_output_raises(self, renderer: GraphvizRenderer) -> None:
        with patch.object(renderer, "_run_dot", return_value="<html></html>"):
            with pytest.raises(RenderingError, match="valid <svg>"):
                renderer.render("digraph { A -> B }")

    def test_malformed_xml_raises(self, renderer: GraphvizRenderer) -> None:
        bad_svg = "<svg><unclosed></svg>"
        with patch.object(renderer, "_run_dot", return_value=bad_svg):
            with pytest.raises(RenderingError, match="valid XML"):
                renderer.render("digraph { A -> B }")


# ------------------------------------------------------------------
# dot subprocess invocation
# ------------------------------------------------------------------

def _completed(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        args=["dot", "-Tsvg"],
        returncode=returncode,
        stdout=stdout.encode("utf-8"),
        stderr=stderr.encode("utf-8"),
    )


class TestDotInvocation:
    def test_simple_directed_graph(self, renderer: GraphvizRenderer) -> None:
        """digraph { A -> B }"""
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(0, stdout=fake_svg)

            result = renderer.render("digraph { A -> B }")

            assert result == fake_svg
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd == ["/usr/bin/dot", "-Tsvg"]
            assert mock_run.call_args[1]["input"] == b"digraph { A -> B }"

    def test_simple_undirected_graph(self, renderer: GraphvizRenderer) -> None:
        """graph { A -- B }"""
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(0, stdout=fake_svg)

            result = renderer.render("graph { A -- B }")

            assert result == fake_svg
            mock_run.assert_called_once()

    def test_graph_with_clusters(self, renderer: GraphvizRenderer) -> None:
        """digraph { subgraph cluster_0 { A -> B } }"""
        dot_source = (
            "digraph G {\n"
            "    subgraph cluster_0 {\n"
            "        A -> B;\n"
            "    }\n"
            "}"
        )
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(0, stdout=fake_svg)

            result = renderer.render(dot_source)
            assert result == fake_svg

    def test_graph_with_styling(self, renderer: GraphvizRenderer) -> None:
        """digraph { node [style=filled]; A [fillcolor=red]; A -> B }"""
        dot_source = (
            "digraph {\n"
            "    node [style=filled];\n"
            "    A [fillcolor=red];\n"
            "    A -> B;\n"
            "}"
        )
        fake_svg = "<svg xmlns='http://www.w3.org/2000/svg'></svg>"

        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(0, stdout=fake_svg)

            result = renderer.render(dot_source)
            assert result == fake_svg

    def test_dot_returns_nonzero(self, renderer: GraphvizRenderer) -> None:
        with patch("pidraw.engines.graphviz.subprocess.run") as mock_run:
            mock_run.return_value = _completed(1, stderr="syntax error")

            with pytest.raises(RenderingError, match="syntax error"):
                renderer.render("digraph { invalid syntax }")

    def test_dot_times_out(self, renderer: GraphvizRenderer) -> None:
        _timeout = subprocess.TimeoutExpired(cmd="dot", timeout=30)
        with patch("pidraw.engines.graphviz.subprocess.run", side_effect=_timeout):
            with pytest.raises(RenderingError, match="timed out"):
                renderer.render("digraph { A -> B }")

    def test_dot_binary_missing(self, renderer: GraphvizRenderer) -> None:
        with patch("pidraw.engines.graphviz.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RenderingError, match="not found"):
                renderer.render("digraph { A -> B }")


# ------------------------------------------------------------------
# Auto-registration
# ------------------------------------------------------------------

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
            assert result == fake_svg

    def test_detection_integration(self) -> None:
        """End-to-end: digraph source is detected and rendered."""
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
                assert result == fake_svg, f"Failed for: {source}"
