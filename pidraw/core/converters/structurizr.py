from __future__ import annotations

import re
from typing import Any

from pidraw.core.converters.base import DiagramConverter, register_converter
from pidraw.core.models import (
    ArrowStyle,
    Diagram,
    Edge,
    FontWeight,
    Group,
    Label,
    Layout,
    LayoutType,
    Node,
    Position,
    Shape,
    ShapeType,
    Size,
    Style,
    Viewport,
)

_TOKEN_PATTERN = re.compile(r'"[^"]*"|\S+')

_ELEMENT_TYPES: dict[str, str] = {
    "person": "Person",
    "softwareSystem": "Software System",
    "container": "Container",
    "component": "Component",
}

_SHAPE_MAP: dict[str, ShapeType] = {
    "Person": ShapeType.ACTOR,
    "Software System": ShapeType.RECTANGLE,
    "Container": ShapeType.ROUNDED_RECTANGLE,
    "Component": ShapeType.ROUNDED_RECTANGLE,
}

_COLOR_MAP: dict[str, tuple[str, str]] = {
    "Person": ("#08427b", "#d4e6f9"),
    "Software System": ("#116b36", "#d4f0e0"),
    "Container": ("#1b6b8c", "#d4edf5"),
    "Component": ("#6b1b8c", "#edd4f5"),
}


def _read_string(tokens: list[str], pos: int) -> tuple[str | None, int]:
    if pos < len(tokens):
        t = tokens[pos]
        if t.startswith('"') and t.endswith('"'):
            return t[1:-1], pos + 1
    return None, pos


def _read_token(tokens: list[str], pos: int) -> tuple[str | None, int]:
    if pos < len(tokens):
        t = tokens[pos]
        if t.startswith('"') and t.endswith('"'):
            return t[1:-1], pos + 1
        return t, pos + 1
    return None, pos


def _try_parse_relationship(tokens: list[str], pos: int) -> tuple[dict | None, int]:
    if pos + 2 >= len(tokens):
        return None, pos
    if tokens[pos + 1] != "->":
        return None, pos
    src = tokens[pos]
    tgt, p2 = _read_token(tokens, pos + 2)
    if tgt is None:
        return None, pos
    desc, p3 = _read_string(tokens, p2)
    tech, p4 = _read_string(tokens, p3)
    return {"source": src, "target": tgt, "description": desc or "", "technology": tech or ""}, p4


def _try_parse_element(tokens: list[str], pos: int) -> tuple[dict | None, int]:
    if pos >= len(tokens):
        return None, pos
    tok = tokens[pos]
    if tok not in _ELEMENT_TYPES:
        return None, pos
    etype = _ELEMENT_TYPES[tok]
    name, p2 = _read_string(tokens, pos + 1)
    if name is None or not name:
        return None, pos
    desc = None
    p3 = p2
    if p2 < len(tokens) and tokens[p2].startswith('"'):
        desc, p3 = _read_string(tokens, p2)
    tech = None
    p4 = p3
    if p3 < len(tokens) and tokens[p3].startswith('"'):
        tech, p4 = _read_string(tokens, p3)
    return {
        "id": name,
        "type": etype,
        "name": name,
        "description": desc or "",
        "technology": tech or "",
    }, p4


def _tokenize(source: str) -> list[str]:
    cleaned = re.sub(r"//[^\n]*", "", source)
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return _TOKEN_PATTERN.findall(cleaned)


