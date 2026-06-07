from __future__ import annotations

from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring

from pidraw.core.models import (
    ArrowStyle,
    Diagram,
    Edge,
    EdgeStyle,
    Group,
    Label,
    Node,
    ShapeType,
    Style,
)
from pidraw.core.shapes import compute_shape_path

_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"
_SVG_ATTR = {"xmlns": _SVG_NS, "xmlns:xlink": _XLINK_NS}

_XML_DECLARATION = '<?xml version="1.0" encoding="utf-8"?>\n'


class SvgBackend:
    def __init__(self, theme: Optional[dict] = None) -> None:
        self._theme = theme or {}
        self._marker_ids: set[str] = set()

    def render(self, diagram: Diagram) -> str:
        vp = diagram.viewport
        vx = vp.x if vp else 0
        vy = vp.y if vp else 0
        vw = vp.width if vp else 800
        vh = vp.height if vp else 600

        root = Element("svg", {
            "xmlns": _SVG_NS,
            "xmlns:xlink": _XLINK_NS,
            "width": str(vw),
            "height": str(vh),
            "viewBox": f"{vx} {vy} {vw} {vh}",
        })

        defs = SubElement(root, "defs")
        self._add_markers(defs, diagram)
        self._add_filters(defs)

        bg = self._theme.get("background")
        if bg is not None:
            _ = SubElement(root, "rect", {
                "width": "100%",
                "height": "100%",
                "fill": bg,
            })

        edges_g = SubElement(root, "g", {"id": "edges"})
        for edge in diagram.edges:
            self._render_edge(edges_g, edge, diagram)

        nodes_g = SubElement(root, "g", {"id": "nodes"})
        for node in diagram.all_nodes():
            self._render_node(nodes_g, node, diagram)

        for group in diagram.groups:
            self._render_group(root, group, diagram)

        raw = tostring(root, encoding="unicode", short_empty_elements=True)
        return _XML_DECLARATION + raw

    def _add_markers(self, defs: Element, diagram: Diagram) -> None:
        for arrow_style in ArrowStyle:
            if arrow_style == ArrowStyle.NONE:
                continue
            mid = f"pidraw-arrow-{arrow_style.value}"
            self._marker_ids.add(mid)
            marker_defs = _ARROW_MARKERS.get(arrow_style)
            if marker_defs is not None:
                marker_elem = Element("marker", {
                    "id": mid,
                    "markerWidth": "10",
                    "markerHeight": "10",
                    "refX": "9",
                    "refY": "5",
                    "orient": "auto",
                    "markerUnits": "userSpaceOnUse",
                })
                path_d, fill, stroke = marker_defs
                SubElement(marker_elem, "path", {
                    "d": path_d,
                    "fill": fill,
                    "stroke": stroke,
                    "stroke-width": "1",
                })
                defs.append(marker_elem)

    def _add_filters(self, defs: Element) -> None:
        shadow_filter = Element("filter", {
            "id": "pidraw-shadow",
            "x": "-10%", "y": "-10%",
            "width": "130%", "height": "130%",
        })
        SubElement(shadow_filter, "feDropShadow", {
            "dx": "2", "dy": "3",
            "stdDeviation": "3",
            "flood-color": "rgba(0,0,0,0.2)",
        })
        defs.append(shadow_filter)

    def _render_node(self, parent: Element, node: Node, diagram: Diagram) -> None:
        pos = node.position
        size = node.size
        if pos is None or size is None:
            return

        style = Style.merge(diagram.style, node.style)
        x, y = pos.x, pos.y
        w, h = size.width, size.height
        shape_type = node.shape.shape_type if node.shape else ShapeType.RECTANGLE

        g = SubElement(parent, "g", {"id": f"node-{node.id}", "class": "node"})

        path_data = compute_shape_path(shape_type, pos, size, style.corner_radius)

        attrs: dict[str, str] = {
            "d": path_data,
            "fill": style.fill_color,
            "fill-opacity": str(style.fill_opacity),
            "stroke": style.stroke_color,
            "stroke-width": str(style.stroke_width),
            "opacity": str(style.opacity),
        }
        if style.stroke_style == EdgeStyle.DASHED:
            attrs["stroke-dasharray"] = f"{style.stroke_width * 4},{style.stroke_width * 4}"
        elif style.stroke_style == EdgeStyle.DOTTED:
            attrs["stroke-dasharray"] = f"{style.stroke_width},{style.stroke_width * 3}"

        SubElement(g, "path", attrs)

        if style.shadow:
            attrs["filter"] = "url(#pidraw-shadow)"

        if node.label is not None and node.label.text:
            self._render_label(g, node.label, x + w / 2, y + h / 2, style)

        if node.children:
            for child in node.children:
                self._render_node(g, child, diagram)

    def _render_edge(self, parent: Element, edge: Edge, diagram: Diagram) -> None:
        src_node = diagram.get_node(edge.source)
        tgt_node = diagram.get_node(edge.target)
        if src_node is None or tgt_node is None:
            return
        src_pos = src_node.position
        tgt_pos = tgt_node.position
        src_size = src_node.size
        tgt_size = tgt_node.size
        if src_pos is None or tgt_pos is None or src_size is None or tgt_size is None:
            return

        style = Style.merge(diagram.style, edge.style)

        x1 = src_pos.x + src_size.width / 2
        y1 = src_pos.y + src_size.height / 2
        x2 = tgt_pos.x + tgt_size.width / 2
        y2 = tgt_pos.y + tgt_size.height / 2

        edge_id = f"edge-{edge.id}" if edge.id else ""
        g = SubElement(parent, "g", {"id": edge_id, "class": "edge"})

        path_attrs: dict[str, str] = {
            "d": f"M{x1},{y1}L{x2},{y2}",
            "fill": "none",
            "stroke": style.stroke_color,
            "stroke-width": str(style.stroke_width),
            "opacity": str(style.opacity),
        }
        if style.stroke_style == EdgeStyle.DASHED:
            path_attrs["stroke-dasharray"] = f"{style.stroke_width * 4},{style.stroke_width * 4}"
        elif style.stroke_style == EdgeStyle.DOTTED:
            path_attrs["stroke-dasharray"] = f"{style.stroke_width},{style.stroke_width * 3}"
        elif style.stroke_style == EdgeStyle.BOLD:
            path_attrs["stroke-width"] = str(style.stroke_width * 2.5)

        if edge.waypoints:
            d = f"M{x1},{y1}"
            for wp in edge.waypoints:
                d += f"L{wp.x},{wp.y}"
            d += f"L{x2},{y2}"
            path_attrs["d"] = d

        arrow_end = ArrowStyle(style.arrow_end) if isinstance(style.arrow_end, str) else style.arrow_end
        if arrow_end != ArrowStyle.NONE:
            path_attrs["marker-end"] = f"url(#pidraw-arrow-{arrow_end.value})"
        arrow_start = ArrowStyle(style.arrow_start) if isinstance(style.arrow_start, str) else style.arrow_start
        if arrow_start != ArrowStyle.NONE:
            path_attrs["marker-start"] = f"url(#pidraw-arrow-{arrow_start.value})"

        SubElement(g, "path", path_attrs)

        if edge.label is not None and edge.label.text:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            self._render_label(g, edge.label, mx, my - 8, style)

    def _render_label(
        self,
        parent: Element,
        label: Label,
        cx: float,
        cy: float,
        style: Style,
    ) -> None:
        text = SubElement(parent, "text", {
            "x": str(cx),
            "y": str(cy),
            "text-anchor": "middle",
            "dominant-baseline": "central",
            "font-family": style.font_family,
            "font-size": f"{style.font_size}px",
            "font-weight": style.font_weight.value,
            "fill": style.text_color,
        })
        text.text = label.text

    def _render_group(self, parent: Element, group: Group, diagram: Diagram) -> None:
        g = SubElement(parent, "g", {"id": f"group-{group.id}", "class": "group"})
        pos = group.position
        size = group.size
        if pos is not None and size is not None:
            style = Style.merge(diagram.style, group.style)
            SubElement(g, "rect", {
                "x": str(pos.x),
                "y": str(pos.y),
                "width": str(size.width),
                "height": str(size.height),
                "fill": style.fill_color,
                "fill-opacity": "0.05",
                "stroke": style.stroke_color,
                "stroke-width": str(style.stroke_width),
                "stroke-dasharray": "6,3",
            })
            if group.label is not None and group.label.text:
                self._render_label(g, group.label, pos.x + size.width / 2, pos.y + 16, style)

        for node in group.nodes:
            self._render_node(g, node, diagram)
        for edge in group.edges:
            self._render_edge(g, edge, diagram)
        for child_group in group.groups:
            self._render_group(g, child_group, diagram)


