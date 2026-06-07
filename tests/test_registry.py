"""Tests for the renderer plugin registry."""

from typing import Generator

import pytest

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RendererNotFoundError
from pidraw.registry import (
    clear_registry,
    get_renderer,
    list_renderers,
    register_renderer,
)


class FakeRenderer(BaseRenderer):
    def render(self, source: str) -> str:
        return f"<svg>{source}</svg>"


@pytest.fixture(autouse=True)
def reset_registry() -> Generator[None, None, None]:
    clear_registry()
    yield
    clear_registry()


class TestRegistry:
    def test_register_and_get(self) -> None:
        r: BaseRenderer = FakeRenderer()
        register_renderer("mermaid", r)
        assert get_renderer("mermaid") is r

    def test_get_case_insensitive(self) -> None:
        r: BaseRenderer = FakeRenderer()
        register_renderer("MERMAID", r)
        assert get_renderer("mermaid") is r

    def test_get_unknown(self) -> None:
        with pytest.raises(RendererNotFoundError):
            get_renderer("nonexistent")

    def test_register_twice_overwrites(self) -> None:
        r1: BaseRenderer = FakeRenderer()
        r2: BaseRenderer = FakeRenderer()
        register_renderer("test", r1)
        register_renderer("test", r2)
        assert get_renderer("test") is r2

    def test_list_renderers_empty(self) -> None:
        assert list_renderers() == {}

    def test_list_renderers(self) -> None:
        r: BaseRenderer = FakeRenderer()
        register_renderer("a", r)
        result = list_renderers()
        assert result == {"a": r}

    def test_list_renderers_is_copy(self) -> None:
        r: BaseRenderer = FakeRenderer()
        register_renderer("a", r)
        result = list_renderers()
        result["b"] = FakeRenderer()
        assert "b" not in list_renderers()

    def test_register_invalid_type(self) -> None:
        with pytest.raises(TypeError):
            register_renderer("test", "not-a-renderer")  # type: ignore[arg-type]

    def test_clear_registry(self) -> None:
        register_renderer("a", FakeRenderer())
        clear_registry()
        assert list_renderers() == {}

    def test_register_non_string_name(self) -> None:
        r: BaseRenderer = FakeRenderer()
        with pytest.raises((TypeError, AttributeError)):
            register_renderer(123, r)  # type: ignore[arg-type]

    def test_register_invalid_renderer_type(self) -> None:
        class NotRenderer:
            def render(self, source: str) -> str:
                return ""

        with pytest.raises(TypeError):
            register_renderer("test", NotRenderer())  # type: ignore[arg-type]

    def test_get_renderer_after_clear(self) -> None:
        r: BaseRenderer = FakeRenderer()
        register_renderer("x", r)
        clear_registry()
        with pytest.raises(RendererNotFoundError):
            get_renderer("x")
