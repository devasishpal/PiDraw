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
    Point,
    Position,
    Shape,
    ShapeType,
    Size,
    Style,
    Viewport,
)

_NODE_PATTERN = re.compile(
    r"(\w[\w\d_]*)"  # 1: id
    r"(?:\[([^\]]*)\])?"  # 2: [label] rectangle
    r"(?:\{([^}]*)\})?"  # 3: {label} rhombus
    r"(?:\(\(([^)]*)\)\))?"  # 4: ((label)) circle
    r"(?:\(([^)]*)\))?"  # 5: (label) rounded rect
    r"(?:\"([^\"]*)\")?"  # 6: "label"
    r"(?:\<\[([^\]]*)\]\>)?"  # 7: <[label]> hexagon
    r"(?:\>([^>]*)\]?)?"  # 8: >label] async
)

_EDGE_PATTERN = re.compile(
    r"(\w[\w\d_]*)"  # source
    r"(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\(\([^)]*\)\)|<\[[^\]]*\]>)?\s*"  # optional node shape
    r"((?:[-=.]*[-=>]+|<-[-=.]*|<-|->|<->|==|--)[-\.=]*[-=>]*)"  # arrow
    r"\s*"  # space
    r"(?:\|(?:[^|]*)\|)?"  # optional edge label |...|
    r"\s*"  # space
    r"(\w[\w\d_]*)"  # target
    r"(?:\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\(\([^)]*\)\)|<\[[^\]]*\]>)?"  # optional node shape
)

_DIRECTION_PATTERN = re.compile(r"(?:^|\n)\s*(graph|flowchart)\s+(TB|TD|BT|LR|RL)", re.IGNORECASE)
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
    r"^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram-v2"
    r"|stateDiagram|erDiagram|pie|gantt)\b",
    re.IGNORECASE,
)