_ARROW_MARKERS: dict[ArrowStyle, tuple[str, str, str]] = {
    ArrowStyle.TRIANGLE: ("M0,0 L10,5 L0,10 Z", "none", "#333"),
    ArrowStyle.TRIANGLE_FILLED: ("M0,0 L10,5 L0,10 Z", "#333", "#333"),
    ArrowStyle.DIAMOND: ("M0,5 L5,0 L10,5 L5,10 Z", "none", "#333"),
    ArrowStyle.DIAMOND_FILLED: ("M0,5 L5,0 L10,5 L5,10 Z", "#333", "#333"),
    ArrowStyle.CIRCLE: ("M0,5 a5,5 0 1,1 10,0 a5,5 0 1,1 -10,0", "none", "#333"),
    ArrowStyle.CIRCLE_FILLED: ("M0,5 a5,5 0 1,1 10,0 a5,5 0 1,1 -10,0", "#333", "#333"),
    ArrowStyle.OPEN: ("M0,0 L8,4 L0,8 L2,4 Z", "none", "#333"),
    ArrowStyle.BOX: ("M0,0 h8 v8 h-8 Z", "none", "#333"),
    ArrowStyle.CROW: ("M0,0 L6,5 L0,10 M6,0 L12,5 L6,10", "none", "#333"),
}
