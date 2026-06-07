"""Tests for the diagnostics and analysis module."""

from __future__ import annotations

from pidraw.diagnostics import analyze
from pidraw.models import AnalysisResult
from pidraw.registry import clear_registry


class TestAnalyze:
    def setup_method(self) -> None:
        clear_registry()

    def test_analyze_returns_analysis_result(self) -> None:
        result = analyze("graph TD\n    A-->B")
        assert isinstance(result, AnalysisResult)

    def test_detected_language_mermaid(self) -> None:
        result = analyze("graph TD\n    A-->B")
        assert result.detected_language == "mermaid"
        assert result.confidence > 0.9

    def test_detected_language_plantuml(self) -> None:
        result = analyze("@startuml\nA-->B\n@enduml")
        assert result.detected_language == "plantuml"
        assert result.confidence > 0.9

    def test_unknown_language_gives_warning(self) -> None:
        result = analyze("this is not a diagram at all")
        assert result.detected_language == "unknown"
        assert any("detect" in w for w in result.warnings)

    def test_renderer_name_populated(self) -> None:
        # After auto-registration, renderer should be found
        from pidraw.engines.base import BaseRenderer
        from pidraw.registry import register_renderer

        class FakeRenderer(BaseRenderer):
            name = "mermaid"
            def render(self, source: str) -> str:
                return "<svg></svg>"

        register_renderer("mermaid", FakeRenderer())

        result = analyze("graph TD\n    A-->B")
        assert result.renderer_chosen == "FakeRenderer"

    def test_renderer_not_found_gives_warning(self) -> None:
        result = analyze("graph TD\n    A-->B")
        assert any("Renderer not found" in w for w in result.warnings)

    def test_confidence_is_float(self) -> None:
        result = analyze("graph TD\n    A-->B")
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    def test_render_true_includes_svg(self) -> None:
        from pidraw.engines.base import BaseRenderer
        from pidraw.registry import register_renderer

        class FakeRenderer(BaseRenderer):
            name = "graphviz"
            def render(self, source: str) -> str:
                return "<svg xmlns='http://www.w3.org/2000/svg'><g id='test'/></svg>"

        register_renderer("graphviz", FakeRenderer())

        result = analyze("digraph G { A -> B }", render=True)
        assert result.svg is not None
        assert "<svg" in result.svg

    def test_optimization_stats_when_render_succeeds(self) -> None:
        from pidraw.engines.mermaid import MermaidRenderer
        from pidraw.registry import register_renderer

        try:
            register_renderer("mermaid", MermaidRenderer())
        except Exception:
            pass

        result = analyze("graph TD\n    A-->B", render=True, optimize=True)
        assert isinstance(result.original_size, int)
        assert isinstance(result.optimized_size, int)

    def test_analyze_with_d2(self) -> None:
        result = analyze("direction: right\nA -> B")
        assert result.detected_language == "d2"
        assert result.confidence > 0.9

    def test_analyze_with_structurizr(self) -> None:
        result = analyze("workspace {\n    model {\n        user = person \"User\"\n    }\n}")
        assert result.detected_language == "structurizr"
        assert result.confidence > 0.9

    def test_analyze_with_vega_lite(self) -> None:
        result = analyze(
            '{"$schema": "https://vega-lite.github.io/schema/vega-lite/v5.json", "mark": "bar"}'
        )
        assert result.detected_language == "vega-lite"
        assert result.confidence > 0.9

    def test_analyze_with_bpmn(self) -> None:
        result = analyze('<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">')
        assert result.detected_language == "bpmn"
        assert result.confidence > 0.9

    def test_analyze_with_tikz(self) -> None:
        result = analyze("\\begin{tikzpicture}\n\\draw (0,0) -- (1,1);\n\\end{tikzpicture}")
        assert result.detected_language == "tikz"
        assert result.confidence > 0.9
