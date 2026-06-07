"""PiDraw SVG optimization engine.

Reduces SVG size, cleans up metadata, normalizes structure,
and guarantees standards-compliant output.
"""

from pidraw.optimizer.levels import optimize_by_level
from pidraw.optimizer.svg_optimizer import OptimizationResult, optimize_many, optimize_svg

__all__ = [
    "OptimizationResult",
    "optimize_many",
    "optimize_svg",
    "optimize_by_level",
]
