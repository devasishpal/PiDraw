from __future__ import annotations

from pidraw.core.models import Diagram, LayoutType, Position, Viewport
from pidraw.layout.base import LayoutEngine, register_layout


@register_layout(LayoutType.LAYERED)
class LayeredLayout(LayoutEngine):
    def layout(self, diagram: Diagram) -> Diagram:
        layout = diagram.layout
        direction = layout.direction if layout else "TB"
        gap_x = layout.node_spacing if layout else 50
        gap_y = layout.layer_spacing if layout else 60
        padding = layout.padding if layout else 20

        nodes = diagram.all_nodes()
        if not nodes:
            return diagram

        layers = self._assign_layers(diagram)
        is_horizontal = direction in ("LR", "RL")
        max_dim_per_layer: list[float] = []

        for layer_idx, layer_ids in enumerate(layers):
            max_dim = 0.0
            x, y = padding, padding
            for nid in layer_ids:
                node = diagram.get_node(nid)
                if node is None:
                    continue
                nw = node.size.width if node.size else 120
                nh = node.size.height if node.size else 50
                dim = nh if is_horizontal else nw
                max_dim = max(max_dim, dim)

                if is_horizontal:
                    node.position = Position(
                        y=layer_idx * (max_dim + gap_y) + padding,
                        x=x,
                    )
                    x += (node.size.width if node.size else 120) + gap_x
                else:
                    node.position = Position(
                        x=layer_idx * (max_dim + gap_x) + padding,
                        y=y,
                    )
                    y += (node.size.height if node.size else 50) + gap_y

            max_dim_per_layer.append(max_dim)

        for n in nodes:
            if n.position is None:
                n.position = Position(padding, padding)

        # Always recompute viewport from actual positions (layout engines may have overridden converter positions)
        min_x = min((n.position.x for n in nodes if n.position), default=0)
        min_y = min((n.position.y for n in nodes if n.position), default=0)
        max_x = max(
            (n.position.x + n.size.width for n in nodes if n.position and n.size), default=800
        )
        max_y = max(
            (n.position.y + n.size.height for n in nodes if n.position and n.size), default=600
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

    def _assign_layers(self, diagram: Diagram) -> list[list[str]]:
        nodes = diagram.all_nodes()
        if not nodes:
            return []

        edges = diagram.edges
        outgoing: dict[str, list[str]] = {n.id: [] for n in nodes}
        incoming: dict[str, list[str]] = {n.id: [] for n in nodes}

        for e in edges:
            if e.source in outgoing and e.target in outgoing:
                outgoing[e.source].append(e.target)
                incoming[e.target].append(e.source)

        layers: list[list[str]] = []
        assigned: set[str] = set()
        remaining = {n.id for n in nodes}

        while remaining:
            layer = [
                nid for nid in remaining if all(pred in assigned for pred in incoming.get(nid, []))
            ]
            if not layer:
                candidates = sorted(remaining)
                layer = [candidates[0]]

            layers.append(layer)
            assigned.update(layer)
            remaining -= set(layer)

        return layers
