from __future__ import annotations

import re

from pidraw.core.converters.base import DiagramConverter, register_converter
from pidraw.core.models import (
    ArrowStyle,
    Diagram,
    Edge,
    EdgeStyle,
    Label,
    Layout,
    LayoutType,
    Node,
    Position,
    Shape,
    ShapeType,
    Size,
    Style,
)

_NODE_PATTERN = re.compile(
    r"(\w[\w\d_]*)"           # id
    r"(?:\[([^\]]*)\])?"       # [label] rectangle
    r"(?:\{([^}]*)\})?"        # {label} rhombus
    r"(?:\(([^)]*)\))?"        # (label) rounded rect
    r"(?:\"([^\"]*)\")?"       # "label"
    r'(?:\<\[([^\]]*)\]\>)?'   # <[label]> hexagon
    r'(?:\(\(([^)]*)\)\))?'    # ((label)) circle
    r"(?:\>([^>]*)\]?)?"       # >label] async
)

_EDGE_PATTERN = re.compile(
    r"(\w[\w\d_]*)"                      # source
    r"(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\(\([^)]*\)\)|<\[[^\]]*\]>)?\s*"  # optional node shape
    r"((?:[-=.]*[-=>]+|<-[-=.]*|<-|->|<->|==|--)[-\.=]*[-=>]*)"  # arrow
    r"\s*"                               # space
    r"(\w[\w\d_]*)"                      # target
    r"(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\(\([^)]*\)\)|<\[[^\]]*\]>)?"  # optional node shape
)

_DIRECTION_PATTERN = re.compile(r"(?:^|\n)\s*(graph|flowchart)\s+(TB|BT|LR|RL)", re.IGNORECASE)
_SUBGRAPH_PATTERN = re.compile(r"subgraph\s+(\w[\w\d_]*)\s*([^\n]*)")
_STYLE_PATTERN = re.compile(
    r"style\s+(\w[\w\d_]*)\s+"
    r"(fill|stroke|color|stroke-width|stroke-dasharray)"
    r"(?::|=)(#[0-9a-fA-F]{3,8}|\w+)"
    r"(?:\s*,\s*(fill|stroke|color|stroke-width|stroke-dasharray)"
    r"(?::|=)(#[0-9a-fA-F]{3,8}|\w+))*",
    re.IGNORECASE,
)
_STYLE_PROP = re.compile(r"(fill|stroke|color|stroke-width|stroke-dasharray)(?::|=)(#[0-9a-fA-F]{3,8}|\w+)", re.IGNORECASE)


