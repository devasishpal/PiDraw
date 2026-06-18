"""Equation renderer — LaTeX math to SVG/PNG.

Uses matplotlib's mathtext engine (no LaTeX installation required).
Falls back to a simple HTML+CSS approach if matplotlib is unavailable.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from io import BytesIO

_HAS_MATPLOTLIB = False
try:
    import matplotlib
    matplotlib.use("AGG")
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    _HAS_MATPLOTLIB = True
except ImportError:
    pass

_HAS_LATEX = False
try:
    import subprocess
    result = subprocess.run(
        ["latex", "--version"],
        capture_output=True,
        timeout=5,
    )
    _HAS_LATEX = result.returncode == 0
except Exception:
    pass


@dataclass
class EquationResult:
    """Result of rendering a LaTeX equation."""

    source: str
    latex: str = ""
    svg: str | None = None
    png: bytes | None = None
    error: str | None = None
    render_time: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.error is None and self.svg is not None


# ---------------------------------------------------------------------------
# LaTeX normalization
# ---------------------------------------------------------------------------

_LATEX_REPLACEMENTS: dict[str, str] = {
    r"\infty": r"\infty",
    r"\pi": r"\pi",
    r"\alpha": r"\alpha",
    r"\beta": r"\beta",
    r"\gamma": r"\gamma",
    r"\delta": r"\delta",
    r"\epsilon": r"\epsilon",
    r"\varepsilon": r"\varepsilon",
    r"\zeta": r"\zeta",
    r"\eta": r"\eta",
    r"\theta": r"\theta",
    r"\vartheta": r"\vartheta",
    r"\iota": r"\iota",
    r"\kappa": r"\kappa",
    r"\lambda": r"\lambda",
    r"\mu": r"\mu",
    r"\nu": r"\nu",
    r"\xi": r"\xi",
    r"\omicron": r"\omicron",
    r"\rho": r"\rho",
    r"\sigma": r"\sigma",
    r"\varsigma": r"\varsigma",
    r"\tau": r"\tau",
    r"\upsilon": r"\upsilon",
    r"\phi": r"\phi",
    r"\varphi": r"\varphi",
    r"\chi": r"\chi",
    r"\psi": r"\psi",
    r"\omega": r"\omega",
    r"\Gamma": r"\Gamma",
    r"\Delta": r"\Delta",
    r"\Theta": r"\Theta",
    r"\Lambda": r"\Lambda",
    r"\Xi": r"\Xi",
    r"\Pi": r"\Pi",
    r"\Sigma": r"\Sigma",
    r"\Phi": r"\Phi",
    r"\Psi": r"\Psi",
    r"\Omega": r"\Omega",
    r"\partial": r"\partial",
    r"\nabla": r"\nabla",
    r"\sqrt": r"\sqrt",
    r"\int": r"\int",
    r"\iint": r"\iint",
    r"\iiint": r"\iiint",
    r"\oint": r"\oint",
    r"\sum": r"\sum",
    r"\prod": r"\prod",
    r"\coprod": r"\coprod",
    r"\cdot": r"\cdot",
    r"\times": r"\times",
    r"\div": r"\div",
    r"\pm": r"\pm",
    r"\mp": r"\mp",
    r"\leq": r"\leq",
    r"\geq": r"\geq",
    r"\neq": r"\neq",
    r"\approx": r"\approx",
    r"\equiv": r"\equiv",
    r"\subset": r"\subset",
    r"\supset": r"\supset",
    r"\subseteq": r"\subseteq",
    r"\supseteq": r"\supseteq",
    r"\cap": r"\cap",
    r"\cup": r"\cup",
    r"\in": r"\in",
    r"\notin": r"\notin",
    r"\forall": r"\forall",
    r"\exists": r"\exists",
    r"\emptyset": r"\emptyset",
    r"\varnothing": r"\varnothing",
    r"\to": r"\to",
    r"\rightarrow": r"\rightarrow",
    r"\leftarrow": r"\leftarrow",
    r"\mapsto": r"\mapsto",
    r"\Rightarrow": r"\Rightarrow",
    r"\Leftarrow": r"\Leftarrow",
    r"\implies": r"\implies",
    r"\iff": r"\iff",
    r"\otimes": r"\otimes",
    r"\oplus": r"\oplus",
    r"\dagger": r"\dagger",
    r"\ddagger": r"\ddagger",
    r"\dots": r"\dots",
    r"\cdots": r"\cdots",
    r"\vdots": r"\vdots",
    r"\ddots": r"\ddots",
    r"\ell": r"\ell",
    r"\hbar": r"\hbar",
    r"\Re": r"\Re",
    r"\Im": r"\Im",
    r"\wp": r"\wp",
    r"\aleph": r"\aleph",
    r"\triangle": r"\triangle",
    r"\angle": r"\angle",
    r"\perp": r"\perp",
    r"\circ": r"\circ",
    r"\bullet": r"\bullet",
    r"\star": r"\star",
    r"\langle": r"\langle",
    r"\rangle": r"\rangle",
    r"\lvert": r"\lvert",
    r"\rvert": r"\rvert",
    r"\lVert": r"\lVert",
    r"\rVert": r"\rVert",
    r"\sin": r"\sin",
    r"\cos": r"\cos",
    r"\tan": r"\tan",
    r"\cot": r"\cot",
    r"\sec": r"\sec",
    r"\csc": r"\csc",
    r"\sinh": r"\sinh",
    r"\cosh": r"\cosh",
    r"\tanh": r"\tanh",
    r"\coth": r"\coth",
    r"\arcsin": r"\arcsin",
    r"\arccos": r"\arccos",
    r"\arctan": r"\arctan",
    r"\log": r"\log",
    r"\ln": r"\ln",
    r"\lg": r"\lg",
    r"\exp": r"\exp",
    r"\det": r"\det",
    r"\dim": r"\dim",
    r"\hom": r"\hom",
    r"\ker": r"\ker",
    r"\arg": r"\arg",
    r"\deg": r"\deg",
    r"\lim": r"\lim",
    r"\liminf": r"\liminf",
    r"\limsup": r"\limsup",
    r"\max": r"\max",
    r"\min": r"\min",
    r"\sup": r"\sup",
    r"\inf": r"\inf",
    r"\Pr": r"\Pr",
    r"\mod": r"\mod",
    r"\pmod": r"\pmod",
    r"\bmod": r"\bmod",
    r"\mathbb": r"\mathbb",
    r"\mathbf": r"\mathbf",
    r"\mathcal": r"\mathcal",
    r"\mathfrak": r"\mathfrak",
    r"\mathit": r"\mathit",
    r"\mathrm": r"\mathrm",
    r"\mathscr": r"\mathscr",
    r"\mathsf": r"\mathsf",
    r"\mathtt": r"\mathtt",
    r"\operatorname": r"\operatorname",
    r"\left": r"\left",
    r"\right": r"\right",
    r"\bigl": r"\bigl",
    r"\bigr": r"\bigr",
    r"\Bigl": r"\Bigl",
    r"\Bigr": r"\Bigr",
    r"\biggl": r"\biggl",
    r"\biggr": r"\biggr",
    r"\Biggl": r"\Biggl",
    r"\Biggr": r"\Biggr",
    r"\colon": r"\colon",
    r"\longrightarrow": r"\longrightarrow",
    r"\longleftarrow": r"\longleftarrow",
    r"\longmapsto": r"\longmapsto",
    r"\longleftrightarrow": r"\longleftrightarrow",
    r"\hookrightarrow": r"\hookrightarrow",
    r"\hookleftarrow": r"\hookleftarrow",
    r"\twoheadrightarrow": r"\twoheadrightarrow",
    r"\twoheadleftarrow": r"\twoheadleftarrow",
    r"\rightleftharpoons": r"\rightleftharpoons",
    r"\leftrightharpoons": r"\leftrightharpoons",
    r"\uparrow": r"\uparrow",
    r"\downarrow": r"\downarrow",
    r"\updownarrow": r"\updownarrow",
    r"\Uparrow": r"\Uparrow",
    r"\Downarrow": r"\Downarrow",
    r"\Updownarrow": r"\Updownarrow",
    r"\nearrow": r"\nearrow",
    r"\searrow": r"\searrow",
    r"\swarrow": r"\swarrow",
    r"\nwarrow": r"\nwarrow",
    r"\le": r"\le",
    r"\ge": r"\ge",
    r"\ne": r"\ne",
    r"\ast": r"\ast",
    r"\diamond": r"\diamond",
    r"\sqcup": r"\sqcup",
    r"\sqcap": r"\sqcap",
    r"\vee": r"\vee",
    r"\wedge": r"\wedge",
    r"\ominus": r"\ominus",
    r"\oslash": r"\oslash",
    r"\odot": r"\odot",
    r"\bigcirc": r"\bigcirc",
    r"\triangleleft": r"\triangleleft",
    r"\triangleright": r"\triangleright",
    r"\bigtriangleup": r"\bigtriangleup",
    r"\bigtriangledown": r"\bigtriangledown",
    r"\Box": r"\Box",
    r"\Diamond": r"\Diamond",
    r"\lhd": r"\lhd",
    r"\rhd": r"\rhd",
    r"\unlhd": r"\unlhd",
    r"\unrhd": r"\unrhd",
}


def normalize_latex(source: str) -> str:
    """Clean LaTeX source by stripping delimiters and normalizing."""
    s = source.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    elif s.startswith(r"\(") and s.endswith(r"\)"):
        s = s[2:-2].strip()
    elif s.startswith(r"\[") and s.endswith(r"\]"):
        s = s[2:-2].strip()
    elif s.startswith(r"\begin{equation*}") and s.endswith(r"\end{equation*}"):
        s = s[len(r"\begin{equation*}"):-len(r"\end{equation*}")].strip()
    elif s.startswith(r"\begin{equation}") and s.endswith(r"\end{equation}"):
        s = s[len(r"\begin{equation}"):-len(r"\end{equation}")].strip()
    elif s.startswith(r"\begin{align*}") and s.endswith(r"\end{align*}"):
        s = s[len(r"\begin{align*}"):-len(r"\end{align*}")].strip()
    elif s.startswith(r"\begin{align}") and s.endswith(r"\end{align}"):
        s = s[len(r"\begin{align}"):-len(r"\end{align}")].strip()
    return s


def _sanitize_for_matplotlib(latex: str) -> str:
    """Convert LaTeX to a form that matplotlib's mathtext can handle.

    Matplotlib's built-in mathtext supports a large subset of LaTeX.
    This function converts or replaces unsupported constructs.
    """
    s = latex.strip()

    s = s.replace(r"\begin{align*}", r"\displaystyle ")
    s = s.replace(r"\end{align*}", "")
    s = s.replace(r"\begin{align}", r"\displaystyle ")
    s = s.replace(r"\end{align}", "")
    s = s.replace(r"\begin{aligned}", r"\displaystyle ")
    s = s.replace(r"\end{aligned}", "")
    s = s.replace(r"\begin{equation*}", r"\displaystyle ")
    s = s.replace(r"\end{equation*}", "")
    s = s.replace(r"\begin{equation}", r"\displaystyle ")
    s = s.replace(r"\end{equation}", "")
    s = s.replace(r"\begin{matrix}", r"\begin{bmatrix}")
    s = s.replace(r"\end{matrix}", r"\end{bmatrix}")
    s = s.replace(r"\begin{pmatrix}", r"\begin{pmatrix}")
    s = s.replace(r"\begin{bmatrix}", r"\begin{bmatrix}")
    s = s.replace(r"\begin{Bmatrix}", r"\begin{Bmatrix}")
    s = s.replace(r"\begin{vmatrix}", r"\begin{vmatrix}")
    s = s.replace(r"\begin{Vmatrix}", r"\begin{Vmatrix}")
    s = s.replace(r"\begin{cases}", r"\begin{cases}")
    s = s.replace(r"\text{", r"\mathrm{")
    s = s.replace(r"\textnormal{", r"\mathrm{")
    s = s.replace(r"\textrm{", r"\mathrm{")

    return s


def _sanitize_for_html(latex: str) -> str:
    """Convert LaTeX to HTML with CSS styling."""
    s = latex.strip()

    s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", _replace_frac, s)
    s = re.sub(r"\\sqrt(?:\[([^\]]*)\])?\{([^{}]*)\}", _replace_sqrt, s)
    s = re.sub(r"\\text\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"_\{([^{}]*)\}", r"<sub>\1</sub>", s)
    s = re.sub(r"\^\{([^{}]*)\}", r"<sup>\1</sup>", s)
    s = re.sub(r"_([a-zA-Z0-9])", r"<sub>\1</sub>", s)
    s = re.sub(r"\^([a-zA-Z0-9])", r"<sup>\1</sup>", s)
    s = re.sub(r"\\sum", "∑", s)
    s = re.sub(r"\\int", "∫", s)
    s = re.sub(r"\\infty", "∞", s)
    s = re.sub(r"\\pi", "π", s)
    s = re.sub(r"\\alpha", "α", s)
    s = re.sub(r"\\beta", "β", s)
    s = re.sub(r"\\gamma", "γ", s)
    s = re.sub(r"\\delta", "δ", s)
    s = re.sub(r"\\epsilon", "ε", s)
    s = re.sub(r"\\theta", "θ", s)
    s = re.sub(r"\\lambda", "λ", s)
    s = re.sub(r"\\mu", "μ", s)
    s = re.sub(r"\\sigma", "σ", s)
    s = re.sub(r"\\phi", "φ", s)
    s = re.sub(r"\\omega", "ω", s)
    s = re.sub(r"\\cdot", "·", s)
    s = re.sub(r"\\times", "×", s)
    s = re.sub(r"\\div", "÷", s)
    s = re.sub(r"\\pm", "±", s)
    s = re.sub(r"\\leq", "≤", s)
    s = re.sub(r"\\geq", "≥", s)
    s = re.sub(r"\\neq", "≠", s)
    s = re.sub(r"\\approx", "≈", s)
    s = re.sub(r"\\equiv", "≡", s)
    s = re.sub(r"\\partial", "∂", s)
    s = re.sub(r"\\nabla", "∇", s)
    s = re.sub(r"\\to", "→", s)
    s = re.sub(r"\\rightarrow", "→", s)
    s = re.sub(r"\\leftarrow", "←", s)
    s = re.sub(r"\\Rightarrow", "⇒", s)
    s = re.sub(r"\\Leftarrow", "⇐", s)
    s = re.sub(r"\\mapsto", "↦", s)
    s = re.sub(r"\\implies", "⟹", s)
    s = re.sub(r"\\iff", "⟺", s)
    s = re.sub(r"\\in", "∈", s)
    s = re.sub(r"\\notin", "∉", s)
    s = re.sub(r"\\subset", "⊂", s)
    s = re.sub(r"\\supset", "⊃", s)
    s = re.sub(r"\\subseteq", "⊆", s)
    s = re.sub(r"\\supseteq", "⊇", s)
    s = re.sub(r"\\cup", "∪", s)
    s = re.sub(r"\\cap", "∩", s)
    s = re.sub(r"\\forall", "∀", s)
    s = re.sub(r"\\exists", "∃", s)
    s = re.sub(r"\\emptyset", "∅", s)
    s = re.sub(r"\\triangle", "△", s)
    s = re.sub(r"\\angle", "∠", s)
    s = re.sub(r"\\perp", "⊥", s)
    s = re.sub(r"\\circ", "∘", s)
    s = re.sub(r"\\bullet", "•", s)
    s = re.sub(r"\\dots", "…", s)
    s = re.sub(r"\\cdots", "⋯", s)
    s = re.sub(r"\\vdots", "⋮", s)
    s = re.sub(r"\\ddots", "⋱", s)

    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = re.sub(r"\s+", " ", s)

    return s.strip()


def _replace_frac(m: re.Match) -> str:
    num = m.group(1)
    den = m.group(2)
    return f'<span class="frac"><span class="num">{num}</span><span class="den">{den}</span></span>'


def _replace_sqrt(m: re.Match) -> str:
    rad = m.group(2)
    deg = m.group(1)
    deg_html = f'<sup>{deg}</sup>' if deg else ""
    return f'<span class="sqrt">{deg_html}{rad}</span>'


# ---------------------------------------------------------------------------
# Main rendering functions
# ---------------------------------------------------------------------------


def render_equation_svg(
    latex: str,
    *,
    fontsize: float = 20,
    dpi: float = 200,
    foreground: str = "black",
    background: str = "none",
) -> EquationResult:
    """Render a LaTeX equation to SVG.

    Uses matplotlib's mathtext engine (no LaTeX installation required).
    Falls back to HTML+CSS rendering if matplotlib is unavailable.

    Args:
        latex: LaTeX math expression (with or without $ delimiters).
        fontsize: Font size in points.
        dpi: Resolution for measurement (affects SVG quality).
        foreground: Text color (CSS color name or hex).
        background: Background color ("none" for transparent).

    Returns:
        EquationResult with .svg attribute.
    """
    start = time.monotonic()
    clean = normalize_latex(latex)

    if _HAS_MATPLOTLIB:
        return _render_via_matplotlib(
            clean, fontsize=fontsize, dpi=dpi,
            foreground=foreground, background=background, start=start,
        )

    return _render_via_html(
        clean, display=False, background=background, start=start,
    )


def render_equation(
    latex: str,
    *,
    display: bool = False,
    dpi: float = 200,
    transparent: bool = True,
    fontsize: float = 20,
) -> EquationResult:
    """Render a LaTeX equation to SVG + PNG.

    Args:
        latex: LaTeX math expression (with or without $ delimiters).
        display: True for display math (centered, larger).
        dpi: DPI for PNG output.
        transparent: Whether PNG background is transparent.
        fontsize: Font size in points.

    Returns:
        EquationResult with .svg and .png attributes.
    """
    start = time.monotonic()
    clean = normalize_latex(latex)

    svg_result = render_equation_svg(
        clean, fontsize=fontsize, dpi=dpi,
    )

    if not svg_result.success:
        return svg_result

    # Convert SVG to PNG via PiDraw's backend
    png: bytes | None = None
    try:
        from pidraw.backend.png import svg_to_png
        scale = dpi / 96.0
        assert svg_result.svg is not None
        png = svg_to_png(
            svg_result.svg,
            scale=scale,
            transparent=transparent,
        )
    except Exception as exc:
        svg_result.warnings.append(f"PNG conversion failed: {exc}")

    return EquationResult(
        source=latex,
        latex=clean,
        svg=svg_result.svg,
        png=png,
        error=svg_result.error,
        render_time=time.monotonic() - start,
        warnings=svg_result.warnings,
    )


def _render_via_matplotlib(
    latex: str,
    *,
    fontsize: float = 20,
    dpi: float = 200,
    foreground: str = "black",
    background: str = "none",
    start: float | None = None,
) -> EquationResult:
    """Render LaTeX via matplotlib's mathtext to SVG."""
    start = start or time.monotonic()

    try:
        sanitized = _sanitize_for_matplotlib(latex)
        sanitized = f"${sanitized}$"

        rcParams.update({
            "mathtext.fontset": "stix",
            "font.family": "STIXGeneral",
            "mathtext.default": "regular",
        })

        fig, ax = plt.subplots(figsize=(1, 1))
        ax.clear()
        ax.axis("off")

        text_obj = ax.text(
            0.5, 0.5, sanitized,
            fontsize=fontsize,
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax.transAxes,
            color=foreground,
        )

        fig.canvas.draw()
        renderer = fig.canvas.renderer  # type: ignore[attr-defined]
        bbox = text_obj.get_window_extent(renderer)

        padding = 8
        w = int(bbox.width + 2 * padding)
        h = int(bbox.height + 2 * padding)

        fig.clear()
        plt.close(fig)

        fig2, ax2 = plt.subplots(figsize=(w / dpi, h / dpi))
        ax2.clear()
        ax2.axis("off")
        if background and background != "none":
            ax2.set_facecolor(background)

        ax2.text(
            0.5, 0.5, sanitized,
            fontsize=fontsize,
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax2.transAxes,
            color=foreground,
        )

        svg_buf = BytesIO()
        fig2.savefig(
            svg_buf,
            format="svg",
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=0.05,
            transparent=(background == "none"),
        )
        plt.close(fig2)

        svg = svg_buf.getvalue().decode("utf-8")

        return EquationResult(
            source=latex,
            latex=latex,
            svg=svg,
            error=None,
            render_time=time.monotonic() - start,
        )

    except Exception:
        plt.close("all")
        return _render_via_html(
            latex, display=False,
            background=background if background != "none" else "transparent",
            start=start,
        )


