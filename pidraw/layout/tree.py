from __future__ import annotations

from pidraw.core.models import Diagram, LayoutType, Node, Position, Viewport
from pidraw.layout.base import LayoutEngine, register_layout


@register_layout(LayoutType.TREE)
class TreeLayout(LayoutEngine):
    def layout(self, diagram: Diagram) -> Diagram:
        layout = diagram.layout
        gap_x = layout.node_spacing if layout else 80
        gap_y = layout.layer_spacing if layout else 60
        padding = layout.padding if layout else 20

        nodes = diagram.all_nodes()
        if not nodes:
            return diagram

        children_of: dict[str, list[str]] = {n.id: [] for n in nodes}
        for e in diagram.edges:
            if e.source in children_of:
                children_of[e.source].append(e.target)

        roots = [n.id for n in nodes if not any(e.target == n.id for e in diagram.edges)]
        if not roots:
            roots = [nodes[0].id]

        def layout_subtree(node_id: str, x: float, y: float) -> tuple[float, float, float]:
            node = diagram.get_node(node_id)
            if node is None:
                return (x, y, x)

            children = children_of.get(node_id, [])
            node_width = node.size.width if node.size else 120

            if not children:
                node.position = Position(x, y)
                return (x, x + node_width, x)

            child_x = x
            child_y = y + gap_y + (node.size.height if node.size else 50)
            midpoints: list[float] = []

            for child_id in children:
                left, right, mid = layout_subtree(child_id, child_x, child_y)
                child_x = right + gap_x
                midpoints.append(mid)

            tree_mid = sum(midpoints) / len(midpoints)
            node.position = Position(tree_mid - node_width / 2, y)
            return (min(x, midpoints[0]), max(child_x - gap_x, x + node_width), tree_mid)

        left, right, _ = layout_subtree(roots[0], padding, padding)

        for n in nodes:
            if n.position is None:
                n.position = Position(padding, padding)

        if diagram.viewport is None:
            max_x = max((n.position.x + n.size.width for n in nodes if n.position and n.size), default=right + padding)
            max_y = max((n.position.y + n.size.height for n in nodes if n.position and n.size), default=400)
            diagram.viewport = Viewport(width=max_x + padding, height=max_y + padding)

        return diagram
