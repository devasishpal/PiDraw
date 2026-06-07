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
    Position,
    Shape,
    ShapeType,
    Size,
)

_PARTICIPANT_PATTERN = re.compile(
    r"(?:participant|actor|entity|class)\s+"
    r'"?(?:(\w[\w\d_]*)"?\s+as\s+(\w[\w\d_]*)|(\w[\w\d_]*))"?'
    r'(?:\s*<<\s*(\w+)\s*>>)?'
    r'(?:\s*\{)?',
    re.IGNORECASE,
)

_ARROW_PATTERN = re.compile(
    r'(\w[\w\d_]*)\s*'
    r'(-+>|\.+>|-+>>|\.+>>|-+\)|\.+\)|-+\[|\.+\[|<[-.]+>|<-[-.]+|<<?[-.]+>>?)'
    r'(?:\s*:\s*(.+))?\s*'
    r'(\w[\w\d_]*)?'
)

_NOTE_PATTERN = re.compile(r"note\s+(left|right|over)\s+(\w[\w\d_]*)", re.IGNORECASE)


@register_converter("plantuml")
class PlantUMLConverter(DiagramConverter):
    language = "plantuml"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="plantuml_diagram", title="PlantUML Diagram")
        diagram.layout = Layout(layout_type=LayoutType.LAYERED, direction="LR", node_spacing=50, layer_spacing=80)

        lines = source.strip().split("\n")
        in_skin = False

        for line in lines:
            line = line.strip()
            if not line or line.startswith("'") or line == "@startuml" or line == "@enduml" or line.startswith("skinparam"):
                continue
            if line.startswith("package ") or line.startswith("namespace "):
                continue
            if line.startswith("!define") or line.startswith("!include"):
                continue

            arrow_match = _ARROW_PATTERN.match(line)
            if arrow_match:
                src_id = arrow_match.group(1)
                raw_arrow = arrow_match.group(2)
                label_text = arrow_match.group(3)
                tgt_id = arrow_match.group(4)

                for nid in (src_id, tgt_id):
                    if nid and nid not in diagram.nodes:
                        node = Node(
                            id=nid,
                            label=Label(text=nid),
                            shape=Shape(shape_type=ShapeType.ACTOR if "actor" in line else ShapeType.RECTANGLE),
                            size=Size(120, 50),
                        )
                        diagram.add_node(node)

                if tgt_id:
                    edge_label = Label(text=label_text) if label_text else None
                    arrow_end = ArrowStyle.TRIANGLE_FILLED
                    if ">>" in raw_arrow:
                        arrow_end = ArrowStyle.DIAMOND_FILLED
                    elif ")" in raw_arrow:
                        arrow_end = ArrowStyle.CIRCLE_FILLED
                    elif "[" in raw_arrow:
                        arrow_end = ArrowStyle.BOX
                    elif "o" in raw_arrow:
                        arrow_end = ArrowStyle.CIRCLE

                    arrow_start = ArrowStyle.NONE
                    if raw_arrow.startswith("<"):
                        arrow_start = arrow_end

                    edge = Edge(
                        id=f"{src_id}->{tgt_id}",
                        source=src_id,
                        target=tgt_id,
                        label=edge_label,
                    )
                    diagram.add_edge(edge)
                continue

            participant_match = _PARTICIPANT_PATTERN.match(line)
            if participant_match:
                alias = participant_match.group(2) or participant_match.group(3)
                name = participant_match.group(1) or alias
                if alias and alias not in diagram.nodes:
                    node = Node(
                        id=alias,
                        label=Label(text=name),
                        shape=Shape(shape_type=ShapeType.RECTANGLE),
                        size=Size(140, 50),
                    )
                    diagram.add_node(node)

        return diagram
