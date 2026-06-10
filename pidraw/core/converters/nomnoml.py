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

_CLASS_PATTERN = re.compile(r"\[([^\]]*)\]")
_STEREOTYPE_PATTERN = re.compile(r"<([^>]+)>")
_RELATION_PATTERN = re.compile(
    r"\[([^\]]+)\]\s*(<->|->|\.->|\.\.>|-->|->o|->x|x->|x--x|-/->|==>|\.\.|-\.-|-/-|\.\.\.|--|\.\.)\s*\[([^\]]+)\]"
)
_STYLE_DIRECTIVE = re.compile(r"^\s*#(\w+)\s*:\s*(.+)$")
_SEPARATOR = re.compile(r"\|")


def _ensure_class(class_defs: dict, raw: str) -> None:
    parts = _SEPARATOR.split(raw)
    name_part = parts[0].strip()
    stereomatch = _STEREOTYPE_PATTERN.search(name_part)
    stereotype = ""
    if stereomatch:
        stereotype = stereomatch.group(1)
        name_part = _STEREOTYPE_PATTERN.sub("", name_part).strip()
    if not name_part or name_part in class_defs:
        return
    fields: list[str] = []
    methods: list[str] = []
    for p in parts[1:]:
        p = p.strip()
        if "(" in p or "()" in p:
            methods.append(p)
        else:
            fields.append(p)
    class_defs[name_part] = {
        "stereotype": stereotype,
        "fields": fields,
        "methods": methods,
    }


