"""Tests for custom exception types and error propagation."""

from typing import Generator

import pytest

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import (
    EngineNotAvailableError,
    LanguageNotSupportedError,
    LayoutError,
    OptimizationError,
    ParseError,
    PiDrawError,
    PngConversionError,
    RenderError,
    RenderTimeoutError,
    RendererNotFoundError,
    RenderingError,
    UnsupportedLanguageError,
)
from pidraw.registry import clear_registry, register_renderer
from pidraw.renderer import render


class FailingRenderer(BaseRenderer):
    def render(self, source: str) -> str:
        raise RenderingError("render failed")


@pytest.fixture(autouse=True)
def auto_clear() -> Generator[None, None, None]:
    clear_registry()
    yield
    clear_registry()


class TestErrorHierarchy:
    def test_pidraw_error_is_base(self) -> None:
        assert issubclass(LanguageNotSupportedError, PiDrawError)
        assert issubclass(EngineNotAvailableError, PiDrawError)
        assert issubclass(RenderError, PiDrawError)
        assert issubclass(ParseError, RenderError)
        assert issubclass(LayoutError, RenderError)
        assert issubclass(RenderTimeoutError, PiDrawError)
        assert issubclass(OptimizationError, PiDrawError)
        assert issubclass(PngConversionError, PiDrawError)
        assert issubclass(UnsupportedLanguageError, LanguageNotSupportedError)
        assert issubclass(RendererNotFoundError, PiDrawError)
        assert issubclass(RenderingError, PiDrawError)

    def test_language_not_supported(self) -> None:
        exc = LanguageNotSupportedError("foo")
        assert str(exc) == "No renderer registered for language: 'foo'"
        assert exc.language == "foo"

    def test_engine_not_available(self) -> None:
        exc = EngineNotAvailableError("mmdc", setup_command="npm install -g @mermaid-js/mermaid-cli")
        assert "mmdc" in str(exc)
        assert "npm install" in str(exc)
        assert exc.engine == "mmdc"
        assert exc.setup_command == "npm install -g @mermaid-js/mermaid-cli"

    def test_render_error(self) -> None:
        exc = RenderError("mermaid", "syntax error", stderr="line 1: bad token")
        assert "mermaid" in str(exc)
        assert exc.language == "mermaid"
        assert exc.reason == "syntax error"
        assert exc.stderr == "line 1: bad token"

    def test_render_timeout(self) -> None:
        exc = RenderTimeoutError("plantuml", 60.0)
        assert "60" in str(exc)
        assert exc.language == "plantuml"
        assert exc.timeout == 60.0

    def test_parse_error(self) -> None:
        exc = ParseError("mermaid", "invalid token")
        assert isinstance(exc, RenderError)

    def test_layout_error(self) -> None:
        exc = LayoutError("graphviz", "cycle detected")
        assert isinstance(exc, RenderError)

    def test_optimization_error(self) -> None:
        exc = OptimizationError("svg malformed")
        assert "svg malformed" in str(exc)

    def test_png_conversion_error(self) -> None:
        exc = PngConversionError("no backends available")
        assert "no backends" in str(exc).lower()

    def test_renderer_not_found_is_pidraw_error(self) -> None:
        assert isinstance(RendererNotFoundError("x"), PiDrawError)

    def test_rendering_error_is_pidraw_error(self) -> None:
        assert isinstance(RenderingError("x"), PiDrawError)

    def test_unsupported_language_backward_compat(self) -> None:
        exc = UnsupportedLanguageError("test msg")
        assert str(exc) == "test msg"
        assert isinstance(exc, LanguageNotSupportedError)


class TestRenderErrors:
    def test_unsupported_language(self) -> None:
        with pytest.raises(UnsupportedLanguageError):
            render("some gibberish text")

    def test_renderer_not_found(self) -> None:
        with pytest.raises(RendererNotFoundError):
            render("graph TD\n    A-->B")

    def test_rendering_error_propagated(self) -> None:
        register_renderer("mermaid", FailingRenderer())
        with pytest.raises(RenderingError, match="render failed"):
            render("graph TD\n    A-->B")

    def test_no_renderer_for_detected_language(self) -> None:
        with pytest.raises(RendererNotFoundError):
            render("graph LR\n    A-->B")

    def test_empty_source(self) -> None:
        with pytest.raises(UnsupportedLanguageError):
            render("")

    def test_whitespace_source(self) -> None:
        with pytest.raises(UnsupportedLanguageError):
            render("   \n  ")
