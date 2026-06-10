from __future__ import annotations

import math
import re
from typing import Optional

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
    r"(?:\|(?:[^|]*)\|)?"               # optional edge label |...|
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
_STYLE_PROP = re.compile(
    r"(fill|stroke|color|stroke-width|stroke-dasharray)(?::|=)(#[0-9a-fA-F]{3,8}|\w+)",
    re.IGNORECASE,
)

_DIAGRAM_TYPE_RE = re.compile(
    r"^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram"
    r"|stateDiagram-v2|erDiagram|pie|gantt)\b",
    re.IGNORECASE,
)


@register_converter("mermaid")
class MermaidConverter(DiagramConverter):
    language = "mermaid"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="mermaid_diagram", title="Mermaid Diagram")
        diagram.layout = Layout(LayoutType.LAYERED, "TB", 40, 60)

        header_match = _DIAGRAM_TYPE_RE.search(source)
        diagram_type = header_match.group(1).lower() if header_match else "graph"

        parsers = {
            "sequencediagram": self._parse_sequence,
            "classdiagram": self._parse_class,
            "statediagram": self._parse_state,
            "statediagram-v2": self._parse_state,
            "erdiagram": self._parse_er,
            "pie": self._parse_pie,
            "gantt": self._parse_gantt,
        }

        parser = parsers.get(diagram_type)
        if parser:
            return parser(source, diagram)

        direction_match = _DIRECTION_PATTERN.search(source)
        if direction_match:
            diagram.layout.direction = direction_match.group(2).upper()

        return self._parse_graph(source, diagram)

    # ── flowchart / graph ────────────────────────────────────────────

    def _parse_graph(self, source: str, diagram: Diagram) -> Diagram:
        lines = source.strip().split("\n")
        node_styles: dict[str, dict[str, str]] = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("%%") or re.match(
                r"^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram)", line, re.IGNORECASE
            ):
                continue
            if line.startswith("subgraph ") or line.startswith("end"):
                continue

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

                for nid in (src_id, tgt_id):
                    idx = line.find(nid)
                    if idx >= 0:
                        remainder = line[idx + len(nid):]
                        shape_type, label_text = self._parse_node_decoration(remainder)
                        if not label_text:
                            label_text = nid
                    else:
                        shape_type, label_text = ShapeType.RECTANGLE, nid

                    if nid not in diagram.nodes:
                        from pidraw.core.shapes import compute_shape_size
                        sz = compute_shape_size(shape_type, label_text)
                        node = Node(
                            id=nid,
                            label=Label(text=label_text),
                            shape=Shape(shape_type=shape_type),
                            size=sz,
                        )
                        diagram.add_node(node)

                label_match = re.search(r"\|([^|]+)\|", line)
                edge_label = Label(text=label_match.group(1)) if label_match else None

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
                    shape_type = ShapeType.RECTANGLE
                elif node_match.group(3) is not None:
                    label_text = node_match.group(3)
                    shape_type = ShapeType.DIAMOND
                elif node_match.group(7) is not None:
                    label_text = node_match.group(7)
                    shape_type = ShapeType.DOUBLE_CIRCLE
                elif node_match.group(4) is not None:
                    label_text = node_match.group(4)
                    shape_type = ShapeType.STADIUM
                elif node_match.group(6) is not None:
                    label_text = node_match.group(6)
                    shape_type = ShapeType.HEXAGON
                elif node_match.group(8) is not None:
                    label_text = node_match.group(8)
                    shape_type = ShapeType.PARALLELOGRAM
                elif node_match.group(5) is not None:
                    label_text = node_match.group(5)

                if nid not in diagram.nodes:
                    from pidraw.core.shapes import compute_shape_size
                    sz = compute_shape_size(shape_type, label_text)
                    node = Node(
                        id=nid,
                        label=Label(text=label_text),
                        shape=Shape(shape_type=shape_type),
                        size=sz,
                    )
                    diagram.add_node(node)

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

    # ── sequenceDiagram ──────────────────────────────────────────────

    def _parse_sequence(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.direction = "TB"
        participants: dict[str, Node] = {}
        seq_idx = [0]

        for line in source.split("\n"):
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            if line.lower().startswith("sequencediagram"):
                continue

            pl = re.match(r"^(participant|actor)\s+([\w\d_]+)(?:\s+as\s+([\w\d_]+))?", line, re.IGNORECASE)
            if pl:
                role = pl.group(1).lower()
                p_id = pl.group(2)
                alias = pl.group(3) or p_id
                if p_id not in participants:
                    node = Node(
                        id=p_id,
                        label=Label(text=alias),
                        shape=Shape(
                            shape_type=ShapeType.ACTOR if role == "actor" else ShapeType.RECTANGLE
                        ),
                        size=Size(width=100, height=40),
                    )
                    diagram.add_node(node)
                    participants[p_id] = node
                continue

            note_m = re.match(r"Note\s+(over|right of|left of)\s+([\w\d_,]+)\s*:\s*(.+)", line)
            if note_m:
                continue

            am = re.match(
                r"([\w\d_]+)\s*"
                r"(->>?|->?x?|-->>?|-[xX]|=>|~[~>]>?)"
                r"\+?[-+]?"
                r"(>>?)?\s*"
                r"([\w\d_]+)\s*"
                r"(?::\s*(.*))?",
                line,
            )
            if am:
                src = am.group(1)
                arrow = am.group(2)
                tgt = am.group(4)
                label_text = am.group(5) or ""

                for pid in (src, tgt):
                    if pid not in participants:
                        node = Node(
                            id=pid,
                            label=Label(text=pid),
                            shape=Shape(shape_type=ShapeType.ACTOR),
                            size=Size(width=100, height=40),
                        )
                        diagram.add_node(node)
                        participants[pid] = node

                arrow_style = ArrowStyle.TRIANGLE_FILLED
                if arrow.startswith("--"):
                    edge_style = EdgeStyle.DASHED
                elif arrow.startswith("~"):
                    edge_style = EdgeStyle.DOTTED
                elif arrow.startswith("="):
                    edge_style = EdgeStyle.BOLD
                else:
                    edge_style = EdgeStyle.SOLID

                if arrow.endswith("x"):
                    arrow_style = ArrowStyle.BOX
                elif arrow.endswith("o"):
                    arrow_style = ArrowStyle.CIRCLE

                edge = Edge(
                    id=f"seq_{seq_idx[0]}",
                    source=src,
                    target=tgt,
                    label=Label(text=label_text) if label_text else None,
                    style=Style(
                        stroke_style=edge_style,
                        arrow_end=arrow_style,
                    ),
                )
                diagram.add_edge(edge)
                seq_idx[0] += 1
                continue

        self._ensure_positions(diagram)
        return diagram

    # ── classDiagram ─────────────────────────────────────────────────

    def _parse_class(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.direction = "TB"
        current_class: Optional[str] = None
        class_bodies: dict[str, list[str]] = {}

        for line in source.split("\n"):
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            if line.lower().startswith("classdiagram"):
                continue

            if "{" in line and not line.startswith("}"):
                cm = re.match(r"(class|interface|enum)\s+(\w[\w\d_]*)\s*\{?", line, re.IGNORECASE)
                if cm:
                    current_class = cm.group(2)
                    if current_class not in class_bodies:
                        class_bodies[current_class] = []
                        node = Node(
                            id=current_class,
                            label=Label(text=current_class),
                            shape=Shape(shape_type=ShapeType.RECTANGLE),
                            size=Size(width=120, height=60),
                            style=Style(
                                fill_color="#f8f9fa",
                                stroke_color="#333333",
                            ),
                        )
                        diagram.add_node(node)
                    continue

            if "}" in line:
                current_class = None
                continue

            if current_class and line:
                class_bodies[current_class].append(line)

            cr = re.match(
                r"(\w[\w\d_]*)\s*(<\|--|--\||<\.\.|\.\.>|\.\.\|>|<\|\.\.|\*--|o--|<@|--\*>|\.\.\*>)"
                r"\s*(\w[\w\d_]*)",
                line,
            )
            if cr:
                src = cr.group(1)
                rel = cr.group(2)
                tgt = cr.group(3)
                edge_style = EdgeStyle.SOLID
                arrow_start = ArrowStyle.NONE
                arrow_end = ArrowStyle.NONE

                if ".." in rel:
                    edge_style = EdgeStyle.DASHED
                if rel.endswith("|>"):
                    arrow_end = ArrowStyle.TRIANGLE_FILLED
                elif rel.endswith(">"):
                    arrow_end = ArrowStyle.TRIANGLE
                elif rel.startswith("<|"):
                    arrow_start = ArrowStyle.TRIANGLE_FILLED
                elif rel.startswith("<"):
                    arrow_start = ArrowStyle.TRIANGLE
                if "*--" in rel or "--*" in rel:
                    arrow_end = ArrowStyle.DIAMOND_FILLED
                elif "o--" in rel or "--o" in rel:
                    arrow_end = ArrowStyle.DIAMOND

                for cid in (src, tgt):
                    if cid not in diagram.nodes:
                        node = Node(
                            id=cid,
                            label=Label(text=cid),
                            shape=Shape(shape_type=ShapeType.RECTANGLE),
                            size=Size(width=100, height=40),
                        )
                        diagram.add_node(node)

                edge = Edge(
                    id=f"{src}-{tgt}",
                    source=src,
                    target=tgt,
                    style=Style(
                        stroke_style=edge_style,
                        arrow_start=arrow_start,
                        arrow_end=arrow_end,
                    ),
                )
                diagram.add_edge(edge)
                continue

            cc = re.match(r"(\w[\w\d_]*)\s*--\s*", line)
            if cc:
                continue

        self._ensure_positions(diagram)
        return diagram

    # ── stateDiagram / stateDiagram-v2 ───────────────────────────────

    def _parse_state(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.direction = "TB"
        state_count = [0]

        for line in source.split("\n"):
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            if line.lower().startswith("statediagram"):
                continue

            sm = re.match(
                r"\s*(\[\[\*\]\]|[\w\d_]+)\s*-->\s*(\[\[\*\]\]|[\w\d_]+)(?:\s*:\s*(.*))?",
                line,
            )
            if sm:
                src_raw = sm.group(1)
                tgt_raw = sm.group(2)
                label_text = sm.group(3) or ""

                src_id = src_raw
                if src_raw == "[*]":
                    src_id = f"__start_{state_count[0]}"
                    if src_id not in diagram.nodes:
                        node = Node(
                            id=src_id,
                            label=Label(text=""),
                            shape=Shape(shape_type=ShapeType.CIRCLE),
                            size=Size(width=20, height=20),
                            style=Style(fill_color="#333333", stroke_color="#333333"),
                        )
                        diagram.add_node(node)

                tgt_id = tgt_raw
                if tgt_raw == "[*]":
                    tgt_id = f"__end_{state_count[0]}"
                    if tgt_id not in diagram.nodes:
                        node = Node(
                            id=tgt_id,
                            label=Label(text=""),
                            shape=Shape(shape_type=ShapeType.DOUBLE_CIRCLE),
                            size=Size(width=24, height=24),
                            style=Style(fill_color="#ffffff", stroke_color="#333333", stroke_width=2),
                        )
                        diagram.add_node(node)

                for sid in (src_id, tgt_id):
                    if sid not in diagram.nodes and not sid.startswith("__"):
                        node = Node(
                            id=sid,
                            label=Label(text=sid),
                            shape=Shape(shape_type=ShapeType.ROUNDED_RECTANGLE),
                            size=Size(width=80, height=40),
                        )
                        diagram.add_node(node)

                edge = Edge(
                    id=f"s_{state_count[0]}",
                    source=src_id,
                    target=tgt_id,
                    label=Label(text=label_text) if label_text else None,
                )
                diagram.add_edge(edge)
                state_count[0] += 1
                continue

        self._ensure_positions(diagram)
        return diagram

    # ── erDiagram ────────────────────────────────────────────────────

    def _parse_er(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.direction = "LR"
        entities: dict[str, list[str]] = {}
        current_entity: Optional[str] = None

        for line in source.split("\n"):
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            if line.lower().startswith("erDiagram"):
                continue

            em = re.match(
                r"(\w[\w\d_]*)\s+(?:\"{2}|)[\w\s]*(?:\"{2}|)\s*\{",
                line,
            )
            if em:
                current_entity = em.group(1)
                entities[current_entity] = []
                continue

            if "}" in line:
                current_entity = None
                continue

            if current_entity and line:
                entities[current_entity].append(line)

            em2 = re.match(
                r"(\w[\w\d_]*)\s*"
                r"(\|o\|\||\|\|o\||\|o\|\||\|\|o\||\|o\|\||\|\|--o\{|"
                r"\|\|--\|\||o\{--\|\||\|\|--o\{|o\{o\{|\|\|--\|\|)"
                r"\s*(?:\"{2}([^\"]{2,})\"{2}|([\w\s]+))?\s*"
                r":\s*(.+)",
                line,
            )
            if not em2:
                em2 = re.match(
                    r"(\w[\w\d_]*)\s*"
                    r"([|o\-.<>{}]+)"
                    r"\s*(?:\"{2}([^\"]{2,})\"{2}|([\w\s]+))?\s*"
                    r":\s*(.+)",
                    line,
                )

            if em2:
                src = em2.group(1)
                label_text = em2.group(5) or ""

                # Simple heuristic for the target — the last word in the line before ":"
                tgt_match = re.match(
                    r"(\w[\w\d_]*)\s*[|o\-.<>{}]+\s*\w*\s*:\s*.+",
                    line,
                )
                tgt = ""
                if tgt_match:
                    tgt = tgt_match.group(1)

                for eid in (src, tgt):
                    if eid and eid not in diagram.nodes:
                        node = Node(
                            id=eid,
                            label=Label(text=eid),
                            shape=Shape(shape_type=ShapeType.RECTANGLE),
                            size=Size(width=100, height=40),
                        )
                        diagram.add_node(node)

                if tgt:
                    edge = Edge(
                        id=f"{src}-{tgt}",
                        source=src,
                        target=tgt,
                        label=Label(text=label_text) if label_text else None,
                    )
                    diagram.add_edge(edge)
                continue

        self._ensure_positions(diagram)
        return diagram

    # ── pie chart ────────────────────────────────────────────────────

    def _parse_pie(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.layout_type = LayoutType.GRID
        slices: list[tuple[str, float]] = []
        total = 0.0

        for line in source.split("\n"):
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            if line.lower().startswith("pie"):
                continue

            pm = re.match(r'"([^"]{2,})"\s*:\s*([\d.]+)', line)
            if not pm:
                pm = re.match(r'([\w\s]+)\s*:\s*([\d.]+)', line)
            if pm:
                label = pm.group(1).strip()
                val = float(pm.group(2))
                slices.append((label, val))
                total += val

        if not slices:
            return diagram

        cx, cy, r = 200, 200, 150
        colors = ["#ff6384", "#36a2eb", "#ffce56", "#4bc0c0",
                  "#9966ff", "#ff9f40", "#c9cbcf", "#ff6384"]
        start_angle = 0.0

        center_id = "pie_center"
        center_node = Node(
            id=center_id,
            label=Label(text=""),
            shape=Shape(shape_type=ShapeType.CIRCLE),
            position=Position(x=cx - r, y=cy - r),
            size=Size(width=r * 2, height=r * 2),
            style=Style(
                fill_color="transparent",
                stroke_color="transparent",
            ),
        )
        diagram.add_node(center_node)

        for i, (label, val) in enumerate(slices):
            angle = (val / total) * 360.0
            mid_angle = start_angle + angle / 2
            label_x = cx + (r * 0.7) * math.cos(math.radians(mid_angle))
            label_y = cy + (r * 0.7) * math.sin(math.radians(mid_angle))
            color = colors[i % len(colors)]

            slice_id = f"pie_{i}"
            slice_node = Node(
                id=slice_id,
                label=Label(text=f"{label} ({val:.0f})"),
                shape=Shape(shape_type=ShapeType.RECTANGLE),
                position=Position(x=label_x - 40, y=label_y - 10),
                size=Size(width=80, height=20),
                style=Style(
                    fill_color=color,
                    text_color="#fff",
                    font_size=10,
                ),
            )
            diagram.add_node(slice_node)
            start_angle += angle

        self._ensure_positions(diagram)
        return diagram

    # ── gantt chart ──────────────────────────────────────────────────

    def _parse_gantt(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.direction = "TB"
        section_name = ""
        task_idx = [0]

        for line in source.split("\n"):
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            if line.lower().startswith("gantt"):
                continue
            if line.lower().startswith("dateformat") or line.lower().startswith("title"):
                continue

            sm = re.match(r"section\s+(.+)", line, re.IGNORECASE)
            if sm:
                section_name = sm.group(1).strip()
                continue

            tm = re.match(
                r"\s*([\w\s]+)\s*:\s*(crit|active|done)?,?\s*"
                r"(after\s+\w+\s*,?\s*)?"
                r"([\w\d]+)\s*,\s*([\w\d]+)",
                line,
            )
            if tm:
                task_name = tm.group(1).strip()
                status = tm.group(2) or "active"

                tid = f"task_{task_idx[0]}"
                label = f"{task_name}"
                if section_name:
                    label = f"[{section_name}] {label}"

                fill = "#4caf50"
                if status == "crit":
                    fill = "#f44336"
                elif status == "done":
                    fill = "#9e9e9e"

                node = Node(
                    id=tid,
                    label=Label(text=label),
                    shape=Shape(shape_type=ShapeType.RECTANGLE),
                    size=Size(width=120, height=30),
                    style=Style(
                        fill_color=fill,
                        text_color="#fff",
                        font_size=11,
                    ),
                )
                diagram.add_node(node)
                task_idx[0] += 1
                continue

            tm2 = re.match(r"\s*([\w\s]+)\s*:\s*([\w\d]+)\s*,\s*([\w\d]+)", line)
            if tm2:
                task_name = tm2.group(1).strip()
                tid = f"task_{task_idx[0]}"
                label = f"{task_name}"
                if section_name:
                    label = f"[{section_name}] {label}"

                node = Node(
                    id=tid,
                    label=Label(text=label),
                    shape=Shape(shape_type=ShapeType.RECTANGLE),
                    size=Size(width=120, height=30),
                    style=Style(
                        fill_color="#4caf50",
                        text_color="#fff",
                        font_size=11,
                    ),
                )
                diagram.add_node(node)
                task_idx[0] += 1
                continue

        self._ensure_positions(diagram)
        return diagram

    # ── shared helpers ──────────────────────────────────────────────

    def _parse_arrow_style(self, arrow_str: str) -> tuple[EdgeStyle, ArrowStyle, ArrowStyle]:
        edge_style = EdgeStyle.SOLID
        arrow_end = ArrowStyle.TRIANGLE_FILLED
        arrow_start = ArrowStyle.NONE

        if "==" in arrow_str:
            edge_style = EdgeStyle.BOLD
        elif "-.->" in arrow_str or "-.." in arrow_str:
            edge_style = EdgeStyle.DOTTED
        elif "-.-" in arrow_str:
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

        return edge_style, arrow_start, arrow_end

    def _parse_node_decoration(self, text: str) -> tuple[ShapeType, str]:
        text = text.strip()
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
        return ShapeType.RECTANGLE, ""

    def _ensure_positions(self, diagram: Diagram) -> None:
        nodes = diagram.all_nodes()
        layout = diagram.layout or Layout()
        gap_x = layout.node_spacing * 4
        gap_y = layout.layer_spacing * 4

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
                if node is not None and node.position is None:
                    node.position = Position(
                        x=col_idx * gap_x + layout.padding,
                        y=layer_idx * gap_y + layout.padding,
                    )

        if diagram.viewport is None:
            positioned = [n for n in nodes if n.position]
            if positioned:
                min_x = min((n.position.x for n in positioned), default=0)
                min_y = min((n.position.y for n in positioned), default=0)
                max_x = max((n.position.x + n.size.width for n in positioned if n.size), default=800)
                max_y = max((n.position.y + n.size.height for n in positioned if n.size), default=600)
                cw = max_x - min_x
                ch = max_y - min_y
                pad = max(layout.padding * 2, cw * 0.15, ch * 0.15)
                from pidraw.core.models import Viewport
                diagram.viewport = Viewport(
                    x=min_x - pad,
                    y=min_y - pad,
                    width=cw + pad * 2,
                    height=ch + pad * 2,
                )
