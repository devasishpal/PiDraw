"""Tests for diagram language detection."""

from pidraw.detector import detect, detect_language
from pidraw.models import DetectionResult


class TestDetect:
    def test_mermaid_graph_td(self) -> None:
        assert detect("graph TD\n    A-->B") == "mermaid"

    def test_mermaid_graph_lr(self) -> None:
        assert detect("graph LR\n    A-->B") == "mermaid"

    def test_mermaid_flowchart(self) -> None:
        assert detect("flowchart TD\n    A-->B") == "mermaid"

    def test_mermaid_sequencediagram(self) -> None:
        assert detect("sequenceDiagram\n    A->>B: Hello") == "mermaid"

    def test_mermaid_classdiagram(self) -> None:
        assert detect("classDiagram\n    class Animal") == "mermaid"

    def test_mermaid_statediagram(self) -> None:
        assert detect("stateDiagram\n    [*] --> Idle") == "mermaid"

    def test_mermaid_erdiagram(self) -> None:
        assert detect("erDiagram\n    CUSTOMER ||--o| ORDER : places") == "mermaid"

    def test_mermaid_gantt(self) -> None:
        assert detect("gantt\n    title A Gantt Diagram") == "mermaid"

    def test_mermaid_pie(self) -> None:
        assert detect("pie\n    title Pie Chart") == "mermaid"

    def test_mermaid_journey(self) -> None:
        assert detect("journey\n    title My journey") == "mermaid"

    def test_mermaid_mindmap(self) -> None:
        assert detect("mindmap\n    root((Root))") == "mermaid"

    def test_mermaid_timeline(self) -> None:
        assert detect("timeline\n    title Timeline") == "mermaid"

    def test_mermaid_gitgraph(self) -> None:
        assert detect("gitgraph\n    commit") == "mermaid"

    def test_plantuml_startuml(self) -> None:
        assert detect("@startuml\nAlice -> Bob: hello\n@enduml") == "plantuml"

    def test_plantuml_startuml_with_block(self) -> None:
        assert detect("@startuml\nparticipant User\n@enduml") == "plantuml"

    def test_plantuml_startmindmap(self) -> None:
        assert detect("@startmindmap\n* Root\n@endmindmap") == "plantuml"

    def test_plantuml_startgantt(self) -> None:
        assert detect("@startgantt\n[Task1] lasts 10 days\n@endgantt") == "plantuml"

    def test_plantuml_startsalt(self) -> None:
        assert detect("@startsalt\n{\nJust a text\n}\n@endsalt") == "plantuml"

    def test_plantuml_startjson(self) -> None:
        assert detect("@startjson\n{\"key\": \"value\"}\n@endjson") == "plantuml"

    def test_plantuml_startyaml(self) -> None:
        assert detect("@startyaml\nkey: value\n@endyaml") == "plantuml"

    def test_plantuml_startwbs(self) -> None:
        assert detect("@startwbs\n* Project\n@endwbs") == "plantuml"

    def test_plantuml_numeric_start(self) -> None:
        assert detect("@start99\nsomething\n@end99") == "plantuml"

    def test_graphviz_digraph(self) -> None:
        assert detect("digraph G {\n    A -> B;\n}") == "graphviz"

    def test_graphviz_strict_digraph(self) -> None:
        assert detect("strict digraph G {\n    A -> B;\n}") == "graphviz"

    def test_graphviz_graph(self) -> None:
        assert detect("graph G {\n    A -- B;\n}") == "graphviz"

    def test_graphviz_strict_graph(self) -> None:
        assert detect("strict graph G {\n    A -- B;\n}") == "graphviz"

    def test_graphviz_digraph_no_name(self) -> None:
        assert detect("digraph {\n    A -> B;\n}") == "graphviz"

    def test_graphviz_graph_no_name(self) -> None:
        assert detect("graph {\n    A -- B;\n}") == "graphviz"

    def test_graphviz_strict_digraph_no_name(self) -> None:
        assert detect("strict digraph {\n    A -> B;\n}") == "graphviz"

    def test_graphviz_strict_graph_no_name(self) -> None:
        assert detect("strict graph {\n    A -- B;\n}") == "graphviz"

    def test_d2_direction_right(self) -> None:
        assert detect("direction: right\nA -> B") == "d2"

    def test_d2_shape(self) -> None:
        assert detect("x: {\n    shape: circle\n}") == "d2"

    def test_d2_direction_up(self) -> None:
        assert detect("direction: up") == "d2"

    def test_d2_simple_arrow(self) -> None:
        assert detect("a -> b") == "d2"

    def test_d2_styled_arrow(self) -> None:
        assert detect("x -> y: hello") == "d2"

    def test_d2_style_block(self) -> None:
        assert detect("style: {\n    stroke: red\n}") == "d2"

    def test_d2_container(self) -> None:
        assert detect("mycontainer: {\n    a -> b\n}") == "d2"

    def test_d2_bi_arrow(self) -> None:
        assert detect("a <-> b") == "d2"

    def test_ascii_plus_minus(self) -> None:
        assert detect("+--+\n|  |\n+--+") == "ascii"

    def test_ascii_dot_line(self) -> None:
        assert detect(".-.\n| |\n.-.") == "ascii"

    def test_ascii_pipe(self) -> None:
        assert detect("| Column1 | Column2 |") == "ascii"

    def test_empty_string(self) -> None:
        assert detect("") == "unknown"

    def test_whitespace_only(self) -> None:
        assert detect("   \n  \n  ") == "unknown"

    def test_gibberish(self) -> None:
        assert detect("foobar\nbazqux") == "unknown"


