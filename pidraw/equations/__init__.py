"""Equation rendering module — renders LaTeX math to SVG/PNG.

Uses matplotlib's mathtext by default (no LaTeX installation required).
"""

from pidraw.equations.renderer import (
    EquationResult,
    render_equation,
    render_equation_svg,
)

__all__ = [
    "EquationResult",
    "render_equation",
    "render_equation_svg",
]
