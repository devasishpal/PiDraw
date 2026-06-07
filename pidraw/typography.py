from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pidraw.core.models import FontWeight, TextAlign


@dataclass
class FontSpec:
    family: str = "sans-serif"
    size: float = 14.0
    weight: FontWeight = FontWeight.NORMAL
    align: TextAlign = TextAlign.CENTER
    color: str = "#333333"
    line_height: float = 1.2
    letter_spacing: float = 0.0

    def to_css(self) -> dict[str, str]:
        anchor = "middle"
        if self.align == TextAlign.LEFT:
            anchor = "start"
        elif self.align == TextAlign.RIGHT:
            anchor = "end"
        return {
            "font-family": self.family,
            "font-size": f"{self.size}px",
            "font-weight": self.weight.value,
            "text-anchor": anchor,
            "fill": self.color,
        }


@dataclass
class TextMetrics:
    width: float = 0.0
    height: float = 0.0
    lines: int = 0
    max_line_width: float = 0.0


_FONT_CACHE: dict[str, tuple[float, float]] = {}
_CHAR_WIDTH_CACHE: dict[str, float] = {}


def estimate_text_size(
    text: str,
    font_size: float = 14.0,
    font_family: str = "sans-serif",
    weight: FontWeight = FontWeight.NORMAL,
    max_width: float | None = None,
) -> TextMetrics:
    char_width = _get_avg_char_width(font_family, font_size, weight)
    line_height = font_size * 1.2
    lines = text.split("\n")

    if max_width is not None:
        wrapped_lines: list[str] = []
        for line in lines:
            while line and len(line) * char_width > max_width:
                split_at = int(max_width / char_width)
                wrapped_lines.append(line[:split_at])
                line = line[split_at:]
            if line:
                wrapped_lines.append(line)
        lines = wrapped_lines

    max_line = max((len(l) for l in lines), default=0)
    total_width = max_line * char_width
    total_height = len(lines) * line_height

    return TextMetrics(
        width=total_width,
        height=total_height,
        lines=len(lines),
        max_line_width=total_width,
    )


def _get_avg_char_width(
    font_family: str,
    font_size: float,
    weight: FontWeight,
) -> float:
    cache_key = f"{font_family}:{font_size}:{weight.value}"
    if cache_key in _CHAR_WIDTH_CACHE:
        return _CHAR_WIDTH_CACHE[cache_key]

    ratio = 0.6
    if font_family in ("monospace", "Courier New", "Courier", "Consolas"):
        ratio = 0.55
    elif font_family in ("sans-serif", "Arial", "Helvetica"):
        ratio = 0.6
    elif font_family in ("serif", "Georgia", "Times New Roman"):
        ratio = 0.65

    width = font_size * ratio
    _CHAR_WIDTH_CACHE[cache_key] = width
    return width


def wrap_text(text: str, max_width: float, font_size: float = 14.0, font_family: str = "sans-serif") -> list[str]:
    char_width = _get_avg_char_width(font_family, font_size, FontWeight.NORMAL)
    max_chars = max(1, int(max_width / char_width))

    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            if current and len(current) + 1 + len(word) > max_chars:
                lines.append(current)
                current = word
            elif current:
                current += " " + word
            else:
                current = word
        if current:
            lines.append(current)
        elif not paragraph:
            lines.append("")

    return lines or [""]
