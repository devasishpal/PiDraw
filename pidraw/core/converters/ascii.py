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
_ARROW_RIGHT = re.compile(r'[-]+[>]')
_ARROW_LEFT = re.compile(r'[<][-]+')
_ARROW_ANY = re.compile(r'<[-]+|[-]+>')

_NODE_LABEL = re.compile(r'[|]([^|]+)[|]')


def _find_all_boxes(line: str) -> list[tuple[int, int]]:
    boxes = []
    pos = 0
    while True:
        m = _BOX_PATTERN.search(line, pos)
        if not m:
            break
        boxes.append((m.start(), m.end()))
        pos = m.end()
    return boxes


@register_converter("ascii")
class ASCIIConverter(DiagramConverter):
    language = "ascii"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="ascii_diagram", title="ASCII Diagram")
        diagram.layout = Layout(layout_type=LayoutType.FLOW, direction="TB", node_spacing=40, layer_spacing=50)

        lines = source.strip().split("\n")
        connections: list[tuple[str, str]] = []
        node_counter = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            boxes = _find_all_boxes(line)
            for start, end in boxes:
                width = end - start - 2

                if i + 2 < len(lines):
                    mid_line = lines[i + 1]
                    if len(mid_line) > start + 1 and mid_line[start] == "|":
                        # Scan all content lines for first non-empty label
                        box_label = ""
                        height = 1
                        j = i + 1
                        while j < len(lines) and len(lines[j]) > start and "|" in lines[j][start:end]:
                            lm = _NODE_LABEL.search(lines[j][start:end])
                            if lm:
                                candidate = lm.group(1).strip()
                                if candidate and not box_label:
                                    box_label = candidate
                            height += 1
                            j += 1

                        if not box_label:
                            box_label = f"Box{node_counter + 1}"

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

            i += 1

        # Second pass: find connections (all boxes already parsed)
        for i, line in enumerate(lines):
            for arrow in _ARROW_ANY.finditer(line):
                arrow_start_col = arrow.start()
                arrow_text = arrow.group()
                is_right = ">" in arrow_text
                # Find nearest box to arrow head and tail
                src_node = None
                tgt_node = None
                for node in diagram.all_nodes():
                    if node.position is None:
                        continue
                    node_col = node.position.x / 10
                    node_row = node.position.y / 20
                    if abs(node_row - i) > 2:
                        continue
                    if is_right:
                        # src is left of arrow, tgt is right
                        if node_col < arrow_start_col:
                            if src_node is None or node_col > src_node.position.x / 10:
                                src_node = node
                        elif node_col > arrow.end():
                            if tgt_node is None or node_col < tgt_node.position.x / 10:
                                tgt_node = node
                    else:
                        # <-- left arrow: src is right, tgt is left
                        if node_col > arrow.end():
                            if src_node is None or node_col < src_node.position.x / 10:
                                src_node = node
                        elif node_col < arrow_start_col:
                            if tgt_node is None or node_col > tgt_node.position.x / 10:
                                tgt_node = node
                if src_node and tgt_node:
                    connections.append((src_node.id, tgt_node.id))

        for src_id, tgt_id in connections:
            if src_id != tgt_id and tgt_id not in [e.target for e in diagram.edges if e.source == src_id]:
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
