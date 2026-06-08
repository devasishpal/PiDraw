"""Public render API — detect, select, and render diagram source to SVG.

Supports automatic language detection, manual override, optimisation
levels, file-based input, and batch rendering.
"""

from __future__ import annotations

import os
import time
import warnings
from typing import Iterable

from pidraw.detector import detect
from pidraw.exceptions import LanguageNotSupportedError, UnsupportedLanguageError, RendererNotFoundError
from pidraw.registry import get_renderer
from pidraw.result import RenderResult

_RECOGNISED_LEVELS = frozenset({"fast", "balanced", "maximum"})
_RECOGNISED_FORMATS = frozenset({"svg", "png"})


def render(
    source: str,
    language: str | None = None,
    *,
    format: str = "svg",
    optimize: str | bool = False,
    quality: bool = False,
    scale: float = 1.0,
    transparent: bool = True,
    timeout: float = 30.0,
    theme: str = "light",
) -> RenderResult:
    """Render a diagram source string into SVG or PNG.

    This is the primary entry point for the PiDraw library.  When
    *language* is ``None`` the diagram language is auto-detected;
    otherwise the specified language is used directly.

    Parameters
    ----------
    source : str
        The diagram source code.
    language : str | None
        Explicit language identifier (e.g. ``"mermaid"``).  When
        ``None`` (default) the language is auto-detected.
    format : str
        Output format.  ``"svg"`` (default) returns a RenderResult with SVG.
        ``"png"`` returns a RenderResult with both SVG and PNG.
    optimize : str or bool
        Optimisation level.  ``False`` (default) = no optimisation.
        ``True`` = ``"balanced"``.  String values: ``"fast"``,
        ``"balanced"``, ``"maximum"``.
    quality : bool
        If ``True``, run the quality enhancement pipeline on output.
    scale : float
        Scale factor for PNG output (default 1.0). Ignored for SVG.
    transparent : bool
        If True (default), render PNG with transparent background.
        Ignored for SVG output.
    timeout : float
        Maximum render time in seconds.
    theme : str
        Theme name to apply to the rendered diagram.

    Returns
    -------
    RenderResult
        The rendered output container with `.svg` and optionally `.png`.

    Raises
    ------
    LanguageNotSupportedError
        If the language cannot be detected or is not supported.
    RendererNotFoundError
        If the detected/explicit language has no registered renderer.
    RenderError
        If the rendering process itself fails.
    """
    start = time.perf_counter()
    fmt = format.lower()
    if fmt not in _RECOGNISED_FORMATS:
        raise ValueError(f"Unsupported format: {format!r}. Use 'svg' or 'png'.")

    if language:
        lang = language.lower()
    else:
        lang = detect(source)

    if lang == "unknown":
        raise UnsupportedLanguageError(
            "Unable to detect diagram language from source"
        )

    renderer = get_renderer(lang)
    svg = renderer.render(source)

    if optimize:
        svg = _apply_optimization(svg, optimize)

    if quality:
        from pidraw.quality import QualityProcessor

        svg = QualityProcessor().process(svg)

    # Build the result
    elapsed = (time.perf_counter() - start) * 1000.0
    result = RenderResult(
        svg=svg,
        language=lang,
        engine_used=renderer.name if hasattr(renderer, "name") else "",
        render_time_ms=elapsed,
    )

    if fmt == "png":
        from pidraw.backend.png import svg_to_png

        png_bytes = svg_to_png(svg, scale=scale, transparent=transparent)
        result.png = png_bytes

    return result


def render_svg(
    source: str,
    language: str | None = None,
    *,
    optimize: str | bool = False,
    quality: bool = False,
    **kwargs: object,
) -> str:
    """Render a diagram source and return just the SVG string.

    This is a convenience wrapper around :func:`render` that returns
    a plain string for backwards compatibility.

    .. deprecated::
        Use :func:`render` instead and access the ``.svg`` attribute
        of the returned :class:`RenderResult`.
    """
    warnings.warn(
        "render_svg() is deprecated. Use render(source, ...).svg instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    result = render(
        source,
        language=language,
        optimize=optimize,
        quality=quality,
        **kwargs,  # type: ignore[arg-type]
    )
    return result.svg