@register_converter("mermaid")
class MermaidConverter(DiagramConverter):
    language = "mermaid"

    def _normalize_inline(self, source: str) -> str:
        lines = source.split("\n")
        result: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("%"):
                result.append(line)
                continue
            header_m = _DIAGRAM_TYPE_RE.match(stripped)
            if header_m:
                rest = stripped[header_m.end():].strip()
                if not rest:
                    result.append(line)
                    continue
                depth = 0
                segments = []
                current = ""
                for ch in rest:
                    if ch == "{":
                        depth += 1
                        current += ch
                    elif ch == "}":
                        depth -= 1
                        current += ch
                    elif ch == ";" and depth == 0:
                        segments.append(current.strip())
                        current = ""
                    else:
                        current += ch
                if current.strip():
                    segments.append(current.strip())
                if not segments:
                    result.append(line)
                    continue

                diagram_type = header_m.group(1).lower()
                if diagram_type in ("flowchart", "graph") and segments:
                    dir_m = re.match(r"(TB|TD|BT|LR|RL)\s*", segments[0], re.IGNORECASE)
                    if dir_m:
                        header_line = header_m.group(1) + " " + dir_m.group(1).upper()
                        result.append(header_line)
                        for s in segments[1:]:
                            if s:
                                result.append(s)
                        continue

                for s in segments:
                    if s:
                        result.append(s)
                continue
            result.append(line)
        return "\n".join(result)

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="mermaid_diagram", title="Mermaid Diagram")
        diagram.layout = Layout(LayoutType.LAYERED, "TB", 40, 60)

        header_match = _DIAGRAM_TYPE_RE.search(source)
        diagram_type = header_match.group(1).lower() if header_match else "graph"

        source = self._normalize_inline(source)

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
            if (
                not line
                or line.startswith("%%")
                or re.match(
                    r"^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram)",
                    line,
                    re.IGNORECASE,
                )
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
                        remainder = line[idx + len(nid) :]
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
                elif node_match.group(4) is not None:
                    label_text = node_match.group(4)
                    shape_type = ShapeType.DOUBLE_CIRCLE
                elif node_match.group(5) is not None:
                    label_text = node_match.group(5)
                    shape_type = ShapeType.STADIUM
                elif node_match.group(7) is not None:
                    label_text = node_match.group(7)
                    shape_type = ShapeType.HEXAGON
                elif node_match.group(8) is not None:
                    label_text = node_match.group(8)
                    shape_type = ShapeType.PARALLELOGRAM
                elif node_match.group(6) is not None:
                    label_text = node_match.group(6)

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

        return diagram

    # ── sequenceDiagram ──────────────────────────────────────────────

    def _parse_sequence(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.direction = "TB"
        participants: dict[str, Node] = {}
        raw_edges: list[tuple[str, str, str, str]] = []  # src, tgt, label, arrow

        for line in source.split("\n"):
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            if line.lower().startswith("sequencediagram"):
                continue

            pl = re.match(
                r"^(participant|actor)\s+([\w\d_]+)(?:\s+as\s+([\w\d_]+))?", line, re.IGNORECASE
            )
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
                r"(->>?|->?x?|-->>?|-[xX]|-\)|--\)|=>|~[~>]>?)"
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

                raw_edges.append((src, tgt, label_text, arrow))
                continue

        if not participants:
            return diagram

        # -- Position participants horizontally --
        pad = diagram.layout.padding if diagram.layout else 20
        gap = diagram.layout.node_spacing if diagram.layout else 60
        pp_width = max((n.size.width if n.size else 100) for n in participants.values())

        x = float(pad)
        y = float(pad)
        part_positions: dict[str, tuple[float, float, float, float]] = {}
        for pid in participants:
            node = participants[pid]
            nw = node.size.width if node.size else 100
            nh = node.size.height if node.size else 40
            node.position = Position(x, y)
            part_positions[pid] = (x, y, nw, nh)
            x += pp_width + gap

        pp_bottom = pad + max((n.size.height if n.size else 40) for n in participants.values())

        # -- Create edges with waypoints at distinct Y levels --
        msg_gap = max(gap, 30)
        for i, (src, tgt, label_text, arrow) in enumerate(raw_edges):
            if src not in part_positions or tgt not in part_positions:
                continue
            sx, sy, sw, sh = part_positions[src]
            tx, ty, tw, th = part_positions[tgt]

            y_off = pp_bottom + (i + 1) * msg_gap

            x1 = sx + sw
            if sx > tx:
                x1 = sx
            x2 = tx
            if sx > tx:
                x2 = tx + tw

            waypoints = [Point(x1, y_off), Point(x2, y_off)]

            edge_style = EdgeStyle.SOLID
            arrow_style = ArrowStyle.TRIANGLE_FILLED
            if arrow.startswith("--"):
                edge_style = EdgeStyle.DASHED
            elif arrow.startswith("~"):
                edge_style = EdgeStyle.DOTTED
            elif arrow.startswith("="):
                edge_style = EdgeStyle.BOLD
            if arrow.endswith("x"):
                arrow_style = ArrowStyle.BOX
            elif arrow.endswith("o"):
                arrow_style = ArrowStyle.CIRCLE

            edge = Edge(
                id=f"seq_{i}",
                source=src,
                target=tgt,
                label=Label(text=label_text) if label_text else None,
                style=Style(stroke_style=edge_style, arrow_end=arrow_style),
                waypoints=waypoints,
            )
            diagram.add_edge(edge)

        # -- Compute viewport --
        all_pos = [n.position for n in diagram.all_nodes() if n.position]
        if all_pos:
            min_x = min(p.x for p in all_pos)
            min_y = min(p.y for p in all_pos)
            max_x = max(
                p.x + (n.size.width if n.size else 100)
                for n, p in zip(diagram.all_nodes(), all_pos)
            )
            max_y = pp_bottom + (len(raw_edges) + 1) * msg_gap + 20
            cw = max_x - min_x
            ch = max_y - min_y
            p = max(pad * 2, cw * 0.15, ch * 0.15)
            diagram.viewport = Viewport(x=min_x - p, y=min_y - p, width=cw + p * 2, height=ch + p * 2)

        # Disable layout engine — we handle positioning
        diagram.layout.layout_type = LayoutType.NONE
        return diagram

    # ── classDiagram ─────────────────────────────────────────────────

    def _parse_class(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.direction = "TB"
        current_class: Optional[str] = None
        class_members: dict[str, list[str]] = {}

        for line in source.split("\n"):
            line = line.strip()
            if not line or line.startswith("%"):
                continue
            if line.lower().startswith("classdiagram"):
                continue

            if "{" in line and not line.startswith("}"):
                cm = re.match(r"(class|interface|enum)\s+([\w][\w-]*)\s*\{?", line, re.IGNORECASE)
                if cm:
                    current_class = cm.group(2)
                    if current_class not in diagram.nodes:
                        node = Node(
                            id=current_class,
                            label=Label(text=current_class),
                            shape=Shape(shape_type=ShapeType.RECTANGLE),
                            size=Size(width=140, height=50),
                            style=Style(
                                fill_color="#f8f9fa",
                                stroke_color="#333333",
                            ),
                        )
                        diagram.add_node(node)

                    brace_s = line.index("{")
                    brace_e = line.find("}", brace_s)
                    if brace_e > brace_s:
                        inline_content = line[brace_s + 1 : brace_e].strip()
                        if inline_content:
                            for p in inline_content.split(";"):
                                p = p.strip()
                                if p:
                                    class_members.setdefault(current_class, []).append(p)
                        current_class = None
                        continue

            if "}" in line:
                current_class = None
                continue

            if current_class and line:
                class_members.setdefault(current_class, []).append(line)

            cr = re.match(
                r"([\w][\w-]*)\s*(<\|--|--\||<\.\.|\.\.>|\.\.\|>|<\|\.\.|\*--|o--|<@|--\*>|\.\.\*>)"
                r"\s*([\w][\w-]*)",
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
                    arrow_start = ArrowStyle.TRIANGLE_FILLED
                elif rel.endswith(">"):
                    arrow_start = ArrowStyle.TRIANGLE
                elif rel.startswith("<|"):
                    arrow_end = ArrowStyle.TRIANGLE_FILLED
                elif rel.startswith("<"):
                    arrow_end = ArrowStyle.TRIANGLE
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

            cc = re.match(r"([\w][\w-]*)\s*--\s*", line)
            if cc:
                continue

            # Parse class member: ClassName : member
            member_m = re.match(r"([\w][\w-]*)\s*:\s*(.+)", line)
            if member_m:
                cname = member_m.group(1)
                member_text = member_m.group(2).strip()
                class_members.setdefault(cname, [])
                class_members[cname].append(member_text)
                continue

        # Enrich class nodes with members
        for cname, members in class_members.items():
            node = diagram.get_node(cname)
            if node is not None:
                all_lines = [node.label.text if node.label else cname] + members
                node.label = Label(text="\n".join(all_lines))
                nlines = len(all_lines)
                node.size = Size(
                    width=max(node.size.width if node.size else 140, 140),
                    height=30 + nlines * 18,
                )

        # Position classes in a grid
        nodes = diagram.all_nodes()
        if nodes:
            pad = diagram.layout.padding if diagram.layout else 20
            gap = diagram.layout.node_spacing if diagram.layout else 40
            cols = max(1, int(math.ceil(math.sqrt(len(nodes)))))
            x, y = float(pad), float(pad)
            max_row_h = 0.0
            for i, node in enumerate(nodes):
                nw = node.size.width if node.size else 120
                nh = node.size.height if node.size else 60
                node.position = Position(x, y)
                max_row_h = max(max_row_h, nh)
                if (i + 1) % cols == 0:
                    x = float(pad)
                    y += max_row_h + gap
                    max_row_h = 0.0
                else:
                    x += nw + gap

        diagram.layout.layout_type = LayoutType.NONE
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
                r"\s*(\[\*\]|[\w\d_]+)\s*-->\s*(\[\*\]|[\w\d_]+)(?:\s*:\s*(.*))?",
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
                            style=Style(
                                fill_color="#ffffff", stroke_color="#333333", stroke_width=2
                            ),
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

        # LayeredLayout handles state diagrams well (nodes flow by transition order)
        diagram.layout.direction = "TB"
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
                r"([\w][\w-]*)\s+(?:\"{2}|)[\w\s]*(?:\"{2}|)\s*\{",
                line,
            )
            if em:
                current_entity = em.group(1)
                entities[current_entity] = []
                continue

            if line.strip() == "}":
                current_entity = None
                continue

            if current_entity and line:
                entities[current_entity].append(line)

            em2 = re.match(
                r"([\w][\w-]*)\s*"
                r"(\|o\|\||\|\|o\||\|o\|\||\|\|o\||\|o\|\||\|\|--o\{|"
                r"\|\|--\|\||o\{--\|\||\|\|--o\{|o\{o\{|\|\|--\|\|)"
                r"\s*(?:\"{2}([^\"]{2,})\"{2}|([\w-]+))?\s*"
                r":\s*(.+)",
                line,
            )
            if not em2:
                em2 = re.match(
                    r"([\w][\w-]*)\s*"
                    r"([|o\-.<>{}]+)"
                    r"\s*(?:\"{2}([^\"]{2,})\"{2}|([\w-]+))?\s*"
                    r":\s*(.+)",
                    line,
                )

            if em2:
                src = em2.group(1)
                label_text = em2.group(5) or ""

                # Target entity is captured by group 4 (or 3 if quoted) in the regex
                tgt = em2.group(4) or em2.group(3) or ""

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

        # Position entities horizontally
        nodes = diagram.all_nodes()
        if nodes:
            pad = diagram.layout.padding if diagram.layout else 20
            gap = diagram.layout.node_spacing if diagram.layout else 50
            x, y = float(pad), float(pad)
            for node in nodes:
                nw = node.size.width if node.size else 100
                node.position = Position(x, y)
                x += nw + gap

        diagram.layout.layout_type = LayoutType.NONE
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
                pm = re.match(r"([\w\s]+)\s*:\s*([\d.]+)", line)
            if pm:
                label = pm.group(1).strip()
                val = float(pm.group(2))
                slices.append((label, val))
                total += val

        if not slices:
            return diagram

        cx, cy, r = 200, 200, 150
        colors = [
            "#ff6384",
            "#36a2eb",
            "#ffce56",
            "#4bc0c0",
            "#9966ff",
            "#ff9f40",
            "#c9cbcf",
            "#ff6384",
        ]
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

        diagram.layout.layout_type = LayoutType.NONE
        return diagram

    # ── gantt chart ──────────────────────────────────────────────────

    def _parse_gantt(self, source: str, diagram: Diagram) -> Diagram:
        diagram.layout.direction = "TB"
        section_name = ""
        task_idx = [0]
        source_id_map: dict[str, str] = {}
        deps: list[tuple[str, str]] = []

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

            # Parse: task_name : [status,] [id,] [after X,] date, duration
            tm = re.match(r"([^:]+?)\s*:\s*(.+)", line)
            if tm:
                task_name = tm.group(1).strip()
                rest = tm.group(2).strip()

                status = ""
                src_id = ""
                after_task = ""

                # Extract optional status (crit/active/done)
                status_m = re.match(r"(crit|active|done),?\s*(.*)", rest, re.IGNORECASE)
                if status_m:
                    status = status_m.group(1).lower()
                    rest = status_m.group(2).strip()

                # Split into comma-separated parts
                parts = [p.strip() for p in re.split(r",\s*", rest)]

                # Extract source ID (the first word that's not a duration)
                for p in parts:
                    if re.match(r"^after\s+(\w+)$", p, re.IGNORECASE):
                        after_task = re.match(r"^after\s+(\w+)$", p, re.IGNORECASE).group(1)
                    elif re.match(r"^\w+$", p) and not re.match(r"^\d+[dwm]$", p) and not src_id:
                        src_id = p

                fill = "#4caf50"
                if status == "crit":
                    fill = "#f44336"
                elif status == "done":
                    fill = "#9e9e9e"

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
                        fill_color=fill,
                        text_color="#fff",
                        font_size=11,
                    ),
                )
                diagram.add_node(node)
                if src_id:
                    source_id_map[src_id] = tid
                if after_task:
                    deps.append((after_task, tid))
                task_idx[0] += 1
                continue

        # Create dependency edges
        for after_id, tid in deps:
            if after_id in source_id_map:
                src_tid = source_id_map[after_id]
                edge = Edge(
                    id=f"{src_tid}-{tid}",
                    source=src_tid,
                    target=tid,
                    style=Style(stroke_style=EdgeStyle.DASHED, arrow_end=ArrowStyle.NONE),
                )
                diagram.add_edge(edge)

        # Position tasks in a vertical stack
        nodes = diagram.all_nodes()
        if nodes:
            pad = diagram.layout.padding if diagram.layout else 20
            gap = diagram.layout.layer_spacing if diagram.layout else 20
            x, y = float(pad), float(pad)
            for node in nodes:
                nh = node.size.height if node.size else 30
                node.position = Position(x, y)
                y += nh + gap

        diagram.layout.layout_type = LayoutType.NONE
        return diagram

    # ── shared helpers ──────────────────────────────────────────────

    def _parse_arrow_style(self, arrow_str: str) -> tuple[EdgeStyle, ArrowStyle, ArrowStyle]:
        edge_style = EdgeStyle.SOLID
        arrow_end = ArrowStyle.TRIANGLE_FILLED
        arrow_start = ArrowStyle.NONE

        if "==" in arrow_str:
            edge_style = EdgeStyle.BOLD
        elif "-." in arrow_str:
            edge_style = EdgeStyle.DOTTED

        if arrow_str.startswith("<->") or arrow_str.startswith("<==>"):
            arrow_start = ArrowStyle.TRIANGLE_FILLED
            arrow_end = ArrowStyle.TRIANGLE_FILLED
        elif arrow_str.startswith("<-"):
            arrow_start = ArrowStyle.TRIANGLE_FILLED

        if arrow_str.endswith("x") or arrow_str.endswith("x--"):
            arrow_end = ArrowStyle.BOX
        elif arrow_str.endswith("o") or arrow_str.endswith("o--"):
            arrow_end = ArrowStyle.CIRCLE

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
            layer = [
                n for n in remaining if not any(t in remaining and t != n for t in deps.get(n, []))
            ]
            if not layer:
                layer = [remaining.pop()]
            layers.append(layer)
            assigned.update(layer)
            remaining -= set(layer)

        layers.reverse()

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
                max_x = max(
                    (n.position.x + n.size.width for n in positioned if n.size), default=800
                )
                max_y = max(
                    (n.position.y + n.size.height for n in positioned if n.size), default=600
                )
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
