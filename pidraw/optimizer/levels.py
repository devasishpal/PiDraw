"""SVG optimisation levels — fast, balanced, maximum.

Each level selects a subset of optimisation passes that trade
compression ratio for execution speed.
"""

from __future__ import annotations

from pidraw.optimizer.svg_optimizer import (
    PASS_REGISTRY,
    OptimizationResult,
    _resolve_passes,
)
from pidraw.optimizer.validators import validate_svg

# ---------------------------------------------------------------------------
# Level definitions
# ---------------------------------------------------------------------------

_FAST_PASSES: list[str] = [
    "remove_comments",
    "remove_editor_metadata",
    "trim_whitespace",
]

_BALANCED_PASSES: list[str] = [
    "remove_comments",
    "remove_editor_metadata",
    "remove_unused_defs",
    "merge_duplicate_defs",
    "collapse_redundant_groups",
    "remove_empty_elements",
    "normalize_transforms",
    "simplify_paths",
    "trim_whitespace",
    "normalize_attribute_ordering",
]

_MAXIMUM_PASSES: list[str] = list(PASS_REGISTRY.keys())

_LEVEL_MAP: dict[str, list[str]] = {
    "fast": _FAST_PASSES,
    "balanced": _BALANCED_PASSES,
    "maximum": _MAXIMUM_PASSES,
}

SUPPORTED_LEVELS: frozenset[str] = frozenset(_LEVEL_MAP.keys())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def optimize_by_level(
    svg: str,
    level: str = "balanced",
    validate_input: bool = True,
    validate_output: bool = True,
) -> OptimizationResult:
    """Optimise an SVG string at the given level.

    Parameters
    ----------
    svg :
        The SVG string.
    level :
        One of ``"fast"``, ``"balanced"``, ``"maximum"``.
    validate_input :
        Validate before optimisation.
    validate_output :
        Validate after optimisation.

    Returns
    -------
    OptimizationResult

    Raises
    ------
    ValueError
        If *level* is not recognised.

    """
    if level not in _LEVEL_MAP:
        msg = f"Unknown optimisation level: {level!r}.  Choose from: {sorted(_LEVEL_MAP)}"
        raise ValueError(msg)

    pass_names = _LEVEL_MAP[level]
    return _optimize_with_passes(
        svg, pass_names, validate_input=validate_input, validate_output=validate_output
    )


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _optimize_with_passes(
    svg: str,
    pass_names: list[str],
    validate_input: bool = True,
    validate_output: bool = True,
) -> OptimizationResult:
    import time

    start = time.perf_counter()

    if validate_input:
        validate_svg(svg)

    original_bytes = len(svg.encode("utf-8"))
    resolved = _resolve_passes(pass_names)

    current = svg
    for fn in resolved:
        current = fn(current)

    if validate_output:
        validate_svg(current)

    optimized_bytes = len(current.encode("utf-8"))
    bytes_saved = original_bytes - optimized_bytes
    reduction = (bytes_saved / original_bytes * 100.0) if original_bytes else 0.0
    elapsed = (time.perf_counter() - start) * 1000.0

    return OptimizationResult(
        original_size=original_bytes,
        optimized_size=optimized_bytes,
        bytes_saved=bytes_saved,
        reduction_percent=reduction,
        svg=current,
        passes_applied=list(pass_names),
        elapsed_ms=elapsed,
    )
