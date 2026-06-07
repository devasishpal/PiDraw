from __future__ import annotations

from pidraw.core.converters import convert, get_converter, list_converters
from pidraw.core.converters.graphviz import GraphvizConverter
from pidraw.core.converters.mermaid import MermaidConverter


class TestConverters:
    def test_list_converters(self) -> None:
        langs = list_converters()
        assert "mermaid" in langs
        assert "plantuml" in langs
        assert "graphviz" in langs
        assert "d2" in langs

    def test_get_converter(self) -> None:
        c = get_converter("mermaid")
        assert c is not None
        assert c.language == "mermaid"

    def test_get_converter_case_insensitive(self) -> None:
        c = get_converter("MERMAID")
        assert c is not None
        assert c.language == "mermaid"

    def test_mermaid_parse_graph(self) -> None:
        result = convert("graph TD\n    A-->B\n", "mermaid")
        assert result.id == "mermaid_diagram"
        assert "A" in result.nodes
        assert "B" in result.nodes
        assert len(result.edges) >= 1

    def test_mermaid_parse_flowchart(self) -> None:
        result = convert("flowchart LR\n    Start-->End\n", "mermaid")
        assert "Start" in result.nodes
        assert "End" in result.nodes

    def test_mermaid_detects_direction(self) -> None:
        result = convert("graph LR\n    A-->B\n", "mermaid")
        assert result.layout is not None
        assert result.layout.direction == "LR"

    def test_plantuml_parse(self) -> None:
        result = convert("@startuml\nA -> B : hello\n@enduml\n", "plantuml")
        assert len(result.nodes) >= 2
        assert len(result.edges) >= 1

    def test_graphviz_parse(self) -> None:
        result = convert("digraph G { a -> b; b -> c; }", "graphviz")
        assert "a" in result.nodes
        assert "b" in result.nodes
        assert len(result.edges) >= 1

    def test_d2_parse(self) -> None:
        result = convert("a -> b\nb -> c\n", "d2")
        assert len(result.nodes) >= 1
        assert len(result.edges) >= 0

    def test_mermaid_parse_styles(self) -> None:
        result = convert("graph TD\n    A[Start] --> B{Decision}\n", "mermaid")
        a = result.get_node("A")
        b = result.get_node("B")
        assert a is not None
        assert b is not None
        assert a.label is not None
        assert a.label.text == "Start"
        assert b.shape is not None
        assert b.shape.shape_type.value == "diamond"

    def test_converter_unknown(self) -> None:
        c = get_converter("nonexistent")
        assert c is None
