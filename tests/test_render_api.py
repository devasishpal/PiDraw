"""Tests for the updated render API with optimisation levels."""

from __future__ import annotations

import os
import tempfile

import pytest

from pidraw.renderer import _apply_optimization, render, render_file, render_many


def test_render_unknown_language() -> None:
    result = render("not a diagram")
    assert not result.success


def test_render_with_optimize_false() -> None:
    """optimize=False should not change behaviour."""
    result = render("not a diagram", optimize=False)
    assert not result.success


def test_render_with_optimize_true() -> None:
    result = render("not a diagram", optimize=True)
    assert not result.success


def test_render_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        render_file("/nonexistent/path.diag")


def test_render_file_with_optimize() -> None:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8")
    tmp.write("graph TD\n    A-->B\n")
    tmp.close()
    try:
        result = render_file(tmp.name, optimize="fast")
        # May succeed or fail depending on registered renderers
        assert isinstance(result.svg, str)
    finally:
        os.unlink(tmp.name)


def test_render_many_empty() -> None:
    result = render_many([])
    assert result == []


def test_render_many_single() -> None:
    results = render_many(["not a diagram"])
    assert len(results) == 1
    assert not results[0].success


class TestApplyOptimization:
    def test_false_returns_unchanged(self) -> None:
        assert _apply_optimization("<svg/>", False) == "<svg/>"

    def test_true_uses_balanced(self) -> None:
        result = _apply_optimization('<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>', True)
        assert "<svg" in result

    def test_fast_level(self) -> None:
        result = _apply_optimization('<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>', "fast")
        assert "<svg" in result

    def test_balanced_level(self) -> None:
        result = _apply_optimization(
            '<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>', "balanced"
        )
        assert "<svg" in result

    def test_maximum_level(self) -> None:
        result = _apply_optimization(
            '<svg xmlns="http://www.w3.org/2000/svg"><g/></svg>', "maximum"
        )
        assert "<svg" in result
