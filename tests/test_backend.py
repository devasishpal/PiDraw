from __future__ import annotations

from pidraw.backend.svg import SvgBackend
from pidraw.core.models import (
    ArrowStyle,
    Diagram,
    Edge,
    Label,
    Layout,
    LayoutType,
    Node,
    Position,
    Shape,
    ShapeType,
    Size,
    Style,
    Viewport,
)


def _simple_diagram() -> Diagram:
    d = Diagram(id="test", viewport=Viewport(400, 300))
    d.layout = Layout(layout_type=LayoutType.NONE)
    d.add_node(
        Node(
            id="a",
            label=Label(text="Node A"),
            shape=Shape(shape_type=ShapeType.RECTANGLE),
            position=Position(20, 20),
            size=Size(120, 50),
        )
    )
    d.add_node(
        Node(
            id="b",
            label=Label(text="Node B"),
            shape=Shape(shape_type=ShapeType.ROUNDED_RECTANGLE),
            position=Position(200, 100),
            size=Size(140, 60),
        )
    )
    d.add_edge(
        Edge(
            id="a->b",
            source="a",
            target="b",
            label=Label(text="connects"),
            style=Style(arrow_end=ArrowStyle.TRIANGLE_FILLED),
        )
    )
    return d


class TestSvgBackend:
    def test_render_basic(self) -> None:
        backend = SvgBackend()
        svg = backend.render(_simple_diagram())
        assert svg.startswith("<?xml")
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_render_valid_xml(self) -> None:
        backend = SvgBackend()
        svg = backend.render(_simple_diagram())
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_render_contains_nodes(self) -> None:
        backend = SvgBackend()
        svg = backend.render(_simple_diagram())
        assert 'id="node-a"' in svg
        assert 'id="node-b"' in svg

    def test_render_contains_edges(self) -> None:
        backend = SvgBackend()
        svg = backend.render(_simple_diagram())
        assert 'id="edge-a->b"' in svg or 'id="edge-a-&gt;b"' in svg

    def test_render_contains_labels(self) -> None:
        backend = SvgBackend()
        svg = backend.render(_simple_diagram())
        assert "Node A" in svg
        assert "Node B" in svg

    def test_render_edge_label(self) -> None:
        backend = SvgBackend()
        svg = backend.render(_simple_diagram())
        assert "connects" in svg

    def test_render_with_markers(self) -> None:
        backend = SvgBackend()
        svg = backend.render(_simple_diagram())
        assert "pidraw-arrow-triangle_filled" in svg

    def test_empty_diagram(self) -> None:
        backend = SvgBackend()
        d = Diagram(id="empty", viewport=Viewport(100, 100))
        svg = backend.render(d)
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_diamond_node(self) -> None:
        backend = SvgBackend()
        d = Diagram(id="d", viewport=Viewport(200, 200))
        d.add_node(
            Node(
                id="d1",
                label=Label(text="Diamond"),
                shape=Shape(shape_type=ShapeType.DIAMOND),
                position=Position(50, 50),
                size=Size(100, 80),
            )
        )
        svg = backend.render(d)
        assert "Diamond" in svg

    def test_render_with_shadow(self) -> None:
        backend = SvgBackend()
        d = Diagram(id="s", viewport=Viewport(200, 200))
        d.add_node(
            Node(
                id="s1",
                label=Label(text="Shadow"),
                shape=Shape(shape_type=ShapeType.RECTANGLE),
                position=Position(30, 30),
                size=Size(100, 50),
                style=Style(shadow=True),
            )
        )
        svg = backend.render(d)
        assert "<svg" in svg
