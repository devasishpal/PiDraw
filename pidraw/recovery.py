"""Error recovery — retry, fallback, and partial recovery for rendering."""

from __future__ import annotations

import time
from typing import Callable

from pidraw.exceptions import (
    PiDrawError,
    RecoverableRenderingError,
)

__all__ = ["RecoverableRenderingError", "render_with_retry", "safe_render"]


def render_with_retry(
    source: str,
    language: str | None = None,
    *,
    render_func: Callable[..., str | bytes],
    max_retries: int = 2,
    retry_delay: float = 0.5,
    backoff: float = 2.0,
    fallback_renderer: Callable[..., str | bytes] | None = None,
) -> str | bytes:
    """Render a diagram with automatic retry and fallback.

    Parameters
    ----------
    source :
        Diagram source code.
    language :
        Explicit language.
    render_func :
        Primary render function.
    max_retries :
        Maximum number of retry attempts.
    retry_delay :
        Initial delay between retries (seconds).
    backoff :
        Multiplier for *retry_delay* after each attempt.
    fallback_renderer :
        Optional fallback renderer used if all retries fail.

    Returns
    -------
    str
        The rendered SVG (possibly from the fallback).

    Raises
    ------
    RecoverableRenderingError
        If all retries and the fallback fail.

    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return render_func(source, language=language)
        except PiDrawError as exc:
            last_exception = exc
            if attempt < max_retries:
                delay = retry_delay * (backoff**attempt)
                time.sleep(delay)

    # Fallback
    if fallback_renderer is not None:
        try:
            return fallback_renderer(source, language=language)
        except Exception as exc:
            last_exception = exc

    raise RecoverableRenderingError(
        f"Rendering failed after {max_retries} retries"
    ) from last_exception


def safe_render(
    source: str,
    language: str | None = None,
    *,
    render_func: Callable[..., str | bytes] | None = None,
    fallback_svg: str | None = None,
) -> str | bytes:
    """Render a diagram, returning a fallback SVG on failure instead of raising.

    Parameters
    ----------
    source :
        Diagram source code.
    language :
        Explicit language.
    render_func :
        Render function (defaults to ``pidraw.renderer.render``).
    fallback_svg :
        SVG to return on failure.  If ``None``, returns a minimal error SVG.

    Returns
    -------
    str
        The rendered SVG or the fallback.

    """
    if render_func is None:
        from pidraw.renderer import render as _render

        render_func = _render

    try:
        return render_func(source, language=language)
    except Exception as exc:
        if fallback_svg is not None:
            return fallback_svg
        return _error_svg(str(exc) if str(exc) else "Rendering failed")


def _error_svg(message: str) -> str:
    """Return a minimal SVG indicating a rendering error."""
    safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100">'
        f'<rect width="100%" height="100%" fill="#fff5f5" stroke="#e00" stroke-width="2"/>'
        f'<text x="20" y="40" font-family="monospace" font-size="14" fill="#c00">'
        f"Rendering Error: {safe_msg}"
        f"</text>"
        f"</svg>"
    )