def render_file(
    path: str,
    language: str | None = None,
    *,
    format: str = "svg",
    optimize: str | bool = False,
    quality: bool = False,
    scale: float = 1.0,
    transparent: bool = True,
    timeout: float = 30.0,
    theme: str = "light",
) -> RenderResult:
    """Read a diagram file and render it to SVG or PNG.

    Parameters
    ----------
    path : str
        Path to the diagram source file.
    language : str | None
        Explicit language identifier.  Auto-detected when ``None``.
    format : str
        Output format.  ``"svg"`` (default) or ``"png"``.
    optimize : str or bool
        Optimisation level (see :func:`render`).
    quality : bool
        If ``True``, run quality enhancement pipeline.
    scale : float
        Scale factor for PNG output (default 1.0). Ignored for SVG.
    timeout : float
        Maximum render time in seconds.
    theme : str
        Theme name to apply.

    Returns
    -------
    RenderResult
        The rendered output.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    LanguageNotSupportedError
        If the language cannot be detected.
    RendererNotFoundError
        If no renderer is registered for the language.
    RenderError
        If the rendering process fails.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Diagram file not found: {path}")

    with open(path, "r", encoding="utf-8-sig") as f:
        source = f.read().lstrip("\ufeff")

    return render(
        source,
        language=language,
        format=format,
        optimize=optimize,
        quality=quality,
        scale=scale,
        transparent=transparent,
        timeout=timeout,
        theme=theme,
    )


def render_many(
    sources: Iterable[str],
    language: str | None = None,
    *,
    format: str = "svg",
    max_workers: int | None = None,
    optimize: str | bool = False,
    quality: bool = False,
    scale: float = 1.0,
    transparent: bool = True,
    timeout: float = 30.0,
    theme: str = "light",
) -> list[RenderResult]:
    """Render multiple diagram sources in parallel.

    Parameters
    ----------
    sources :
        Iterable of diagram source strings.
    language :
        Explicit language override for all sources.
    format :
        Output format.  ``"svg"`` (default) or ``"png"``.
    max_workers :
        Maximum parallel workers (default = CPU count).
    optimize :
        Optimisation level (see :func:`render`).
    quality :
        If ``True``, run quality enhancement.
    scale :
        Scale factor for PNG output (default 1.0). Ignored for SVG.
    timeout :
        Maximum render time in seconds per source.
    theme :
        Theme name to apply.

    Returns
    -------
    list[RenderResult]
        Rendered outputs, one per input in the same order.
    """
    from pidraw.pool import RenderPool

    pool = RenderPool(max_workers=max_workers)
    results = pool.render_many(sources, language=language, show_progress=False)

    outputs: list[RenderResult] = []
    for r in results:
        if r.error:
            raise LanguageNotSupportedError(str(r.error))
        svg = r.svg
        if optimize:
            svg = _apply_optimization(svg, optimize)
        if quality:
            from pidraw.quality import QualityProcessor

            svg = QualityProcessor().process(svg)

        elapsed = 0.0
        result = RenderResult(
            svg=svg,
            language=language or "",
            render_time_ms=elapsed,
        )
        if format == "png":
            from pidraw.backend.png import svg_to_png

            result.png = svg_to_png(svg, scale=scale, transparent=transparent)
        outputs.append(result)
    return outputs


def _apply_optimization(svg: str, level: str | bool) -> str:
    if level is False:
        return svg
    if level is True:
        level = "balanced"
    if level in _RECOGNISED_LEVELS:
        from pidraw.optimizer.levels import optimize_by_level

        return optimize_by_level(svg, level=level).svg
    from pidraw.optimizer import optimize_svg

    return optimize_svg(svg).svg