def _parse_model(
    tokens: list[str], pos: int, parent_id: str | None = None
) -> tuple[dict[str, Any], int]:
    elements: dict[str, dict[str, Any]] = {}
    relationships: list[dict[str, Any]] = []
    while pos < len(tokens):
        tok = tokens[pos]
        if tok == "}":
            pos += 1
            break
        if tok == "{":
            pos += 1
            continue
        rel = _try_parse_relationship(tokens, pos)
        if rel[0] is not None:
            relationships.append(rel[0])
            pos = rel[1]
            continue
        if pos + 1 < len(tokens) and tokens[pos + 1] == "=":
            ident = tok
            pos += 2
            if pos < len(tokens) and tokens[pos] in _ELEMENT_TYPES:
                elem, new_pos = _try_parse_element(tokens, pos)
                if elem:
                    elem["id"] = ident
                    elem["parent"] = parent_id
                    elements[ident] = elem
                    pos = new_pos
                    if pos < len(tokens) and tokens[pos] == "{":
                        pos += 1
                        children, pos = _parse_model(tokens, pos, ident)
                        for k, v in children["elements"].items():
                            elements[k] = v
                        relationships.extend(children["relationships"])
                        if pos < len(tokens) and tokens[pos] == "}":
                            pos += 1
            continue
        if tok in _ELEMENT_TYPES:
            elem, new_pos = _try_parse_element(tokens, pos)
            if elem:
                elem["parent"] = parent_id
                eid = elem["id"]
                elements[eid] = elem
                pos = new_pos
                if pos < len(tokens) and tokens[pos] == "{":
                    pos += 1
                    children, pos = _parse_model(tokens, pos, eid)
                    for k, v in children["elements"].items():
                        elements[k] = v
                    relationships.extend(children["relationships"])
                    if pos < len(tokens) and tokens[pos] == "}":
                        pos += 1
            continue
        pos += 1
    return {"elements": elements, "relationships": relationships}, pos


