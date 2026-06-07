"""Main SVG optimisation orchestration.

Combines all passes into a pipeline and provides the public
:func:`optimize_svg` and :func:`optimize_many` entry points.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

from pidraw.optimizer.passes import (
    collapse_redundant_groups,
    merge_duplicate_defs,
    normalize_attribute_ordering,
    normalize_transforms,
    remove_comments,
    remove_editor_metadata,
    remove_empty_elements,
    remove_unused_defs,
    simplify_paths,
    trim_whitespace,
)
from pidraw.optimizer.validators import validate_svg

# ---------------------------------------------------------------------------
# Pass registry
# ---------------------------------------------------------------------------

PassFunction = Callable[[str], str]

PASS_REGISTRY: dict[str, PassFunction] = {
    "remove_comments": remove_comments,
    "remove_editor_metadata": remove_editor_metadata,
    "remove_unused_defs": remove_unused_defs,
    "merge_duplicate_defs": merge_duplicate_defs,
    "collapse_redundant_groups": collapse_redundant_groups,
    "remove_empty_elements": remove_empty_elements,
    "normalize_transforms": normalize_transforms,
    "simplify_paths": simplify_paths,
    "trim_whitespace": trim_whitespace,
    "normalize_attribute_ordering": normalize_attribute_ordering,
}

DEFAULT_PASSES: list[str] = list(PASS_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class OptimizationResult:
    """Metrics and output from an optimisation run."""

    original_size: int = 0
    """Byte count of the input SVG (UTF-8 encoded)."""

    optimized_size: int = 0
    """Byte count of the output SVG (UTF-8 encoded)."""

    bytes_saved: int = 0
    """``original_size - optimized_size`` (negative if larger)."""

    reduction_percent: float = 0.0
    """Percentage of size reduction (negative if larger)."""

    svg: str = ""
    """The optimised SVG string."""

    passes_applied: list[str] = field(default_factory=list)
    """Names of the passes that were executed."""

    elapsed_ms: float = 0.0
    """Wall-clock time in milliseconds for the whole optimisation."""

    @property
    def ratio(self) -> float:
        """Compression ratio (optimised / original), 0 if no original."""
        if self.original_size == 0:
            return 0.0
        return self.optimized_size / self.original_size


# ---------------------------------------------------------------------------
# Core optimisation
# ---------------------------------------------------------------------------


def _resolve_passes(passes: Iterable[str | PassFunction]) -> list[PassFunction]:
    """Resolve a mixed iterable of pass names and callables to callables."""
    resolved: list[PassFunction] = []
    for item in passes:
        if isinstance(item, str):
            try:
                resolved.append(PASS_REGISTRY[item])
            except KeyError:
                msg = f"Unknown pass: {item!r}.  Available: {list(PASS_REGISTRY)}"
                raise ValueError(msg) from None
        else:
            resolved.append(item)
    return resolved


def optimize_svg(
    svg: str,
    passes: Iterable[str | PassFunction] | None = None,
    validate_input: bool = True,
    validate_output: bool = True,
) -> OptimizationResult:
    """Run the SVG optimisation pipeline.

    Parameters
    ----------
    svg :
        The SVG string to optimise.
    passes :
        Passes to apply, either by name or as callables.
        ``None`` applies all built-in passes.
    validate_input :
        If ``True`` (default), validate *svg* before optimising.
    validate_output :
        If ``True`` (default), validate the result after optimising.

    Returns
    -------
    OptimizationResult
        Contains the optimised SVG and metrics.

    Raises
    ------
    SVGValidationError
        If either input or output validation fails and the
        corresponding flag is ``True``.



    """
    start = time.perf_counter()

    if validate_input:
        validate_svg(svg)

    original_bytes = len(svg.encode("utf-8"))

    pass_list: list[str | PassFunction] = (
        list(DEFAULT_PASSES) if passes is None else list(passes)
    )
    resolved = _resolve_passes(pass_list)

    current = svg
    applied_names: list[str] = []

    for item in pass_list:
        if isinstance(item, str):
            applied_names.append(item)
        else:
            applied_names.append(item.__name__)

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
        passes_applied=applied_names,
        elapsed_ms=elapsed,
    )


# ---------------------------------------------------------------------------
# Batch optimisation
# ---------------------------------------------------------------------------


def optimize_many(
    svgs: Iterable[str],
    passes: Iterable[str | PassFunction] | None = None,
    validate_input: bool = True,
    validate_output: bool = True,
) -> list[OptimizationResult]:
    """Optimise multiple SVGs.

    Parameters
    ----------
    svgs :
        An iterable of SVG strings.
    passes, validate_input, validate_output :
        Forwarded to each :func:`optimize_svg` call.

    Returns
    -------
    list[OptimizationResult]
        One result per input SVG, in the same order.

    """
    return [
        optimize_svg(
            s,
            passes=passes,
            validate_input=validate_input,
            validate_output=validate_output,
        )
        for s in svgs
    ]
