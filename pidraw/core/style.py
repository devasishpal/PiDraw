from __future__ import annotations

from pidraw.core.models import EdgeStyle, FontWeight, Style, TextAlign


def make_style(
    stroke_color: str | None = None,
    stroke_width: float | None = None,
    stroke_style: EdgeStyle | None = None,
    fill_color: str | None = None,
    fill_opacity: float | None = None,
    padding: float | None = None,
    margin: float | None = None,
    spacing: float | None = None,
    corner_radius: float | None = None,
    font_family: str | None = None,
    font_size: float | None = None,
    font_weight: FontWeight | None = None,
    text_align: TextAlign | None = None,
    text_color: str | None = None,
) -> Style:
    kwargs: dict = {}
    if stroke_color is not None:
        kwargs["stroke_color"] = stroke_color
    if stroke_width is not None:
        kwargs["stroke_width"] = stroke_width
    if stroke_style is not None:
        kwargs["stroke_style"] = stroke_style
    if fill_color is not None:
        kwargs["fill_color"] = fill_color
    if fill_opacity is not None:
        kwargs["fill_opacity"] = fill_opacity
    if padding is not None:
        kwargs["padding"] = padding
    if margin is not None:
        kwargs["margin"] = margin
    if spacing is not None:
        kwargs["spacing"] = spacing
    if corner_radius is not None:
        kwargs["corner_radius"] = corner_radius
    if font_family is not None:
        kwargs["font_family"] = font_family
    if font_size is not None:
        kwargs["font_size"] = font_size
    if font_weight is not None:
        kwargs["font_weight"] = font_weight
    if text_align is not None:
        kwargs["text_align"] = text_align
    if text_color is not None:
        kwargs["text_color"] = text_color
    return Style(**kwargs)


def style_to_css(style: Style) -> dict[str, str]:
    props: dict[str, str] = {}
    props["stroke"] = style.stroke_color
    props["stroke-width"] = str(style.stroke_width)
    props["fill"] = style.fill_color
    props["fill-opacity"] = str(style.fill_opacity)
    props["opacity"] = str(style.opacity)
    props["font-family"] = style.font_family
    props["font-size"] = f"{style.font_size}px"
    props["font-weight"] = style.font_weight.value
    props["text-anchor"] = _text_anchor(style.text_align)
    props["fill"] = style.text_color if style.text_align == TextAlign.LEFT else style.fill_color
    if style.stroke_style == EdgeStyle.DASHED:
        props["stroke-dasharray"] = f"{style.stroke_width * 4},{style.stroke_width * 4}"
    elif style.stroke_style == EdgeStyle.DOTTED:
        props["stroke-dasharray"] = f"{style.stroke_width},{style.stroke_width * 3}"
    elif style.stroke_style == EdgeStyle.BOLD:
        props["stroke-width"] = str(style.stroke_width * 2.5)
    return props


def _text_anchor(align: TextAlign) -> str:
    if align == TextAlign.LEFT:
        return "start"
    if align == TextAlign.RIGHT:
        return "end"
    return "middle"
