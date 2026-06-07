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
    Shape,
    ShapeType,
    Size,
    Style,
)

_NODE_STMT = re.compile(
    r'(\w[\w\d_]*|"[^"]*")\s*'
    r'(?:\[([^\]]*)\])?'
    r'\s*;?'
)

_EDGE_STMT = re.compile(
    r'(\w[\w\d_]*|"[^"]*")\s*'
    r'(--|->)\s*'
    r'(\w[\w\d_]*|"[^"]*")'
    r'(?:\s*\[([^\]]*)\])?'
    r'\s*;?'
)

_ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"|(\w+)\s*=\s*(\S+)')
_BRACES = re.compile(r'\{(.*)\}', re.DOTALL)

_SHAPE_MAP: dict[str, ShapeType] = {
    "box": ShapeType.RECTANGLE,
    "rect": ShapeType.RECTANGLE,
    "rectangle": ShapeType.RECTANGLE,
    "rounded": ShapeType.ROUNDED_RECTANGLE,
    "ellipse": ShapeType.ELLIPSE,
    "circle": ShapeType.CIRCLE,
    "doublecircle": ShapeType.DOUBLE_CIRCLE,
    "diamond": ShapeType.DIAMOND,
    "parallelogram": ShapeType.PARALLELOGRAM,
    "hexagon": ShapeType.HEXAGON,
    "cylinder": ShapeType.CYLINDER,
    "box3d": ShapeType.RECTANGLE,
    "note": ShapeType.DOCUMENT,
    "component": ShapeType.RECTANGLE,
    "actor": ShapeType.ACTOR,
}


@register_converter("graphviz")
class GraphvizConverter(DiagramConverter):
    language = "graphviz"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="graphviz_diagram", title="Graphviz Diagram")
        diagram.layout = Layout(layout_type=LayoutType.LAYERED, direction="TB", node_spacing=50, layer_spacing=70)

        direction = "TB"
        default_node_shape = ShapeType.ELLIPSE

        body_match = _BRACES.search(source)
        body = body_match.group(1) if body_match else source

        rankdir_m = re.search(r'rankdir\s*=\s*"?(\w+)"?', source, re.IGNORECASE)
        if rankdir_m:
            direction = rankdir_m.group(1).upper()

        # Split into statements by semicolon or newline
        stmts = re.split(r'[;\n]+', body)

        for stmt in stmts:
            stmt = stmt.strip()
            if not stmt or stmt.startswith("//") or stmt.startswith("#"):
                continue

            if re.match(r'^(subgraph|node|edge|graph)\b', stmt, re.IGNORECASE):
                continue

            edge_match = _EDGE_STMT.match(stmt)
            if edge_match:
                src_raw = edge_match.group(1).strip('"')
                tgt_raw = edge_match.group(3).strip('"')

                for nid in (src_raw, tgt_raw):
                    if nid not in diagram.nodes:
                        node = Node(
                            id=nid,
                            label=Label(text=nid),
                            shape=Shape(shape_type=default_node_shape),
                            size=Size(100, 50),
                        )
                        diagram.add_node(node)

                attrs_str = edge_match.group(4) or ""
                attrs = self._parse_attrs(attrs_str)
                edge = Edge(
                    id=f"{src_raw}->{tgt_raw}",
                    source=src_raw,
                    target=tgt_raw,
                    label=Label(text=attrs["label"]) if "label" in attrs else None,
                )
                diagram.add_edge(edge)
                continue

            node_match = _NODE_STMT.match(stmt)
            if node_match and "->" not in stmt and "--" not in stmt:
                nid = node_match.group(1).strip('"')
                attrs_str = node_match.group(2) or ""
                attrs = self._parse_attrs(attrs_str)

                shape = _SHAPE_MAP.get(attrs.get("shape", "").lower(), default_node_shape)
                label_text = attrs.get("label", nid)

                # Parse style attributes from Graphviz
                fillcolor = attrs.get("fillcolor", "")
                color = attrs.get("color", "")
                fontcolor = attrs.get("fontcolor", "")

                if nid not in diagram.nodes:
                    tw = max(len(label_text) * 8, 60)
                    node_style_obj = None
                    if fillcolor or color or fontcolor:
                        node_style_obj = Style(
                            fill_color=fillcolor if fillcolor else Style().fill_color,
                            stroke_color=color if color else Style().stroke_color,
                            text_color=fontcolor if fontcolor else Style().text_color,
                        )
                    node = Node(
                        id=nid,
                        label=Label(text=label_text),
                        shape=Shape(shape_type=shape),
                        size=Size(tw + 40, 50),
                        style=node_style_obj,
                    )
                    diagram.add_node(node)

        if direction in ("LR", "RL"):
            diagram.layout.direction = direction

        return diagram

    def _parse_attrs(self, attrs: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for m in _ATTR.finditer(attrs):
            key = m.group(1) or m.group(3)
            value = m.group(2) or m.group(4) or ""
            result[key] = value
        return result
