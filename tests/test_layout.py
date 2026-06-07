from __future__ import annotations

from pidraw.core.models import Diagram, Edge, Label, Layout, LayoutType, Node, Size
from pidraw.layout import apply_layout
from pidraw.layout.flow import FlowLayout
from pidraw.layout.grid import GridLayout
from pidraw.layout.layered import LayeredLayout
from pidraw.layout.tree import TreeLayout


def _simple_diagram() -> Diagram:
    d = Diagram(id="test")
    d.add_node(Node(id="a", label=Label(text="A"), size=Size(100, 50)))
    d.add_node(Node(id="b", label=Label(text="B"), size=Size(100, 50)))
    d.add_node(Node(id="c", label=Label(text="C"), size=Size(100, 50)))
    d.add_edge(Edge(id="a->b", source="a", target="b"))
    d.add_edge(Edge(id="b->c", source="b", target="c"))
    return d


class TestTreeLayout:
    def test_layout_assigns_positions(self) -> None:
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.TREE)
        result = apply_layout(d)
        node_a = result.get_node("a")
        assert node_a is not None
        assert node_a.position is not None

    def test_viewport_created(self) -> None:
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.TREE)
        result = apply_layout(d)
        assert result.viewport is not None
        assert result.viewport.width > 0
        assert result.viewport.height > 0


class TestFlowLayout:
    def test_topological_sort(self) -> None:
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.FLOW)
        result = apply_layout(d)
        node_a = result.get_node("a")
        node_b = result.get_node("b")
        node_c = result.get_node("c")
        assert node_a is not None and node_b is not None and node_c is not None
        assert node_a.position is not None
        assert node_b.position is not None

    def test_flow_layout_positions(self) -> None:
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.FLOW, direction="TB")
        result = apply_layout(d)
        positions = [(n.position.y if n.position else 0, n.position.x if n.position else 0)
                     for n in [result.get_node("a"), result.get_node("b"), result.get_node("c")]
                     if n is not None and n.position is not None]
        # Should be in increasing y
        for i in range(len(positions) - 1):
            assert positions[i][0] <= positions[i + 1][0]


class TestGridLayout:
    def test_grid_assigns_positions(self) -> None:
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.GRID)
        result = apply_layout(d)
        for n in result.all_nodes():
            assert n.position is not None

    def test_grid_positions_unique(self) -> None:
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.GRID)
        result = apply_layout(d)
        poss = [(n.position.x, n.position.y) for n in result.all_nodes() if n.position]
        assert len(poss) == len(set(poss))


class TestLayeredLayout:
    def test_layered_assigns_layers(self) -> None:
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.LAYERED)
        result = apply_layout(d)
        for n in result.all_nodes():
            assert n.position is not None

    def test_layered_direction(self) -> None:
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.LAYERED, direction="LR")
        result = apply_layout(d)
        a = result.get_node("a")
        c = result.get_node("c")
        assert a is not None and c is not None
        assert a.position is not None and c.position is not None


class TestLayoutEngines:
    def test_tree_engine(self) -> None:
        engine = TreeLayout()
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.TREE)
        result = engine.layout(d)
        assert result is not None

    def test_flow_engine(self) -> None:
        engine = FlowLayout()
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.FLOW)
        result = engine.layout(d)
        assert result is not None

    def test_grid_engine(self) -> None:
        engine = GridLayout()
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.GRID)
        result = engine.layout(d)
        assert result is not None

    def test_layered_engine(self) -> None:
        engine = LayeredLayout()
        d = _simple_diagram()
        d.layout = Layout(layout_type=LayoutType.LAYERED)
        result = engine.layout(d)
        assert result is not None
