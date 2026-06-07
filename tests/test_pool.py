"""Tests for the parallel rendering pool."""

from __future__ import annotations

from pidraw.pool import RenderPool, RenderResult, summarize


class TestRenderPool:
    def test_create_pool_default(self) -> None:
        pool = RenderPool()
        assert pool.max_workers > 0

    def test_create_pool_with_workers(self) -> None:
        pool = RenderPool(max_workers=2)
        assert pool.max_workers == 2

    def test_create_pool_with_cache(self) -> None:
        from pidraw.cache import CacheManager
        cache = CacheManager()
        pool = RenderPool(cache=cache)
        assert pool is not None


class TestRenderResult:
    def test_result_defaults(self) -> None:
        r = RenderResult(svg="<svg/>")
        assert r.svg == "<svg/>"
        assert r.error is None
        assert not r.cached

    def test_result_with_error(self) -> None:
        r = RenderResult(svg="", error="error msg")
        assert r.error == "error msg"


class TestBatchRenderSummary:
    def test_empty_summary(self) -> None:
        s = summarize([])
        assert s.total == 0
        assert s.succeeded == 0
        assert s.failed == 0

    def test_summary_with_results(self) -> None:
        results = [
            RenderResult(svg="<svg>1</svg>", task_id=0),
            RenderResult(svg="", task_id=1, error="fail"),
        ]
        s = summarize(results)
        assert s.total == 2
        assert s.succeeded == 1
        assert s.failed == 1

    def test_summary_cached_count(self) -> None:
        results = [
            RenderResult(svg="<svg/>", cached=True),
            RenderResult(svg="<svg/>", cached=False),
            RenderResult(svg="<svg/>", cached=True),
        ]
        s = summarize(results)
        assert s.succeeded == 3
        assert s.cached == 2
