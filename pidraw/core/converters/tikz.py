"""TikZ-to-Diagram converter — supports a practical subset of TikZ for diagrams."""

from __future__ import annotations

import re
from typing import Any

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

_TIKZ_COMMENT_RE = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
_NODE_DEF_RE = re.compile(
    r"\\node\s*"
    r"(?:\[([^\]]*)\])?\s*"  # style options
    r"(?:\(([\w\d_-]+)\))?\s*"  # name
    r"(?:at\s*\(([^)]*)\))?\s*"  # position
    r"(?:\{([^}]*)\})?\s*"  # label text
    r";",
    re.DOTALL,
)
_EDGE_DEF_RE = re.compile(
    r"\\(?:draw|path)\s*"
    r"(?:\[([^\]]*)\])?\s*"  # style options
    r"\(([\w\d_.-]+)\)\s*"  # source
    r"("
    r"(?:[-=<>]+(?:\s*\([\w\d_.-]+\)\s*)?)*"  # path ops with intermediate nodes
    r"[-=<>]+"
    r")"
    r"\s*\(([\w\d_.-]+)\)"  # target
    r"\s*(?:node\[([^\]]*)\]\s*\{([^}]*)\})?\s*"  # optional edge label
    r"\s*;",
    re.DOTALL,
)
_SCOPE_RE = re.compile(
    r"\\begin{scope}\s*(?:\[([^\]]*)\])?\s*(.*?)\\end{scope}",
    re.DOTALL,
)
_MATRIX_RE = re.compile(
    r"\\matrix\s*(?:\[([^\]]*)\])?\s*(?:\(([\w\d_-]+)\))?\s*\{"
    r"(.*?)\}",
    re.DOTALL,
)
_PATH_SEG_RE = re.compile(
    r"\(([\w\d_.-]+)\)\s*"  # node reference
    r"((?:[-=<>]+)"  # connector
    r"(?:\s*\([\w\d_.-]+\)\s*[-=<>]+)*)"  # optional intermediate stops
)
_NODE_REF_IN_PATH = re.compile(r"\(([\w\d_.-]+)\)")
_OPTION_SPLIT_RE = re.compile(r",\s*")
_ARROW_OPTS_RE = re.compile(r"[-=]+>|<[-=]+|<->|=>|<=>")

# Named TikZ colors
_TIKZ_COLORS: dict[str, str] = {
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "cyan": "#00ffff",
    "magenta": "#ff00ff",
    "yellow": "#ffff00",
    "black": "#000000",
    "white": "#ffffff",
    "gray": "#808080",
    "grey": "#808080",
    "darkgray": "#404040",
    "lightgray": "#d3d3d3",
    "brown": "#a52a2a",
    "lime": "#00ff00",
    "olive": "#808000",
    "orange": "#ffa500",
    "pink": "#ffc0cb",
    "purple": "#800080",
    "teal": "#008080",
    "violet": "#8a2be2",
}


def _parse_color(c: str) -> str:
    return _TIKZ_COLORS.get(c.lower(), c if c.startswith("#") else c)


