"""Tests for the Renderer class."""

from __future__ import annotations

from typing import Any, Generator
from unittest.mock import patch

import pytest

from pidraw.engines.mermaid import MermaidRenderer
from pidraw.registry import clear_registry, register_renderer
from pidraw.renderer_class import Renderer


@pytest.fixture(autouse=True)
def auto_clear() -> Generator[None, None, None]:
    clear_registry()
    yield
    clear_registry()


class TestRendererConstruction:
    def test_default_params(self) -> None:
        r = Renderer()
        assert r._theme == "light"
        assert r._optimize == "balanced"
        assert r._timeout == 30.0

    def test_custom_params(self) -> None:
        r = Renderer(
            theme="dark",
            optimize="maximum",
            timeout=60,
            cache_dir="/tmp/cache",
            png_scale=2.0,
            png_width=800,
        )
        assert r._theme == "dark"
        assert r._optimize == "maximum"
        assert r._timeout == 60
        assert r._cache_dir == "/tmp/cache"
        assert r._png_scale == 2.0
        assert r._png_width == 800


class TestRendererRender:
    SVG_OUTPUT = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

    def test_render_svg(self) -> None:
        r = Renderer()
        mermaid = MermaidRenderer(mmdc_path="/fake/mmdc")
        register_renderer("mermaid", mermaid)

        with patch.object(mermaid, "_run_mmdc", return_value=self.SVG_OUTPUT):
            result = r.render("graph TD; A-->B;")
            assert "<svg" in result.svg

    def test_render_with_explicit_language(self) -> None:
        r = Renderer()
        mermaid = MermaidRenderer(mmdc_path="/fake/mmdc")
        register_renderer("mermaid", mermaid)

        with patch.object(mermaid, "_run_mmdc", return_value=self.SVG_OUTPUT):
            result = r.render("graph TD; A-->B;", language="mermaid")
            assert "<svg" in result.svg

    def test_render_file(self, tmp_path: Any) -> None:
        r = Renderer()
        mermaid = MermaidRenderer(mmdc_path="/fake/mmdc")
        register_renderer("mermaid", mermaid)

        d = tmp_path / "test"
        d.mkdir()
        f = d / "diagram.mmd"
        f.write_text("graph TD; A-->B;", encoding="utf-8")

        with patch.object(mermaid, "_run_mmdc", return_value=self.SVG_OUTPUT):
            result = r.render_file(str(f))
            assert "<svg" in result.svg

    def test_render_unknown_language(self) -> None:
        r = Renderer()
        with pytest.raises(Exception):
            r.render("some random text")


class TestRendererAvailableEngines:
    def test_returns_dict(self) -> None:
        mermaid = MermaidRenderer(mmdc_path="/fake/mmdc")
        register_renderer("mermaid", mermaid)
        r = Renderer()
        engines = r.available_engines()
        assert isinstance(engines, dict)

    def test_contains_mermaid(self) -> None:
        mermaid = MermaidRenderer(mmdc_path="/fake/mmdc")
        register_renderer("mermaid", mermaid)
        r = Renderer()
        engines = r.available_engines()
        assert "mermaid" in engines
