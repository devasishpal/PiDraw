from __future__ import annotations

from pidraw.core.models import Diagram, Label, Node, Size
from pidraw.themes import apply_theme, get_theme, list_themes


class TestThemes:
    def test_list_themes(self) -> None:
        themes = list_themes()
        assert "light" in themes
        assert "dark" in themes
        assert "minimal" in themes
        assert "professional" in themes
        assert "blueprint" in themes

    def test_get_theme(self) -> None:
        theme = get_theme("light")
        assert theme is not None
        assert theme.name == "light"

    def test_get_theme_case_insensitive(self) -> None:
        theme = get_theme("DARK")
        assert theme is not None
        assert theme.name == "dark"

    def test_light_theme_style(self) -> None:
        theme = get_theme("light")
        assert theme is not None
        style = theme.style()
        assert style.fill_color == "#ffffff"
        assert style.text_color == "#333333"

    def test_dark_theme_style(self) -> None:
        theme = get_theme("dark")
        assert theme is not None
        style = theme.style()
        assert style.fill_color == "#1e1e1e"

    def test_minimal_theme_style(self) -> None:
        theme = get_theme("minimal")
        assert theme is not None
        style = theme.style()
        assert style.stroke_width == 1.0

    def test_professional_theme_style(self) -> None:
        theme = get_theme("professional")
        assert theme is not None
        style = theme.style()
        assert style.shadow is True

    def test_blueprint_theme_style(self) -> None:
        theme = get_theme("blueprint")
        assert theme is not None
        style = theme.style()
        assert "monospace" in style.font_family or "Courier" in style.font_family

    def test_apply_dark_theme_to_diagram(self) -> None:
        d = Diagram(id="test")
        d.add_node(Node(id="n1", label=Label(text="Test"), size=Size(100, 50)))
        result = apply_theme(d, "dark")
        assert result.style is not None

    def test_unknown_theme_returns_none(self) -> None:
        theme = get_theme("nonexistent")
        assert theme is None
