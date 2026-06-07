"""Diagnostics and analysis for diagram source code."""

from __future__ import annotations

from pidraw.detector import detect_language
from pidraw.exceptions import RendererNotFoundError, RenderingError
from pidraw.models import AnalysisResult, DiagramLanguage
from pidraw.optimizer.svg_optimizer import optimize_svg
from pidraw.registry import get_renderer


def analyze(
    source: str,
    render: bool = True,
    optimize: bool = True,
) -> AnalysisResult:
    """Analyse a diagram source string and optionally render + optimise it.

    Parameters
    ----------
    source : str
        The diagram source code.
    render : bool
        If ``True`` (default), run the renderer and include the SVG.
    optimize : bool
        If ``True`` (default) and *render* is also ``True``, run the
        optimisation pipeline on the output and include statistics.

    Returns
    -------
    AnalysisResult
        Detected language, confidence, renderer info, warnings, SVG,
        and optimisation metrics.

    """
    detection = detect_language(source)
    lang = detection.language
    warnings: list[str] = []
    renderer_name: str | None = None
    svg: str | None = None
    orig_size = 0
    opt_size = 0
    bytes_saved = 0
    reduction = 0.0

    if lang == DiagramLanguage.UNKNOWN:
        warnings.append("Could not detect diagram language")

    if lang != DiagramLanguage.UNKNOWN:
        try:
            r = get_renderer(lang.value)
            renderer_name = type(r).__name__
        except RendererNotFoundError as exc:
            warnings.append(f"Renderer not found: {exc}")
        except Exception as exc:
            warnings.append(f"Renderer error: {exc}")

    if render and renderer_name is not None and lang != DiagramLanguage.UNKNOWN:
        try:
            r = get_renderer(lang.value)
            raw_svg = r.render(source)
            svg = raw_svg

            if optimize:
                try:
                    opt_result = optimize_svg(raw_svg)
                    svg = opt_result.svg
                    orig_size = opt_result.original_size
                    opt_size = opt_result.optimized_size
                    bytes_saved = opt_result.bytes_saved
                    reduction = opt_result.reduction_percent
                except Exception as exc:
                    warnings.append(f"Optimisation skipped: {exc}")
        except RenderingError as exc:
            warnings.append(f"Rendering failed: {exc}")
        except Exception as exc:
            warnings.append(f"Rendering error: {exc}")

    return AnalysisResult(
        detected_language=lang.value,
        confidence=detection.confidence,
        renderer_chosen=renderer_name,
        warnings=warnings,
        svg=svg,
        original_size=orig_size,
        optimized_size=opt_size,
        bytes_saved=bytes_saved,
        reduction_percent=reduction,
    )
