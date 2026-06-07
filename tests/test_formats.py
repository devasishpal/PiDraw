"""Tests for the formats registry."""

from __future__ import annotations

from pidraw.formats import FormatInfo, format_table, list_formats


class TestListFormats:
    def test_list_formats_returns_list(self) -> None:
        formats = list_formats()
        assert isinstance(formats, list)
        assert len(formats) > 0

    def test_format_info_dataclass(self) -> None:
        fmt = FormatInfo(
            language="test",
            label="Test",
            extensions=[".test"],
            description="A test format",
        )
        assert fmt.language == "test"
        assert fmt.cli_tool == ""

    def test_mermaid_in_list(self) -> None:
        formats = list_formats()
        names = [f.language for f in formats]
        assert "mermaid" in names

    def test_plantuml_in_list(self) -> None:
        formats = list_formats()
        names = [f.language for f in formats]
        assert "plantuml" in names

    def test_graphviz_in_list(self) -> None:
        formats = list_formats()
        names = [f.language for f in formats]
        assert "graphviz" in names

    def test_format_table_output(self) -> None:
        table = format_table()
        assert isinstance(table, str)
        assert "Language" in table
        assert "Extensions" in table
        assert "CLI Tool" in table

    def test_all_extensions(self) -> None:
        formats = list_formats()
        all_exts = []
        for fmt in formats:
            all_exts.extend(fmt.extensions)
        assert ".mmd" in all_exts
        assert ".puml" in all_exts
        assert ".dot" in all_exts