class TestDetectLanguage:
    def test_returns_detection_result(self) -> None:
        result = detect_language("graph TD\n    A-->B")
        assert isinstance(result, DetectionResult)

    def test_mermaid_confidence(self) -> None:
        result = detect_language("graph TD\n    A-->B")
        assert result.language.value == "mermaid"
        assert result.confidence >= 0.9

    def test_plantuml_high_confidence(self) -> None:
        result = detect_language("@startuml\nA-->B\n@enduml")
        assert result.language.value == "plantuml"
        assert result.confidence >= 0.95

    def test_unknown_zero_confidence(self) -> None:
        result = detect_language("")
        assert result.language.value == "unknown"
        assert result.confidence == 0.0

    def test_confidence_tikz(self) -> None:
        result = detect_language("\\begin{tikzpicture}\n\\draw (0,0);\n\\end{tikzpicture}")
        assert result.language.value == "tikz"
        assert result.confidence >= 0.95

    def test_confidence_vega(self) -> None:
        result = detect_language('{"$schema": "https://vega.github.io/schema/vega/v5.json"}')
        assert result.language.value == "vega"
        assert result.confidence >= 0.9

    def test_confidence_vega_lite(self) -> None:
        result = detect_language('{"$schema": "https://vega-lite.github.io/schema/vega-lite/v5.json"}')
        assert result.language.value == "vega-lite"
        assert result.confidence >= 0.95

    def test_confidence_structurizr(self) -> None:
        result = detect_language("workspace {\n    model {\n    }\n}")
        assert result.language.value == "structurizr"
        assert result.confidence >= 0.95

    def test_confidence_bpmn(self) -> None:
        result = detect_language('<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"/>')
        assert result.language.value == "bpmn"
        assert result.confidence >= 0.95

    def test_confidence_wavedrom(self) -> None:
        result = detect_language('{"signal": [{"name": "clk", "wave": "p...."}]}')
        assert result.language.value == "wavedrom"
        assert result.confidence >= 0.95

    def test_confidence_excalidraw(self) -> None:
        result = detect_language('{"type": "excalidraw", "elements": []}')
        assert result.language.value == "excalidraw"
        assert result.confidence >= 0.95

    def test_highest_confidence_wins(self) -> None:
        result = detect_language("graph TD\n    A-->B")
        assert result.language.value == "mermaid"
        assert result.confidence >= 0.95

    def test_matched_pattern_not_none(self) -> None:
        result = detect_language("graph TD\n    A-->B")
        assert result.matched_pattern is not None

    def test_zero_confidence_whitespace_only(self) -> None:
        result = detect_language("   \n  ")
        assert result.language.value == "unknown"
        assert result.confidence == 0.0
