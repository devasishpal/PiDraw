from __future__ import annotations

from pidraw.core.models import Diagram, Label, Node, Position, Size, Viewport
from pidraw.pipeline import render_native


class TestExportPipeline:
    def test_pipeline_with_mermaid_source(self) -> None:
        source = "graph TD\n    A-->B\n    B-->C\n"
        svg = render_native(source, "mermaid")
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_pipeline_with_plantuml_source(self) -> None:
        source = "@startuml\nA -> B : hello\n@enduml\n"
        svg = render_native(source, "plantuml")
        assert "<svg" in svg

    def test_pipeline_with_graphviz_source(self) -> None:
        source = "digraph G { a -> b; b -> c; }"
        svg = render_native(source, "graphviz")
        assert "<svg" in svg

    def test_pipeline_with_d2_source(self) -> None:
        source = "a -> b\nb -> c\n"
        svg = render_native(source, "d2")
        assert "<svg" in svg

    def test_pipeline_with_dark_theme(self) -> None:
        source = "graph TD\n    A-->B\n"
        svg = render_native(source, "mermaid", theme="dark")
        assert "<svg" in svg

    def test_pipeline_with_professional_theme(self) -> None:
        source = "graph TD\n    A-->B\n"
        svg = render_native(source, "mermaid", theme="professional")
        assert "<svg" in svg

    def test_pipeline_with_blueprint_theme(self) -> None:
        source = "graph TD\n    A-->B\n"
        svg = render_native(source, "mermaid", theme="blueprint")
        assert "<svg" in svg

    def test_pipeline_from_diagram(self) -> None:
        from pidraw.pipeline import render_native_from_diagram
        d = Diagram(id="test", viewport=Viewport(300, 200))
        d.add_node(Node(
            id="n1",
            label=Label(text="Hello"),
            position=Position(10, 10),
            size=Size(100, 50),
        ))
        svg = render_native_from_diagram(d)
        assert "<svg" in svg

    def test_pipeline_with_optimize(self) -> None:
        source = "graph TD\n    A-->B\n"
        svg = render_native(source, "mermaid", optimize=True)
        assert "<svg" in svg

    def test_unknown_language_raises(self) -> None:
        import pytest
        with pytest.raises(ValueError, match="No converter"):
            render_native("anything", "unknown_lang")

    def test_ascii_converter(self) -> None:
        source = "+---+ \n| A | \n+---+ \n  |   \n+---+ \n| B | \n+---+ \n"
        svg = render_native(source, "ascii")
        assert "<svg" in svg
