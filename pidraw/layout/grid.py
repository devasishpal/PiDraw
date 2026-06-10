from __future__ import annotations

import math

from pidraw.core.models import Diagram, LayoutType, Position, Viewport
from pidraw.layout.base import LayoutEngine, register_layout


@register_layout(LayoutType.GRID)
class GridLayout(LayoutEngine):
    def layout(self, diagram: Diagram) -> Diagram:
        layout = diagram.layout
        gap_x = layout.node_spacing if layout else 40
        gap_y = layout.layer_spacing if layout else 40
        padding = layout.padding if layout else 20

        nodes = diagram.all_nodes()
        if not nodes:
            return diagram

        cols = max(1, int(math.ceil(math.sqrt(len(nodes)))))
        x, y = padding, padding
        max_row_height = 0.0

        for i, node in enumerate(nodes):
            node_width = node.size.width if node.size else 120
            node_height = node.size.height if node.size else 50

            node.position = Position(x, y)
            max_row_height = max(max_row_height, node_height)

            if (i + 1) % cols == 0:
                x = padding
                y += max_row_height + gap_y
                max_row_height = 0.0
            else:
                x += node_width + gap_x

        # Always recompute viewport from actual positions
        min_x = min((n.position.x for n in nodes if n.position), default=0)
        min_y = min((n.position.y for n in nodes if n.position), default=0)
        max_x = max(
            (n.position.x + n.size.width for n in nodes if n.position and n.size), default=800
        )
        max_y = max(
            (n.position.y + n.size.height for n in nodes if n.position and n.size), default=y + 60
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
