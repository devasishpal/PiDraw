from __future__ import annotations

import re

from pidraw.core.converters.base import DiagramConverter, register_converter
from pidraw.core.models import (
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
)

_BOX_PATTERN = re.compile(r'[+][-]+[+]')
_LINE_PATTERN = re.compile(r'[|]')
_ARROW_PATTERN = re.compile(r'[-]+[>]|[-]+[v^]')

_NODE_LABEL = re.compile(r'[|]([^|]+)[|]')


@register_converter("ascii")
class ASCIIConverter(DiagramConverter):
    language = "ascii"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="ascii_diagram", title="ASCII Diagram")
        diagram.layout = Layout(layout_type=LayoutType.FLOW, direction="TB", node_spacing=40, layer_spacing=50)

        lines = source.strip().split("\n")
        connections: list[tuple[int, int]] = []
        node_counter = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            box_match = _BOX_PATTERN.search(line)
            if box_match:
                start = box_match.start()
                end = box_match.end()
                width = end - start - 2

                if i + 2 < len(lines):
                    mid_line = lines[i + 1]
                    if len(mid_line) > start + 1 and mid_line[start] == "|":
                        label_match = _NODE_LABEL.search(mid_line[start:end])
                        label_text = label_match.group(1) if label_match else f"Box{node_counter + 1}"
                        height = 1
                        j = i + 1
                        while j < len(lines) and "|" in lines[j][start:end] if len(lines[j]) > start else False:
                            height += 1
                            j += 1

                        box_label = label_text.strip()
                        nid = f"n{node_counter}"
                        node_counter += 1
                        node = Node(
                            id=nid,
                            label=Label(text=box_label),
                            shape=Shape(shape_type=ShapeType.RECTANGLE),
                            size=Size(max(len(box_label) * 8 + 20, width * 7), max(height * 18, 30)),
                            position=Position(x=start * 10, y=i * 20),
                        )
                        diagram.add_node(node)

                        # Look for connections
                        for k in range(max(0, i - 1), min(len(lines), i + height + 2)):
                            conn_line = lines[k]
                            arrow = _ARROW_PATTERN.search(conn_line)
                            if arrow:
                                conn_start = arrow.start()
                                conn_end = arrow.end()
                                # Find which box this connects to
                                for existing in diagram.all_nodes():
                                    if existing.id != nid and existing.position:
                                        ex, _ = existing.position.x / 10, existing.position.y / 20
                                        if abs(conn_end * 10 - ex) < 30 or abs(conn_start * 10 - ex) < 30:
                                            connections.append((nid, existing.id))

            i += 1

        for src_id, tgt_id in connections:
            if tgt_id not in [e.target for e in diagram.edges if e.source == src_id]:
                edge = Edge(
                    id=f"{src_id}->{tgt_id}",
                    source=src_id,
                    target=tgt_id,
                    style=None,
                )
                diagram.add_edge(edge)

        if node_counter == 0:
            diagram.add_node(Node(
                id="n0",
                label=Label(text="Diagram"),
                shape=Shape(shape_type=ShapeType.RECTANGLE),
                size=Size(200, 80),
                position=Position(20, 20),
            ))

        diagram.viewport = None

        return diagram