@register_converter("nomnoml")
class NomnomlConverter(DiagramConverter):
    language = "nomnoml"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="nomnoml_diagram", title="Nomnoml Diagram")
        diagram.layout = Layout(
            layout_type=LayoutType.LAYERED,
            direction="TB",
            node_spacing=60,
            layer_spacing=70,
        )
        diagram.style = Style(
            font_family="sans-serif",
            font_size=13,
            stroke_width=2,
            fill_color="#ffffff",
            stroke_color="#333333",
            text_color="#333333",
        )

        class_defs: dict[str, dict] = {}
        relationships: list[tuple[str, str, str]] = []
        node_counter = 0

        lines = source.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("//") or line_stripped.startswith("#"):
                continue

            rel_match = _RELATION_PATTERN.search(line_stripped)
            if rel_match:
                src_name = rel_match.group(1).strip()
                arrow_type = rel_match.group(2).strip()
                tgt_raw = rel_match.group(3).strip()
                _ensure_class(class_defs, tgt_raw)
                tgt_name = _SEPARATOR.split(tgt_raw)[0].strip()
                stereomatch = _STEREOTYPE_PATTERN.search(tgt_name)
                if stereomatch:
                    tgt_name = _STEREOTYPE_PATTERN.sub("", tgt_name).strip()
                relationships.append((src_name, arrow_type, tgt_name))
                continue

            class_match = _CLASS_PATTERN.findall(line_stripped)
            for cm in class_match:
                _ensure_class(class_defs, cm)

        default_w = 140
        default_h = 50
        slot_h = 18

        for name, info in class_defs.items():
            nid = f"n{node_counter}"
            node_counter += 1

            lines_list = [name]
            sep = "---"
            if info["fields"]:
                lines_list.append(sep)
                for f in info["fields"]:
                    lines_list.append(f"  {f}")
            if info["methods"]:
                lines_list.append(sep)
                for m in info["methods"]:
                    lines_list.append(f"  {m}")
            num_lines = len(lines_list)

            font_w = 8
            h = max(default_h, num_lines * slot_h + 16)
            w = default_w
            for line in lines_list:
                w = max(w, len(line) * font_w + 32)

            full_label = "\n".join(lines_list)

            stereotype = info["stereotype"]
            shape_type = ShapeType.RECTANGLE
            stroke_style = EdgeStyle.SOLID
            fill = "#ffffff"
            if stereotype == "abstract":
                stroke_style = EdgeStyle.DASHED
                fill = "#f5f5f5"
            elif stereotype == "interface":
                stroke_style = EdgeStyle.DOTTED
                fill = "#e8f4f8"
            elif stereotype == "note":
                shape_type = ShapeType.DOCUMENT
                fill = "#fffde7"
            elif stereotype == "package":
                shape_type = ShapeType.STADIUM
                fill = "#f0f0f0"
            elif stereotype == "frame":
                shape_type = ShapeType.ROUNDED_RECTANGLE
                fill = "#fafafa"
            elif stereotype == "database":
                shape_type = ShapeType.DATABASE
                fill = "#f3e5f5"
            elif stereotype == "input":
                shape_type = ShapeType.PARALLELOGRAM
                fill = "#e8f5e9"
            elif stereotype == "choice" or stereotype == "decision":
                shape_type = ShapeType.DIAMOND
                fill = "#fff3e0"

            node = Node(
                id=nid,
                label=Label(
                    text=full_label,
                    width=w,
                    height=h,
                ),
                shape=Shape(shape_type=shape_type),
                size=Size(w, h),
                position=Position(0, 0),
                style=Style(
                    fill_color=fill,
                    stroke_color="#333333",
                    stroke_width=2,
                    stroke_style=stroke_style,
                ),
            )
            diagram.add_node(node)

        if node_counter == 0:
            diagram.add_node(
                Node(
                    id="n0",
                    label=Label(text="Diagram"),
                    size=Size(140, 50),
                    position=Position(20, 20),
                    shape=Shape(shape_type=ShapeType.RECTANGLE),
                )
            )

        for src_name, arrow_type, tgt_name in relationships:
            src_node = self._find_node(diagram, src_name)
            tgt_node = self._find_node(diagram, tgt_name)
            if src_node is None or tgt_node is None:
                continue

            arrow_start = ArrowStyle.NONE
            arrow_end = ArrowStyle.TRIANGLE_FILLED
            stroke_style = EdgeStyle.SOLID

            if arrow_type == "->":
                arrow_end = ArrowStyle.TRIANGLE_FILLED
            elif arrow_type == "-->":
                arrow_end = ArrowStyle.TRIANGLE_FILLED
                stroke_style = EdgeStyle.BOLD
            elif arrow_type == "<->":
                arrow_start = ArrowStyle.TRIANGLE_FILLED
                arrow_end = ArrowStyle.TRIANGLE_FILLED
            elif arrow_type == "..>" or arrow_type == ".->":
                arrow_end = ArrowStyle.TRIANGLE
                stroke_style = EdgeStyle.DASHED
            elif arrow_type == "->o":
                arrow_end = ArrowStyle.CIRCLE_FILLED
            elif arrow_type == "->x":
                arrow_end = ArrowStyle.BOX
            elif arrow_type == "-/-" or arrow_type == "-/->":
                arrow_end = ArrowStyle.NONE
                stroke_style = EdgeStyle.DASHED
            elif arrow_type == "==>":
                arrow_end = ArrowStyle.TRIANGLE_FILLED
                stroke_style = EdgeStyle.BOLD
            elif arrow_type == "-.-" or arrow_type == "..":
                stroke_style = EdgeStyle.DASHED
                arrow_end = ArrowStyle.NONE
            elif arrow_type == "--" or arrow_type == "...":
                arrow_end = ArrowStyle.NONE
            else:
                arrow_end = ArrowStyle.TRIANGLE_FILLED

            edge = Edge(
                id=f"{src_node.id}->{tgt_node.id}",
                source=src_node.id,
                target=tgt_node.id,
                label=None,
                style=Style(
                    stroke_style=stroke_style,
                    arrow_start=arrow_start,
                    arrow_end=arrow_end,
                    stroke_color="#333333",
                    stroke_width=2,
                ),
            )
            diagram.add_edge(edge)

        return diagram

    def _find_node(self, diagram: Diagram, name: str) -> Node | None:
        name = _SEPARATOR.split(name.strip())[0].strip()
        for n in diagram.all_nodes():
            if n.label and n.label.text:
                first_line = n.label.text.split("\n")[0].strip()
                if first_line == name:
                    return n
        return None
