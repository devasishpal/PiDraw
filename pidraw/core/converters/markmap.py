from __future__ import annotations

from pidraw.core.converters.base import DiagramConverter, register_converter
from pidraw.core.models import (
    Diagram,
    Edge,
    FontWeight,
    Label,
    Layout,
    LayoutType,
    Node,
    Shape,
    ShapeType,
    Size,
    Style,
)


@register_converter("markmap")
class MarkmapConverter(DiagramConverter):
    language = "markmap"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="markmap_diagram", title="Markmap Mindmap")
        diagram.layout = Layout(
            layout_type=LayoutType.TREE,
            direction="TB",
            node_spacing=80,
            layer_spacing=70,
            padding=40,
        )
        diagram.style = Style(
            font_family="sans-serif",
            font_size=14,
            fill_color="#ffffff",
            stroke_color="#4a90d9",
            text_color="#333333",
            stroke_width=1.5,
        )

        lines = source.strip().split("\n")
        heading_stack: list[tuple[int, Node]] = []
        node_counter = 0
        edges: list[tuple[str, str]] = []

        root = Node(
            id="root",
            label=Label(text="Mindmap"),
            shape=Shape(shape_type=ShapeType.ROUNDED_RECTANGLE),
            size=Size(160, 48),
            style=Style(
                fill_color="#1a3a5c",
                text_color="#ffffff",
                font_size=20,
                font_weight=FontWeight.BOLD,
                font_family="sans-serif",
                stroke_color="#1a3a5c",
                stroke_width=2,
            ),
        )
        diagram.add_node(root)
        heading_stack.append((0, root))

        color_palette = [
            "#4a90d9",
            "#50b86c",
            "#e8a838",
            "#d96060",
            "#8e6cc0",
            "#3fb4b4",
            "#d97a3a",
            "#b45f8a",
        ]

        level_font_sizes = {1: 18, 2: 15, 3: 13, 4: 12, 5: 11, 6: 11}
        level_heights = {1: 50, 2: 40, 3: 36, 4: 34, 5: 32, 6: 32}

        for line in lines:
            if not line.strip():
                continue

            stripped = line.rstrip()
            level = 0
            for ch in stripped:
                if ch == "#":
                    level += 1
                else:
                    break

            if level == 0:
                continue

            title = stripped[level:].strip()
            title = title.lstrip("#").strip()
            if not title:
                continue

            nid = f"n{node_counter}"
            node_counter += 1

            ci = min(level - 1, len(color_palette) - 1)
            depth_color = color_palette[ci]
            fs = level_font_sizes.get(level, 11)
            nh = level_heights.get(level, 32)
            nw = max(len(title) * int(fs * 0.7) + 40, 80)

            node = Node(
                id=nid,
                label=Label(text=title),
                shape=Shape(shape_type=ShapeType.ROUNDED_RECTANGLE),
                size=Size(nw, nh),
                style=Style(
                    fill_color=depth_color,
                    text_color="#ffffff",
                    font_size=fs,
                    font_weight=FontWeight.BOLD if level <= 2 else FontWeight.NORMAL,
                    font_family="sans-serif",
                    stroke_color=depth_color,
                    stroke_width=1.5,
                    padding=12,
                ),
            )
            diagram.add_node(node)

            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            if heading_stack:
                parent_node = heading_stack[-1][1]
                edges.append((parent_node.id, nid))

            heading_stack.append((level, node))

        for src_id, tgt_id in edges:
            edge = Edge(
                id=f"{src_id}->{tgt_id}",
                source=src_id,
                target=tgt_id,
                style=Style(
                    stroke_color="#8899aa",
                    stroke_width=2,
                ),
            )
            diagram.add_edge(edge)

        return diagram
