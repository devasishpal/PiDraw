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

        if diagram.viewport is None:
            max_x = max((n.position.x + n.size.width for n in nodes if n.position and n.size), default=800)
            max_y = max((n.position.y + n.size.height for n in nodes if n.position and n.size), default=y + 60)
            diagram.viewport = Viewport(width=max_x + padding, height=max_y + padding)

        return diagram
