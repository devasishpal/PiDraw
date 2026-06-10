from __future__ import annotations

from pidraw.core.models import Diagram, LayoutType, Node, Position, Viewport
from pidraw.layout.base import LayoutEngine, register_layout


@register_layout(LayoutType.FLOW)
class FlowLayout(LayoutEngine):
    def layout(self, diagram: Diagram) -> Diagram:
        layout = diagram.layout
        direction = layout.direction if layout else "TB"
        gap_x = layout.node_spacing if layout else 40
        gap_y = layout.layer_spacing if layout else 50
        padding = layout.padding if layout else 20

        nodes = diagram.all_nodes()
        if not nodes:
            return diagram

        sorted_nodes = self._topological_sort(diagram)
        x, y = padding, padding
        is_horizontal = direction in ("LR", "RL")

        for node in sorted_nodes:
            node_width = node.size.width if node.size else 120
            node_height = node.size.height if node.size else 50
            node.position = Position(x, y)

            if is_horizontal:
                x += node_width + gap_x
            else:
                y += node_height + gap_y

        # Always recompute viewport from actual positions
        min_x = min((n.position.x for n in nodes if n.position), default=0)
        min_y = min((n.position.y for n in nodes if n.position), default=0)
        max_x = max(
            (n.position.x + n.size.width for n in nodes if n.position and n.size),
            default=x + padding,
        )
        max_y = max(
            (n.position.y + n.size.height for n in nodes if n.position and n.size),
            default=y + padding,
        )
        cw = max_x - min_x
        ch = max_y - min_y
        pad = max(padding * 2, cw * 0.15, ch * 0.15)
        diagram.viewport = Viewport(
            x=min_x - pad,
            y=min_y - pad,
            width=cw + pad * 2,
            height=ch + pad * 2,
        )

        return diagram

    def _topological_sort(self, diagram: Diagram) -> list[Node]:
        nodes = diagram.all_nodes()
        if not nodes:
            return []
        edges = diagram.edges

        in_degree: dict[str, int] = {n.id: 0 for n in nodes}
        adj: dict[str, list[str]] = {n.id: [] for n in nodes}
        for e in edges:
            if e.source in adj and e.target in adj:
                adj[e.source].append(e.target)
                in_degree[e.target] = in_degree.get(e.target, 0) + 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        if not queue:
            queue = [nodes[0].id]

        sorted_ids: list[str] = []
        while queue:
            nid = queue.pop(0)
            sorted_ids.append(nid)
            for child in adj.get(nid, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        remaining = [n.id for n in nodes if n.id not in sorted_ids]
        sorted_ids.extend(remaining)

        node_map = {n.id: n for n in nodes}
        result = [node_map[nid] for nid in sorted_ids if nid in node_map]
        return result