def _render_via_html(
    latex: str,
    display: bool = False,
    background: str = "transparent",
    start: float | None = None,
) -> EquationResult:
    """Render LaTeX to SVG via HTML+CSS as fallback."""
    start = start or time.monotonic()
    html_eq = _sanitize_for_html(latex)

    display_css = "text-align: center;" if display else "display: inline;"
    bg_css = f"background: {background};" if background != "transparent" else "background: transparent;"

    w, h = "800", "200"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xhtml="http://www.w3.org/1999/xhtml"
     width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <style>{{
      .eq {{
        font-family: 'Cambria Math', 'Times New Roman', serif;
        font-size: 28px;
        padding: 16px 24px;
        white-space: nowrap;
        {display_css}
        {bg_css}
      }}
      sub {{ font-size: 0.65em; vertical-align: sub; line-height: 0.8; }}
      sup {{ font-size: 0.65em; vertical-align: super; line-height: 0.8; }}
      .frac {{ display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; margin: 0 2px; }}
      .num {{ border-bottom: 1px solid #222; padding: 0 4px 2px 4px; }}
      .den {{ padding: 2px 4px 0 4px; }}
      .sqrt {{ display: inline-flex; align-items: flex-start; }}
      .sqrt .deg {{ font-size: 0.6em; vertical-align: super; }}
      .sqrt::before {{ content: "\\221A"; }}
    }}</style>
  </defs>
  <foreignObject x="0" y="0" width="{w}" height="{h}">
    <xhtml:div xmlns="http://www.w3.org/1999/xhtml"
         style="margin:0;padding:0">
      <div class="eq">{html_eq}</div>
    </xhtml:div>
  </foreignObject>
</svg>"""

    return EquationResult(
        source=latex,
        latex=latex,
        svg=svg,
        error=None,
        render_time=time.monotonic() - start,
        warnings=["Rendered via HTML fallback (limited LaTeX support)"],
    )
