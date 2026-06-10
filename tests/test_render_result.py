"""Tests for RenderResult dataclass."""

from __future__ import annotations

from pathlib import Path

from pidraw.result import RenderResult


class TestRenderResult:
    def test_defaults(self) -> None:
        r = RenderResult(svg="<svg></svg>")
        assert r.svg == "<svg></svg>"
        assert r.png is None
        assert r.language == ""
        assert r.engine_used == ""
        assert r.render_time_ms == 0.0
        assert r.warnings == []
        assert r.cache_hit is False
        assert r.source_hash == ""

    def test_custom_values(self) -> None:
        r = RenderResult(
            svg="<svg></svg>",
            png=b"PNG",
            language="mermaid",
            engine_used="cli:mmdc",
            render_time_ms=42.5,
            warnings=["deprecated"],
            cache_hit=True,
            source_hash="abc123",
        )
        assert r.png == b"PNG"
        assert r.language == "mermaid"
        assert r.engine_used == "cli:mmdc"
        assert r.render_time_ms == 42.5
        assert r.warnings == ["deprecated"]
        assert r.cache_hit is True
        assert r.source_hash == "abc123"

    def test_len(self) -> None:
        r = RenderResult(svg="<svg></svg>")
        assert len(r) == len("<svg></svg>")

    def test_save_svg(self, tmp_path: Path) -> None:
        r = RenderResult(svg="<svg></svg>")
        out = tmp_path / "test.svg"
        r.save(str(out))
        assert out.read_text(encoding="utf-8") == "<svg></svg>"

    def test_save_png(self, tmp_path: Path) -> None:
        r = RenderResult(svg="<svg></svg>", png=b"PNGDATA")
        out = tmp_path / "test.png"
        r.save(str(out))
        assert out.read_bytes() == b"PNGDATA"

    def test_save_png_no_data(self, tmp_path: Path) -> None:
        r = RenderResult(svg="<svg></svg>")
        out = tmp_path / "test.png"
        try:
            r.save(str(out))
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert "No PNG data" in str(exc)

    def test_save_no_ext_inferred(self, tmp_path: Path) -> None:
        r = RenderResult(svg="<svg></svg>")
        out = tmp_path / "test"
        r.save(str(out))
        assert out.read_text(encoding="utf-8") == "<svg></svg>"

    def test_fields_order(self) -> None:
        import dataclasses

        fields = [f.name for f in dataclasses.fields(RenderResult)]
        assert fields == [
            "svg",
            "png",
            "language",
            "engine_used",
            "render_time_ms",
            "warnings",
            "cache_hit",
            "source_hash",
        ]

    def test_mutable_warnings(self) -> None:
        r = RenderResult(svg="<svg></svg>")
        r.warnings.append("test warning")
        assert r.warnings == ["test warning"]

    def test_large_svg_len(self) -> None:
        svg = "<svg>" + "x" * 10000 + "</svg>"
        r = RenderResult(svg=svg)
        assert len(r) == len(svg)