@register_converter("mermaid")
class MermaidConverter(DiagramConverter):
    language = "mermaid"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="mermaid_diagram", title="Mermaid Diagram")
        diagram.layout = Layout(layout_type=LayoutType.LAYERED, direction="TB", node_spacing=40, layer_spacing=60)

        direction_match = _DIRECTION_PATTERN.search(source)
        if direction_match:
            diagram.layout.direction = direction_match.group(2).upper()

        lines = source.strip().split("\n")
        node_styles: dict[str, dict[str, str]] = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("%%") or re.match(r"^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram)", line, re.IGNORECASE):
                continue
            if line.startswith("subgraph "):
                continue
            if line.startswith("end"):
                continue

            # Parse style directives: style A fill:#4CAF50,color:#fff
            if line.lower().startswith("style "):
                parts = line.split(None, 2)
                if len(parts) >= 2:
                    nid = parts[1]
                    props_str = parts[2] if len(parts) > 2 else ""
                    props = {}
                    for m in _STYLE_PROP.finditer(props_str):
                        k, v = m.group(1).lower(), m.group(2)
                        props[k] = v
                    if props:
                        node_styles[nid] = props
                continue

            edge_match = _EDGE_PATTERN.match(line)
            if edge_match:
                src_id, arrow_str, tgt_id = edge_match.groups()
                edge_style, arrow_start, arrow_end = self._parse_arrow_style(arrow_str)

                # Extract node decorations from the full line
                for nid, raw in ((src_id, src_id), (tgt_id, tgt_id)):
                    # Find the actual position of this node in the line
                    idx = line.find(nid)
                    if idx >= 0:
                        remainder = line[idx + len(nid):]
                        shape_type, label_text = self._parse_node_decoration(remainder)
                    else:
                        shape_type, label_text = ShapeType.RECTANGLE, nid

                    if nid not in diagram.nodes:
                        tw = max(len(label_text) * 8, 60)
                        node = Node(
                            id=nid,
                            label=Label(text=label_text),
                            shape=Shape(shape_type=shape_type),
                            size=Size(tw + 40, 50),
                        )
                        diagram.add_node(node)

                label_match = re.search(r"\|([^|]+)\|", line)
                edge_label = None
                if label_match:
                    edge_label = Label(text=label_match.group(1))

                edge = Edge(
                    id=f"{src_id}->{tgt_id}",
                    source=src_id,
                    target=tgt_id,
                    label=edge_label,
                    style=Style(
                        arrow_end=arrow_end,
                        arrow_start=arrow_start,
                        stroke_style=edge_style,
                    ),
                )
                diagram.add_edge(edge)
                continue

            node_match = _NODE_PATTERN.match(line)
            if node_match:
                nid = node_match.group(1)
                shape_type = ShapeType.RECTANGLE
                label_text = nid

                if node_match.group(2) is not None:
                    label_text = node_match.group(2)
                    shape_type = ShapeType.ROUNDED_RECTANGLE if line.strip().startswith("(") else ShapeType.RECTANGLE
                elif node_match.group(3) is not None:
                    label_text = node_match.group(3)
                    shape_type = ShapeType.DIAMOND
                elif node_match.group(4) is not None:
                    label_text = node_match.group(4)
                    shape_type = ShapeType.ROUNDED_RECTANGLE
                elif node_match.group(5) is not None:
                    label_text = node_match.group(5)
                elif node_match.group(6) is not None:
                    label_text = node_match.group(6)
                    shape_type = ShapeType.HEXAGON
                elif node_match.group(7) is not None:
                    label_text = node_match.group(7)
                    shape_type = ShapeType.DOUBLE_CIRCLE

                if nid not in diagram.nodes:
                    tw = max(len(label_text) * 8, 60)
                    node = Node(
                        id=nid,
                        label=Label(text=label_text),
                        shape=Shape(shape_type=shape_type),
                        size=Size(tw + 40, 50),
                    )
                    diagram.add_node(node)

        # Apply parsed style directives to nodes
        for nid, props in node_styles.items():
            node = diagram.get_node(nid)
            if node is not None:
                fill = props.get("fill")
                stroke = props.get("stroke")
                txt_color = props.get("color")
                if fill or stroke or txt_color:
                    node.style = Style(
                        fill_color=fill or Style().fill_color,
                        stroke_color=stroke or Style().stroke_color,
                        text_color=txt_color or Style().text_color,
                    )

        self._ensure_positions(diagram)
        return diagram

    def _parse_arrow_style(self, arrow_str: str) -> tuple[EdgeStyle, ArrowStyle, ArrowStyle]:
        edge_style = EdgeStyle.SOLID
        arrow_end = ArrowStyle.TRIANGLE_FILLED
        arrow_start = ArrowStyle.NONE

        if "==" in arrow_str or "===" in arrow_str:
            edge_style = EdgeStyle.BOLD
        elif "-.-" in arrow_str or "-.." in arrow_str:
            edge_style = EdgeStyle.DOTTED
        elif "-.-" in arrow_str or ".-" in arrow_str:
            edge_style = EdgeStyle.DASHED

        if arrow_str.startswith("<->") or arrow_str.startswith("<==>"):
            arrow_start = ArrowStyle.TRIANGLE_FILLED
            arrow_end = ArrowStyle.TRIANGLE_FILLED
        elif arrow_str.startswith("<-"):
            arrow_start = ArrowStyle.TRIANGLE_FILLED
        elif arrow_str.endswith("-->"):
            arrow_end = ArrowStyle.OPEN
        elif arrow_str.endswith("o--"):
            arrow_end = ArrowStyle.CIRCLE
        elif arrow_str.endswith("x--"):
            arrow_end = ArrowStyle.BOX

        if "-." in arrow_str and "->" in arrow_str:
            pass

        return edge_style, arrow_start, arrow_end

    def _parse_node_decoration(self, text: str) -> tuple[ShapeType, str]:
        text = text.strip()
        # Check for decorations like [label], {label}, (label), ((label)), <[label]>
        if text.startswith("[") and "]" in text:
            end = text.index("]")
            return ShapeType.RECTANGLE, text[1:end]
        if text.startswith("{") and "}" in text:
            end = text.index("}")
            return ShapeType.DIAMOND, text[1:end]
        if text.startswith("((") and "))" in text:
            end = text.index("))")
            return ShapeType.DOUBLE_CIRCLE, text[2:end]
        if text.startswith("(") and ")" in text:
            end = text.index(")")
            return ShapeType.ROUNDED_RECTANGLE, text[1:end]
        if text.startswith("<[") and "]>" in text:
            end = text.index("]>")
            return ShapeType.HEXAGON, text[2:end]
        if text.startswith(">") and "]" in text:
            end = text.index("]")
            return ShapeType.PARALLELOGRAM, text[1:end]
        return ShapeType.RECTANGLE, text.split()[0] if text else ""

    def _ensure_positions(self, diagram: Diagram) -> None:
        nodes = diagram.all_nodes()
        layout = diagram.layout or Layout()
        gap_x = layout.node_spacing + 140
        gap_y = layout.layer_spacing + 50

        deps: dict[str, list[str]] = {n.id: [] for n in nodes}
        for e in diagram.edges:
            if e.source in deps:
                deps[e.source].append(e.target)

        layers: list[list[str]] = []
        assigned: set[str] = set()
        remaining = set(deps.keys())

        while remaining:
            layer = [n for n in remaining if not any(t in remaining and t != n for t in deps.get(n, []))]
            if not layer:
                layer = [remaining.pop()]
            layers.append(layer)
            assigned.update(layer)
            remaining -= set(layer)

        for layer_idx, layer_nodes in enumerate(layers):
            for col_idx, nid in enumerate(layer_nodes):
                node = diagram.get_node(nid)
                if node is not None:
                    node.position = Position(
                        x=col_idx * gap_x + layout.padding,
                        y=layer_idx * gap_y + layout.padding,
                    )

        if diagram.viewport is None:
            max_x = max((n.position.x + n.size.width for n in nodes if n.position and n.size), default=800)
            max_y = max((n.position.y + n.size.height for n in nodes if n.position and n.size), default=600)
            from pidraw.core.models import Viewport
            diagram.viewport = Viewport(width=max_x + 40, height=max_y + 40)
