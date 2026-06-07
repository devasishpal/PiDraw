from __future__ import annotations

import re

from pidraw.core.converters.base import DiagramConverter, register_converter
from pidraw.core.models import (
    ArrowStyle,
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

_EDGE_D2 = re.compile(
    r'(\w[\w\d_.]*)\s*(<[-=]*|[-=]*[->]|<[-=]*[->])\s*(\w[\w\d_.]*)'
    r'(?:\s*:\s*(.+))?'
)

_NODE_D2 = re.compile(r'^(\w[\w\d_.]*)\s*:\s*(\w+)')

_CONTAINER_D2 = re.compile(r'^(\w[\w\d_.]*)\s*\{\s*$')

_STYLE_PROP = re.compile(r'style\.\w+' r'(?:\.\w+)?\s*:\s*(.+)')

_DIRECTIVE = re.compile(r'^(direction|shape|style|link|icon|constraint|near)', re.IGNORECASE)

_SHAPE_MAP: dict[str, ShapeType] = {
    "rectangle": ShapeType.RECTANGLE,
    "square": ShapeType.RECTANGLE,
    "circle": ShapeType.CIRCLE,
    "ellipse": ShapeType.ELLIPSE,
    "diamond": ShapeType.DIAMOND,
    "hexagon": ShapeType.HEXAGON,
    "cloud": ShapeType.CLOUD,
    "cylinder": ShapeType.CYLINDER,
    "stadium": ShapeType.STADIUM,
    "class": ShapeType.RECTANGLE,
    "sql_table": ShapeType.RECTANGLE,
    "image": ShapeType.RECTANGLE,
    "person": ShapeType.ACTOR,
}


@register_converter("d2")
class D2Converter(DiagramConverter):
    language = "d2"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="d2_diagram", title="D2 Diagram")
        diagram.layout = Layout(layout_type=LayoutType.FLOW, direction="TB", node_spacing=50, layer_spacing=70)

        lines = source.strip().split("\n")
        in_container: list[str] = []
        in_styles = False
        styles_section: dict[str, dict[str, str]] = {}

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped == "}":
                if in_styles:
                    in_styles = False
                if in_container and stripped == "}":
                    in_container.pop()
                continue
            if stripped.startswith("#"):
                continue

            # Track styles: section
            if stripped.lower().startswith("styles:"):
                in_styles = True
                continue

            if in_styles:
                # Parse: parent.child: { prop: value }
                style_match = re.match(r'([\w.]+)\s*:\s*\{', stripped)
                if style_match:
                    target = style_match.group(1)
                    # Collect properties until we hit }
                    props = {}
                    style_lines = lines[lines.index(line) + 1:]
                    for sl in style_lines:
                        sls = sl.strip()
                        if sls == "}":
                            break
                        prop_m = re.match(r'(\w+)\s*:\s*"([^"]*)"', sls)
                        if prop_m:
                            props[prop_m.group(1)] = prop_m.group(2)
                    if props:
                        styles_section[target] = props
                continue

            if stripped.startswith('"') and stripped.endswith('"'):
                continue

            container_match = _CONTAINER_D2.match(stripped)
            if container_match:
                cid = container_match.group(1)
                in_container.append(cid)
                if cid not in diagram.nodes:
                    node = Node(
                        id=cid,
                        label=Label(text=cid),
                        shape=Shape(shape_type=ShapeType.ROUNDED_RECTANGLE),
                        size=Size(160, 60),
                    )
                    diagram.add_node(node)
                continue

            edge_match = _EDGE_D2.match(stripped)
            if edge_match:
                src_id = edge_match.group(1)
                arrow_str = edge_match.group(2)
                tgt_id = edge_match.group(3)
                label_text = edge_match.group(4)

                for nid in (src_id, tgt_id):
                    parts = nid.split(".")
                    simple_id = parts[-1]
                    if simple_id not in diagram.nodes:
                        node = Node(
                            id=simple_id,
                            label=Label(text=nid),
                            shape=Shape(shape_type=ShapeType.RECTANGLE),
                            size=Size(130, 50),
                        )
                        diagram.add_node(node)

                arrow_start = ArrowStyle.NONE
                arrow_end = ArrowStyle.TRIANGLE_FILLED
                if "<" in arrow_str and ">" in arrow_str:
                    arrow_start = ArrowStyle.TRIANGLE_FILLED

                edge_label = Label(text=label_text) if label_text else None
                edge = Edge(
                    id=f"{src_id}->{tgt_id}",
                    source=src_id.split(".")[-1],
                    target=tgt_id.split(".")[-1],
                    label=edge_label,
                    style=Style(arrow_end=arrow_end, arrow_start=arrow_start),
                )
                diagram.add_edge(edge)
                continue

            node_match = _NODE_D2.match(stripped)
            if node_match:
                nid = node_match.group(1)
                shape_str = node_match.group(2).lower()

                shape_type = _SHAPE_MAP.get(shape_str, ShapeType.RECTANGLE)
                if nid not in diagram.nodes:
                    label_text = nid
                    node = Node(
                        id=nid,
                        label=Label(text=label_text),
                        shape=Shape(shape_type=shape_type),
                        size=Size(130, 50),
                    )
                    diagram.add_node(node)

        # Apply styles from styles: section
        for target, props in styles_section.items():
            parts = target.split(".")
            nid = parts[-1]
            node = diagram.get_node(nid)
            if node is not None:
                fill = props.get("fill")
                stroke = props.get("stroke")
                node.style = Style(
                    fill_color=fill if fill else (node.style.fill_color if node.style else Style().fill_color),
                    stroke_color=stroke if stroke else (node.style.stroke_color if node.style else Style().stroke_color),
                )

        return diagram