@register_converter("structurizr")
class StructurizrConverter(DiagramConverter):
    language = "structurizr"

    def parse(self, source: str) -> Diagram:
        diagram = Diagram(id="structurizr_diagram", title="Structurizr Diagram")
        diagram.layout = Layout(layout_type=LayoutType.NONE)
        diagram.style = Style(
            font_family="sans-serif",
            font_size=13,
            fill_color="#ffffff",
            stroke_color="#333333",
        )

        tokens = _tokenize(source)
        elements: dict[str, dict[str, Any]] = {}
        relationships: list[dict[str, Any]] = []
        pos = 0
        while pos < len(tokens):
            tok = tokens[pos]
            if tok in ("}", "{"):
                pos += 1
                continue
            if tok == "workspace":
                pos += 1
                _read_string(tokens, pos)
                _read_string(tokens, pos)
                continue
            if tok == "model":
                pos += 1
                if pos < len(tokens) and tokens[pos] == "{":
                    pos += 1
                result, pos = _parse_model(tokens, pos)
                elements.update(result["elements"])
                relationships.extend(result["relationships"])
                continue
            if tok == "views":
                pos += 1
                while pos < len(tokens) and tokens[pos] not in ("}", "{"):
                    pos += 1
                continue
            pos += 1

        children_of: dict[str, list[str]] = {}
        for eid, edata in elements.items():
            pid = edata.get("parent")
            if pid:
                children_of.setdefault(pid, []).append(eid)

        def _make_node(eid: str, edata: dict) -> Node:
            etype = edata.get("type", "Software System")
            ename = edata.get("name", eid)
            edesc = edata.get("description", "")
            etech = edata.get("technology", "")
            parts = [ename]
            if edesc:
                parts.append(f"[{edesc}]")
            if etech:
                parts.append(f"({etech})")
            display = "\n".join(parts)
            text_color, bg_color = _COLOR_MAP.get(etype, ("#333", "#fff"))
            longest = max(len(p) for p in parts)
            label_w = max(longest * 7.5 + 32, 120)
            label_h = len(parts) * 20 + 12
            return Node(
                id=eid,
                label=Label(
                    text=display if len(parts) > 1 else ename, width=label_w, height=label_h
                ),
                shape=Shape(shape_type=_SHAPE_MAP.get(etype, ShapeType.RECTANGLE)),
                size=Size(label_w, label_h),
                style=Style(
                    fill_color=bg_color,
                    stroke_color=text_color,
                    text_color=text_color,
                    stroke_width=2,
                    font_size=12 if etype == "Person" else 13,
                    font_family="sans-serif",
                ),
            )

        node_map: dict[str, Node] = {}
        group_map: dict[str, Group] = {}
        for eid, edata in elements.items():
            node = _make_node(eid, edata)
            node_map[eid] = node
            diagram.add_node(node)

        for eid in sorted(elements.keys()):
            edata = elements[eid]
            if edata.get("type") not in ("Software System", "Container"):
                continue
            kids = children_of.get(eid, [])
            if not kids:
                continue
            gid = f"group_{eid}"
            group = Group(id=gid, label=Label(text=edata["name"]))
            for cid in kids:
                group.nodes.append(node_map[cid])
            group_map[eid] = group
            diagram.add_group(group)

            parent_node = node_map[eid]
            label = parent_node.label
            style = parent_node.style
            parent_node.label = Label(
                text=edata["name"],
                width=label.width if label else 220,
                height=28,
            )
            parent_node.style = Style(
                fill_color=style.fill_color if style else "#dae8fc",
                stroke_color=style.stroke_color if style else "#6c8ebf",
                text_color=style.stroke_color if style else "#6c8ebf",
                stroke_width=0,
                font_size=13,
                font_weight=FontWeight.BOLD,
                font_family="sans-serif",
            )

        node_w = 220
        node_h = 60
        pad_x = 40
        pad_y = 30
        gap_y = 30
        group_pad = 20
        y_cursor = float(pad_y)

        for eid in elements:
            pid = elements[eid].get("parent")
            if pid and pid in elements:
                continue
            if eid in group_map:
                _layout_parent_with_children(
                    eid,
                    node_map,
                    group_map,
                    children_of,
                    pad_x,
                    y_cursor,
                    node_w,
                    node_h,
                    group_pad,
                    gap_y,
                    elements,
                )
                g = group_map[eid]
                gpos = g.position
                gsz = g.size
                y_cursor = (gpos.y if gpos else 0) + (gsz.height if gsz else 0) + gap_y
            else:
                n = node_map[eid]
                nsz = n.size
                nw = nsz.width if nsz else node_w
                nh = nsz.height if nsz else node_h
                n.position = Position(pad_x + (node_w - nw) / 2, y_cursor + 10)
                n.size = Size(max(nw, node_w), max(nh, node_h))
                y_cursor += float(max(nh, node_h) + gap_y)

        max_x = 0.0
        for n in node_map.values():
            if n.position:
                if n.position and n.size:
                    max_x = max(max_x, n.position.x + n.size.width)
        for g in group_map.values():
            if g.position and g.size:
                max_x = max(max_x, g.position.x + g.size.width)

        vw = max(max_x + pad_x, 500)
        vh = max(y_cursor + pad_y, 200)
        diagram.viewport = Viewport(x=0, y=0, width=vw, height=vh)

        for rel in relationships:
            src = rel["source"]
            tgt = rel["target"]
            sn = node_map.get(src)
            tn = node_map.get(tgt)
            if sn and tn:
                txt = rel["description"]
                if rel["technology"]:
                    txt = f"{txt} [{rel['technology']}]" if txt else f"[{rel['technology']}]"
                diagram.add_edge(
                    Edge(
                        id=f"{src}->{tgt}",
                        source=sn.id,
                        target=tn.id,
                        label=Label(text=txt) if txt else None,
                        style=Style(
                            arrow_end=ArrowStyle.TRIANGLE_FILLED,
                            stroke_color="#333",
                            stroke_width=1.5,
                        ),
                    )
                )

        if not diagram.all_nodes() and not diagram.groups:
            diagram.add_node(
                Node(
                    id="empty",
                    label=Label(text="No elements defined"),
                    size=Size(200, 60),
                    position=Position(20, 20),
                )
            )

        return diagram


def _layout_parent_with_children(
    eid: str,
    node_map: dict,
    group_map: dict,
    children_of: dict,
    x0: float,
    y0: float,
    def_w: float,
    def_h: float,
    group_pad: float,
    gap_y: float,
    elements: dict,
) -> None:
    group = group_map[eid]
    kids = children_of.get(eid, [])

    parent_header_h = 28
    gap_after_parent = 14

    child_y = y0 + parent_header_h + gap_after_parent

    for cid in kids:
        cn = node_map[cid]
        csz = cn.size
        cw = max(csz.width if csz else def_w, def_w - group_pad * 2)
        ch = max(csz.height if csz else def_h, def_h)
        cn.position = Position(
            x0 + group_pad + (cw - (csz.width if csz else def_w)) / 2, child_y + 10
        )
        cn.size = Size(cw, ch)
        child_y += ch + gap_y

    gw = max(def_w + group_pad * 2, 240)
    gh = max(child_y - y0 - gap_y + group_pad, 60)
    group.position = Position(x0, y0)
    group.size = Size(gw, gh)

    n = node_map[eid]
    n.position = Position(x0 + 4, y0 + 4)
    n.size = Size(gw - 8, parent_header_h)
