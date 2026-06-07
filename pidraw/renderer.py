"""Public render API — detect, select, and render diagram source to SVG.

Supports automatic language detection, manual override, optimisation
levels, file-based input, and batch rendering.
"""

from __future__ import annotations

import os
from typing import Iterable

from pidraw.detector import detect
from pidraw.exceptions import UnsupportedLanguageError
from pidraw.registry import get_renderer

_RECOGNISED_LEVELS = frozenset({"fast", "balanced", "maximum"})


def render(
    source: str,
    language: str | None = None,
    *,
    optimize: str | bool = False,
    quality: bool = False,
) -> str:
    """Render a diagram source string into SVG.

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
    optimize : str or bool
        Optimisation level.  ``False`` (default) = no optimisation.
        ``True`` = ``"balanced"``.  String values: ``"fast"``,
        ``"balanced"``, ``"maximum"``.
    quality : bool
        If ``True``, run the quality enhancement pipeline on output.

    Returns
    -------
    str
        The rendered (and optionally optimised) SVG output.

    Raises
    ------
    UnsupportedLanguageError
        If the language cannot be detected or is not supported.
    RendererNotFoundError
        If the detected/explicit language has no registered renderer.
    RenderingError
        If the rendering process itself fails.

    """
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

    return svg


def render_file(
    path: str,
    language: str | None = None,
    *,
    optimize: str | bool = False,
    quality: bool = False,
) -> str:
    """Read a diagram file and render it to SVG.

    Parameters
    ----------
    path : str
        Path to the diagram source file.
    language : str | None
        Explicit language identifier.  Auto-detected when ``None``.
    optimize : str or bool
        Optimisation level (see :func:`render`).
    quality : bool
        If ``True``, run quality enhancement pipeline.

    Returns
    -------
    str
        The rendered SVG output.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    UnsupportedLanguageError
        If the language cannot be detected.
    RendererNotFoundError
        If no renderer is registered for the language.
    RenderingError
        If the rendering process fails.

    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Diagram file not found: {path}")

    with open(path, "r", encoding="utf-8-sig") as f:
        source = f.read().lstrip("\ufeff")

    return render(source, language=language, optimize=optimize, quality=quality)


def render_many(
    sources: Iterable[str],
    language: str | None = None,
    *,
    max_workers: int | None = None,
    optimize: str | bool = False,
    quality: bool = False,
) -> list[str]:
    """Render multiple diagram sources in parallel.

    Parameters
    ----------
    sources :
        Iterable of diagram source strings.
    language :
        Explicit language override for all sources.
    max_workers :
        Maximum parallel workers (default = CPU count).
    optimize :
        Optimisation level (see :func:`render`).
    quality :
        If ``True``, run quality enhancement.

    Returns
    -------
    list[str]
        Rendered SVG strings, one per input in the same order.

    """
    from pidraw.pool import RenderPool

    pool = RenderPool(max_workers=max_workers)
    results = pool.render_many(
        sources, language=language, show_progress=False
    )

    svgs: list[str] = []
    for r in results:
        if r.error:
            raise UnsupportedLanguageError(r.error)
        svg = r.svg
        if optimize:
            svg = _apply_optimization(svg, optimize)
        if quality:
            from pidraw.quality import QualityProcessor
            svg = QualityProcessor().process(svg)
        svgs.append(svg)
    return svgs


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
