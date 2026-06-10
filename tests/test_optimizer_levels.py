"""Tests for optimisation levels (fast / balanced / maximum)."""

from __future__ import annotations

import pytest

from pidraw.optimizer.levels import (
    SUPPORTED_LEVELS,
    optimize_by_level,
)
from pidraw.optimizer.svg_optimizer import OptimizationResult


class TestOptimizeByLevel:
    MINIMAL_SVG = (
        "<svg xmlns=\"http://www.w3.org/2000/svg\"><g><circle cx='10' cy='10' r='5'/></g></svg>"
    )

    def test_fast_level(self) -> None:
        result = optimize_by_level(self.MINIMAL_SVG, level="fast")
        assert isinstance(result, OptimizationResult)
        assert result.svg

    def test_balanced_level(self) -> None:
        result = optimize_by_level(self.MINIMAL_SVG, level="balanced")
        assert isinstance(result, OptimizationResult)
        assert result.svg

    def test_maximum_level(self) -> None:
        result = optimize_by_level(self.MINIMAL_SVG, level="maximum")
        assert isinstance(result, OptimizationResult)
        assert result.svg

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown optimisation level"):
            optimize_by_level(self.MINIMAL_SVG, level="invalid")

    def test_supported_levels(self) -> None:
        assert "fast" in SUPPORTED_LEVELS
        assert "balanced" in SUPPORTED_LEVELS
        assert "maximum" in SUPPORTED_LEVELS

    def test_result_metrics(self) -> None:
        result = optimize_by_level(self.MINIMAL_SVG, level="balanced")
        assert result.original_size > 0
        assert result.passes_applied is not None
        assert len(result.passes_applied) > 0

    def test_fast_is_quicker(self) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            "<g><g><circle cx='10' cy='10' r='5'/></g></g></svg>"
        )
        fast = optimize_by_level(svg, level="fast")
        balanced = optimize_by_level(svg, level="balanced")
        assert len(fast.passes_applied) <= len(balanced.passes_applied)

    def test_preserves_svg_validity(self) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect width="100" height="50" fill="red"/></svg>'
        )
        result = optimize_by_level(svg, level="maximum")
        assert "<svg" in result.svg
        assert "rect" in result.svg
