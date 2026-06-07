"""Tests for error recovery."""

from __future__ import annotations

import pytest

from pidraw.exceptions import PiDrawError, RecoverableRenderingError
from pidraw.recovery import render_with_retry, safe_render


class _AlwaysFails:
    def __call__(self, source: str, language: str | None = None) -> str:
        raise PiDrawError("always fails")


class _AlwaysSucceeds:
    def __call__(self, source: str, language: str | None = None) -> str:
        return "<svg/>"


class _FailsThenSucceeds:
    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, source: str, language: str | None = None) -> str:
        self.call_count += 1
        if self.call_count <= 1:
            raise PiDrawError("transient error")
        return "<svg/>"


_always_fails = _AlwaysFails()
_always_succeeds = _AlwaysSucceeds()


class TestRenderWithRetry:
    def test_success_first_try(self) -> None:
        result = render_with_retry("src", render_func=_always_succeeds)
        assert result == "<svg/>"

    def test_retry_then_success(self) -> None:
        fts = _FailsThenSucceeds()
        result = render_with_retry("src", render_func=fts, max_retries=3)
        assert result == "<svg/>"

    def test_all_retries_fail_no_fallback(self) -> None:
        with pytest.raises(RecoverableRenderingError):
            render_with_retry("src", render_func=_always_fails, max_retries=2)

    def test_fallback_used(self) -> None:
        result = render_with_retry(
            "src",
            render_func=_always_fails,
            max_retries=1,
            fallback_renderer=_always_succeeds,
        )
        assert result == "<svg/>"

    def test_fallback_also_fails(self) -> None:
        with pytest.raises(RecoverableRenderingError):
            render_with_retry(
                "src",
                render_func=_always_fails,
                max_retries=1,
                fallback_renderer=_always_fails,
            )


class TestSafeRender:
    def test_success(self) -> None:
        result = safe_render("src", render_func=_always_succeeds)
        assert result == "<svg/>"

    def test_failure_returns_error_svg(self) -> None:
        result = safe_render("src", render_func=_always_fails)
        assert "<svg" in result
        assert "Rendering Error" in result

    def test_failure_returns_custom_fallback(self) -> None:
        result = safe_render("src", render_func=_always_fails, fallback_svg="<svg fallback/>")
        assert result == "<svg fallback/>"
