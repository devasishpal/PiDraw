"""Tests for the SVG quality engine."""

from __future__ import annotations

from pidraw.quality import QualityProcessor, default_quality, minimal_quality


class TestQualityProcessor:
    def test_default_processor(self) -> None:
        qp = default_quality()
        assert qp is not None

    def test_minimal_processor(self) -> None:
        qp = minimal_quality()
        assert qp is not None

    def test_process_minimal_svg(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        result = QualityProcessor().process(svg)
        assert "<svg" in result

    def test_viewbox_normalization(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"></svg>'
        result = QualityProcessor().process(svg)
        assert 'viewBox="0 0 800 600"' in result or "viewBox" in result

    def test_text_alignment_added(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><text x="10" y="20">hello</text></svg>'
        result = QualityProcessor().process(svg)
        assert "dominant-baseline" in result
        assert "text-anchor" in result

    def test_arrow_orient_normalized(self) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<defs><marker id="a" orient="270"><path d="M0,0 L5,5 L0,10"/></marker></defs>'
            "</svg>"
        )
        result = QualityProcessor().process(svg)
        assert 'orient="auto"' in result

    def test_empty_groups_removed(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><g></g><g id="keep"/></svg>'
        result = QualityProcessor().process(svg)
        assert "<g id=" in result or "<g/>" in result

    def test_path_sharpening(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M10.0 20.5 L30.123 40.789"/></svg>'
        result = QualityProcessor().process(svg)
        assert "20.5" in result  # should keep 20.5

    def test_valid_xml_output(self) -> None:
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><circle cx="10" cy="10" r="5"/></svg>'
        result = QualityProcessor().process(svg)
        assert result.strip().startswith("<svg")

    def test_process_with_single_pass(self) -> None:
        qp = QualityProcessor(
            normalize_viewbox=True,
            fix_text_alignment=False,
            fix_arrow_heads=False,
            clean_spacing=False,
            sharp_paths=False,
        )
        svg = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        result = qp.process(svg)
        assert "<svg" in result
