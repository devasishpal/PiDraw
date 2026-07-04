"""Tests for async rendering API."""

from __future__ import annotations

import asyncio
from typing import Any, Generator

import pytest

from pidraw.async_api import arender, arender_file
from pidraw.engines.mermaid import MermaidRenderer
from pidraw.registry import clear_registry, register_renderer


@pytest.fixture(autouse=True)
def auto_clear() -> Generator[None, None, None]:
    clear_registry()
    yield
    clear_registry()


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_arender_basic() -> None:
    r = MermaidRenderer(mmdc_path="/fake/mmdc")
    register_renderer("mermaid", r)

    result = _run(arender("graph TD; A-->B;"))
    assert "<svg" in result.svg
    assert "A" in result.svg
    assert "B" in result.svg
    assert result.language == "mermaid"


def test_arender_with_language() -> None:
    r = MermaidRenderer(mmdc_path="/fake/mmdc")
    register_renderer("mermaid", r)

    result = _run(arender("graph TD; A-->B;", language="mermaid"))
    assert "<svg" in result.svg
    assert "A" in result.svg
    assert "B" in result.svg


def test_arender_unknown_language() -> None:
    result = _run(arender("some random text"))
    assert not result.success


def test_arender_file(tmp_path: Any) -> None:
    r = MermaidRenderer(mmdc_path="/fake/mmdc")
    register_renderer("mermaid", r)

    d = tmp_path / "test"
    d.mkdir()
    f = d / "diagram.mmd"
    f.write_text("graph TD; A-->B;", encoding="utf-8")

    result = _run(arender_file(str(f)))
    assert "<svg" in result.svg
    assert "A" in result.svg
    assert "B" in result.svg


def test_arender_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        _run(arender_file("/nonexistent/file.mmd"))
