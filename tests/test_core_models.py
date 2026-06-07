from __future__ import annotations

from pidraw.core.models import (
    ArrowStyle,
    Diagram,
    Edge,
    EdgeStyle,
    FontWeight,
    Group,
    Label,
    Layout,
    LayoutType,
    Node,
    Position,
    Shape,
    ShapeType,
    Size,
    Style,
    TextAlign,
    Viewport,
)


class TestPosition:
    def test_default(self) -> None:
        p = Position()
        assert p.x == 0.0
        assert p.y == 0.0

    def test_add(self) -> None:
        assert (Position(1, 2) + Position(3, 4)) == Position(4, 6)

    def test_sub(self) -> None:
        assert (Position(5, 7) - Position(2, 3)) == Position(3, 4)

    def test_as_tuple(self) -> None:
        assert Position(10, 20).as_tuple() == (10.0, 20.0)


class TestSize:
    def test_default(self) -> None:
        s = Size()
        assert s.width == 0.0
        assert s.height == 0.0

    def test_as_tuple(self) -> None:
        assert Size(100, 50).as_tuple() == (100.0, 50.0)


class TestStyle:
    def test_default_values(self) -> None:
        s = Style()
        assert s.stroke_color == "#333333"
        assert s.fill_color == "#ffffff"
        assert s.font_size == 14.0

    def test_merge_both_none(self) -> None:
        s = Style.merge(None, None)
        assert s.stroke_color == "#333333"

    def test_merge_with_override(self) -> None:
        base = Style(stroke_color="#000", fill_color="#eeefff", corner_radius=8.0)
        override = Style(stroke_color="#e00")
        merged = Style.merge(base, override)
        assert merged.stroke_color == "#e00"
        assert merged.fill_color == "#eeefff"
        assert merged.corner_radius == 8.0


class TestNode:
    def test_create_minimal(self) -> None:
        n = Node(id="n1")
        assert n.id == "n1"
        assert n.label is None

    def test_create_with_label(self) -> None:
        n = Node(id="n1", label=Label(text="Hello"))
        assert n.label is not None
        assert n.label.text == "Hello"

    def test_create_with_shape(self) -> None:
        n = Node(id="n1", shape=Shape(shape_type=ShapeType.DIAMOND))
        assert n.shape is not None
        assert n.shape.shape_type == ShapeType.DIAMOND


class TestEdge:
    def test_create_minimal(self) -> None:
        e = Edge(id="e1", source="a", target="b")
        assert e.source == "a"
        assert e.target == "b"

    def test_with_label(self) -> None:
        e = Edge(id="e1", source="a", target="b", label=Label(text="edge"))
        assert e.label is not None
        assert e.label.text == "edge"


class TestDiagram:
    def test_empty_diagram(self) -> None:
        d = Diagram(id="test")
        assert len(d.all_nodes()) == 0
        assert len(d.all_edges()) == 0

    def test_add_node(self) -> None:
        d = Diagram(id="test")
        n = Node(id="n1")
        d.add_node(n)
        assert d.get_node("n1") == n
        assert len(d.all_nodes()) == 1

    def test_add_edge(self) -> None:
        d = Diagram(id="test")
        d.add_node(Node(id="a"))
        d.add_node(Node(id="b"))
        e = Edge(id="e1", source="a", target="b")
        d.add_edge(e)
        assert len(d.all_edges()) == 1

    def test_add_group(self) -> None:
        d = Diagram(id="test")
        g = Group(id="g1")
        d.add_group(g)
        assert len(d.groups) == 1


class TestEnums:
    def test_shape_types(self) -> None:
        assert ShapeType.RECTANGLE.value == "rectangle"
        assert ShapeType.DIAMOND.value == "diamond"
        assert ShapeType.CIRCLE.value == "circle"

    def test_edge_styles(self) -> None:
        assert EdgeStyle.SOLID.value == "solid"
        assert EdgeStyle.DASHED.value == "dashed"

    def test_arrow_styles(self) -> None:
        assert ArrowStyle.TRIANGLE_FILLED.value == "triangle_filled"
        assert ArrowStyle.NONE.value == "none"

    def test_text_align(self) -> None:
        assert TextAlign.CENTER.value == "center"

    def test_font_weight(self) -> None:
        assert FontWeight.BOLD.value == "bold"

    def test_layout_type(self) -> None:
        assert LayoutType.FLOW.value == "flow"
        assert LayoutType.LAYERED.value == "layered"
        assert LayoutType.TREE.value == "tree"
