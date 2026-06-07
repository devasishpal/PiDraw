"""Tests for custom exception types and error propagation."""

from typing import Generator

import pytest

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import (
    PiDrawError,
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
        assert issubclass(UnsupportedLanguageError, PiDrawError)
        assert issubclass(RendererNotFoundError, PiDrawError)
        assert issubclass(RenderingError, PiDrawError)

    def test_unsupported_language_is_pidraw_error(self) -> None:
        assert isinstance(UnsupportedLanguageError("x"), PiDrawError)

    def test_renderer_not_found_is_pidraw_error(self) -> None:
        assert isinstance(RendererNotFoundError("x"), PiDrawError)

    def test_rendering_error_is_pidraw_error(self) -> None:
        assert isinstance(RenderingError("x"), PiDrawError)

    def test_exception_message(self) -> None:
        exc = UnsupportedLanguageError("test msg")
        assert str(exc) == "test msg"


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
