from __future__ import annotations

from pidraw.core.models import FontWeight, TextAlign
from pidraw.typography import FontSpec, estimate_text_size, wrap_text


class TestFontSpec:
    def test_default_values(self) -> None:
        fs = FontSpec()
        assert fs.family == "sans-serif"
        assert fs.size == 14.0
        assert fs.weight == FontWeight.NORMAL

    def test_to_css_center(self) -> None:
        fs = FontSpec(align=TextAlign.CENTER)
        css = fs.to_css()
        assert css["text-anchor"] == "middle"

    def test_to_css_left(self) -> None:
        fs = FontSpec(align=TextAlign.LEFT)
        css = fs.to_css()
        assert css["text-anchor"] == "start"

    def test_to_css_right(self) -> None:
        fs = FontSpec(align=TextAlign.RIGHT)
        css = fs.to_css()
        assert css["text-anchor"] == "end"


class TestEstimateTextSize:
    def test_single_line(self) -> None:
        m = estimate_text_size("Hello", font_size=14)
        assert m.width > 0
        assert m.height > 0
        assert m.lines == 1

    def test_multi_line(self) -> None:
        m = estimate_text_size("Hello\nWorld", font_size=14)
        assert m.lines == 2

    def test_empty_string(self) -> None:
        m = estimate_text_size("", font_size=14)
        assert m.lines == 1
        assert m.width >= 0


class TestWrapText:
    def test_no_wrap_needed(self) -> None:
        lines = wrap_text("Hello", max_width=500, font_size=14)
        assert len(lines) == 1
        assert lines[0] == "Hello"

    def test_wrap_long_text(self) -> None:
        lines = wrap_text("This is a very long line of text", max_width=50, font_size=14)
        assert len(lines) > 1

    def test_multiple_paragraphs(self) -> None:
        lines = wrap_text("Hello\nWorld", max_width=500, font_size=14)
        assert len(lines) == 2