@register_converter("tikz")
class TikzConverter(DiagramConverter):
    """Convert TikZ diagram source into the internal Diagram model.

    Supports a practical subset of TikZ commonly used for diagrams:
    ``\\node``, ``\\draw``, ``\\path``, ``\\scope``, basic styles,
    and common shape types.
    """

    language = "tikz"

    def parse(self, source: str) -> Diagram:
        source = _TIKZ_COMMENT_RE.sub("", source)
        diagram = Diagram(id="tikz_diagram", title="TikZ Diagram")
        diagram.layout = Layout(LayoutType.LAYERED, "TB", 50, 80)
        diagram.metadata["engine"] = "tikz-native"

        global_style: dict[str, Any] = {}
        source = self._process_scopes(source, global_style, diagram)
        source = self._process_matrix(source, global_style, diagram)
        self._process_nodes(source, global_style, diagram)
        self._process_edges(source, global_style, diagram)
        self._ensure_positions(diagram)
        return diagram

    def _process_scopes(self, source: str, global_style: dict[str, Any], diagram: Diagram) -> str:
        def _replacer(m: re.Match) -> str:
            opts = m.group(1) or ""
            body = m.group(2)
            scope_style = dict(global_style)
            if opts:
                scope_style.update(self._parse_options(opts))
            self._process_nodes(body, scope_style, diagram)
            self._process_edges(body, scope_style, diagram)
            return ""

        return _SCOPE_RE.sub(_replacer, source)

    def _process_matrix(self, source: str, global_style: dict[str, Any], diagram: Diagram) -> str:
        def _replacer(m: re.Match) -> str:
            opts = m.group(1) or ""
            name = m.group(2)
            body = m.group(3)
            matrix_style = dict(global_style)
            if opts:
                matrix_style.update(self._parse_options(opts))
            rows = re.split(r"\\\\", body)
            for row_idx, row in enumerate(rows):
                cells = re.split(r"&", row)
                for col_idx, cell_content in enumerate(cells):
                    cell_content = cell_content.strip()
                    if not cell_content:
                        continue
                    cell_id = f"{name or 'matrix'}_{row_idx}_{col_idx}"
                    label_text = cell_content
                    style = Style(fill_color="#f0f0f0", stroke_color="#cccccc")
                    node = Node(
                        id=cell_id,
                        label=Label(text=label_text),
                        shape=Shape(shape_type=ShapeType.RECTANGLE),
                        size=Size(width=80, height=30),
                        style=style,
                    )
                    diagram.add_node(node)
            return ""

        return _MATRIX_RE.sub(_replacer, source)

    def _process_nodes(self, source: str, parent_style: dict[str, Any], diagram: Diagram) -> None:
        for match in _NODE_DEF_RE.finditer(source):
            opts_str = match.group(1) or ""
            node_id = match.group(2)
            pos_str = match.group(3)
            label_text = match.group(4) or (node_id or "")

            if not node_id:
                continue

            opts = self._parse_options(opts_str)
            effective = dict(parent_style)
            effective.update(opts)

            shape_type, node_style = self._apply_node_style(effective)
            text_len = len(label_text.strip()) if label_text else 0
            nw = max(60, text_len * 8 + 20)
            nh = 36
            node = Node(
                id=node_id,
                label=Label(text=label_text.strip()),
                shape=Shape(shape_type=shape_type),
                size=Size(width=nw, height=nh),
                style=node_style,
            )
            if pos_str:
                parts = pos_str.split(",")
                if len(parts) >= 2:
                    try:
                        node.position = Position(
                            x=float(parts[0].strip()),
                            y=float(parts[1].strip()),
                        )
                    except ValueError:
                        pass
            diagram.add_node(node)

    def _process_edges(self, source: str, parent_style: dict[str, Any], diagram: Diagram) -> None:
        for match in _EDGE_DEF_RE.finditer(source):
            opts_str = match.group(1) or ""
            src_id = match.group(2)
            tgt_id = match.group(4)
            label_text = match.group(6) or ""

            opts = self._parse_options(opts_str)
            effective = dict(parent_style)
            effective.update(opts)

            edge_style, arrow_start, arrow_end = self._parse_edge_style(effective)

            edge = Edge(
                id=f"{src_id}->{tgt_id}",
                source=src_id,
                target=tgt_id,
                label=Label(text=label_text) if label_text else None,
                style=Style(
                    stroke_style=edge_style,
                    arrow_start=arrow_start,
                    arrow_end=arrow_end,
                    stroke_color=effective.get("stroke_color", "#333333"),
                    stroke_width=effective.get("stroke_width", 1.5),
                ),
            )
            diagram.add_edge(edge)

    def _apply_node_style(self, opts: dict[str, Any]) -> tuple[ShapeType, Style]:
        shape_type = ShapeType.RECTANGLE
        if opts.get("circle"):
            shape_type = ShapeType.CIRCLE
        elif opts.get("ellipse"):
            shape_type = ShapeType.ELLIPSE
        elif opts.get("diamond"):
            shape_type = ShapeType.DIAMOND

        style = Style(
            stroke_color=opts.get("stroke_color", "#333333"),
            stroke_width=opts.get("stroke_width", 1.5),
            fill_color=opts.get("fill_color", "#ffffff"),
            text_color=opts.get("text_color", "#333333"),
            font_size=opts.get("font_size", 14.0),
        )
        if opts.get("rounded_corners"):
            style.corner_radius = opts["rounded_corners"]
        if opts.get("dashed"):
            style.stroke_style = EdgeStyle.DASHED
        elif opts.get("dotted"):
            style.stroke_style = EdgeStyle.DOTTED

        return shape_type, style

    def _parse_edge_style(self, opts: dict[str, Any]) -> tuple[EdgeStyle, ArrowStyle, ArrowStyle]:
        edge_style = EdgeStyle.SOLID
        arrow_start = ArrowStyle.NONE
        arrow_end = ArrowStyle.NONE

        if opts.get("dashed"):
            edge_style = EdgeStyle.DASHED
        elif opts.get("dotted"):
            edge_style = EdgeStyle.DOTTED

        arrow = opts.get("arrow", "")
        if "->" in arrow or arrow.endswith(">"):
            arrow_end = ArrowStyle.TRIANGLE_FILLED
        if "<-" in arrow or arrow.startswith("<"):
            arrow_start = ArrowStyle.TRIANGLE_FILLED

        return edge_style, arrow_start, arrow_end

    def _parse_options(self, opts_str: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if not opts_str.strip():
            return result

        parts = _OPTION_SPLIT_RE.split(opts_str.strip())
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if "=" in part:
                key, val = part.split("=", 1)
                key = key.strip().lower()
                val = val.strip()
                self._set_option(result, key, val)
            elif part.lower() in ("thick", "very thick", "semithick", "ultra thick"):
                widths = {"ultra thick": 3.0, "very thick": 2.5, "thick": 2.0, "semithick": 1.5}
                result["stroke_width"] = widths.get(part.lower(), 2.0)
            elif part.lower() in ("thin", "very thin", "ultra thin"):
                widths = {"ultra thin": 0.4, "very thin": 0.6, "thin": 0.8}
                result["stroke_width"] = widths.get(part.lower(), 0.8)
            elif part.lower() == "dashed":
                result["dashed"] = True
            elif part.lower() == "dotted":
                result["dotted"] = True
            elif part.lower() == "solid":
                result["dashed"] = False
                result["dotted"] = False
            elif part.lower().startswith("rounded corners"):
                parts2 = part.split("=", 1)
                radius = 4.0
                if len(parts2) > 1:
                    try:
                        radius = float(parts2[1].strip().rstrip("pt"))
                    except ValueError:
                        pass
                result["rounded_corners"] = radius
            elif part.lower() in _TIKZ_COLORS:
                result["stroke_color"] = _TIKZ_COLORS[part.lower()]
            elif part == "->" or part == "=>":
                result["arrow"] = part
            elif part == "<-" or part == "<->" or part == "<=>" or part == "<=":
                result["arrow"] = part
            elif part.lower() in ("rectangle", "circle", "ellipse", "diamond"):
                result[part.lower()] = True
            elif part.lower().startswith("font="):
                sizes = {
                    r"\tiny": 8,
                    r"\scriptsize": 9,
                    r"\footnotesize": 10,
                    r"\small": 11,
                    r"\normalsize": 12,
                    r"\large": 14,
                    r"\Large": 16,
                    r"\LARGE": 18,
                    r"\huge": 20,
                    r"\Huge": 24,
                }
                font_val = part.split("=", 1)[1].strip()
                result["font_size"] = sizes.get(font_val, 12)
            elif (
                part.lower().startswith("above")
                or part.lower().startswith("below")
                or part.lower().startswith("left")
                or part.lower().startswith("right")
                or part.lower().startswith("at ")
                or part.lower().startswith("midway")
                or part.lower().startswith("sloped")
                or part.lower() == "auto"
            ):
                nodes = part.lower().split("=", 1)
                result[nodes[0]] = nodes[1] if len(nodes) > 1 else True
            elif part.lower().startswith("scale="):
                try:
                    result["scale"] = float(part.split("=", 1)[1].strip())
                except ValueError:
                    pass

        return result

    def _set_option(self, result: dict[str, Any], key: str, val: str) -> None:
        if key in ("draw", "stroke"):
            result["stroke_color"] = _parse_color(val)
        elif key in ("fill", "bg"):
            color = _parse_color(val)
            result["fill_color"] = color
            if not any(k in result for k in ("draw", "stroke")):
                result["stroke_color"] = color
        elif key in ("text", "color", "fontcolor"):
            result["text_color"] = _parse_color(val)
        elif key == "line width":
            try:
                result["stroke_width"] = float(val.rstrip("ptmm "))
            except ValueError:
                pass
        elif key == "thick":
            result["stroke_width"] = 2.0
        elif key == "thin":
            result["stroke_width"] = 0.8
        elif key == "opacity":
            try:
                result["fill_opacity"] = float(val)
            except ValueError:
                pass
        elif key == "text opacity":
            try:
                result["opacity"] = float(val)
            except ValueError:
                pass
        elif key == "font":
            result["font"] = val
        elif key == "scale":
            try:
                result["scale"] = float(val)
            except ValueError:
                pass

    def _ensure_positions(self, diagram: Diagram) -> None:
        """Assign positions to nodes that don't have explicit positions."""
        nodes_with_pos = [n for n in diagram.all_nodes() if n.position is not None]
        if nodes_with_pos:
            return

        nodes = diagram.all_nodes()
        if not nodes:
            return
        layout = diagram.layout or Layout()
        gap_x = layout.node_spacing * 4
        gap_y = layout.layer_spacing * 4

        deps: dict[str, list[str]] = {n.id: [] for n in nodes}
        for e in diagram.edges:
            if e.source in deps:
                deps[e.source].append(e.target)

        layers: list[list[str]] = []
        remaining = set(deps.keys())
        while remaining:
            layer = [
                n for n in remaining if not any(t in remaining and t != n for t in deps.get(n, []))
            ]
            if not layer:
                layer = [remaining.pop()]
            layers.append(layer)
            remaining -= set(layer)

        for layer_idx, layer_nodes in enumerate(layers):
            for col_idx, nid in enumerate(layer_nodes):
                node = diagram.get_node(nid)
                if node is not None:
                    node.position = Position(
                        x=col_idx * gap_x + layout.padding,
                        y=layer_idx * gap_y + layout.padding,
                    )

        from pidraw.core.models import Viewport

        positions = [n.position for n in nodes if n.position]
        sizes = [n.size for n in nodes if n.size and n.position]
        if positions and sizes:
            min_x = min(p.x for p in positions)
            min_y = min(p.y for p in positions)
            max_x = max(p.x + s.width for p, s in zip(positions, sizes))
            max_y = max(p.y + s.height for p, s in zip(positions, sizes))
            cw = max_x - min_x
            ch = max_y - min_y
            pad = max(layout.padding * 2, cw * 0.15, ch * 0.15)
            diagram.viewport = Viewport(
                x=min_x - pad,
                y=min_y - pad,
                width=cw + pad * 2,
                height=ch + pad * 2,
            )
