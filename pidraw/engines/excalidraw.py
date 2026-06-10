"""Renderer for Excalidraw diagrams — parses JSON and renders SVG natively."""

from __future__ import annotations

import json
import math
from typing import Any

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderError

_MAX_SIZE = 10 * 1024 * 1024
_FONT_MAP: dict[int, str] = {
    1: "Virgil, 'Comic Sans MS', cursive, sans-serif",
    2: "'Helvetica Neue', Helvetica, Arial, sans-serif",
    3: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
}


def _parse_color(c: str) -> str:
    return c if c.startswith("#") else f"#{c}"


def _render_element(elem: dict[str, Any]) -> str:
    t = elem.get("type", "")
    x = float(elem.get("x", 0))
    y = float(elem.get("y", 0))
    w = float(elem.get("width", 0))
    h = float(elem.get("height", 0))
    sw = float(elem.get("strokeWidth", 2))
    sc = _parse_color(elem.get("strokeColor", "#000000"))
    bg = _parse_color(elem.get("backgroundColor", "transparent"))
    opacity = float(elem.get("opacity", 100)) / 100
    angle = float(elem.get("angle", 0))
    rough = elem.get("roughness", 0)
    fill = bg if bg != "transparent" else "none"

    parts: list[str] = []

    if t == "rectangle":
        rx = rough * 4
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{rx}" ry="{rx}" '
            f'stroke="{sc}" stroke-width="{sw}" fill="{fill}" opacity="{opacity}"/>'
        )
    elif t == "ellipse":
        cx = x + w / 2
        cy = y + h / 2
        parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{w / 2}" ry="{h / 2}" '
            f'stroke="{sc}" stroke-width="{sw}" fill="{fill}" opacity="{opacity}"/>'
        )
    elif t == "diamond":
        pts = f"{x + w / 2},{y} {x + w},{y + h / 2} {x + w / 2},{y + h} {x},{y + h / 2}"
        parts.append(
            f'<polygon points="{pts}" '
            f'stroke="{sc}" stroke-width="{sw}" fill="{fill}" opacity="{opacity}"/>'
        )
    elif t == "text":
        txt = elem.get("text", "")
        fs = float(elem.get("fontSize", 20))
        font_family = _FONT_MAP.get(int(elem.get("fontFamily", 2)), "sans-serif")
        parts.append(
            f'<text x="{x}" y="{y + fs}" font-size="{fs}" '
            f'font-family="{font_family}" '
            f'fill="{sc}" opacity="{opacity}">{_escape(txt)}</text>'
        )
    elif t in ("arrow", "line"):
        pts = elem.get("points", [])
        if not pts or len(pts) < 2:
            pts = [[0, 0], [w, h]]
        abs_pts = [(x + p[0], y + p[1]) for p in pts]
        d = " ".join(f"{'M' if i == 0 else 'L'}{px},{py}" for i, (px, py) in enumerate(abs_pts))
        marker_end = ""
        if t == "arrow":
            marker_end = ' marker-end="url(#arrowhead)"'
        parts.append(
            f'<path d="{d}" stroke="{sc}" stroke-width="{sw}" '
            f'fill="none" opacity="{opacity}"{marker_end}/>'
        )
    elif t == "freedraw":
        pts = elem.get("points", [])
        if pts and len(pts) >= 2:
            abs_pts = [(x + p[0], y + p[1]) for p in pts]
            d = " ".join(f"{'M' if i == 0 else 'L'}{px},{py}" for i, (px, py) in enumerate(abs_pts))
            parts.append(
                f'<path d="{d}" stroke="{sc}" stroke-width="{max(sw, 1)}" '
                f'fill="none" opacity="{opacity}"/>'
            )
    elif t == "image":
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="#e0e0e0" stroke="{sc}" stroke-width="{sw}" '
            f'stroke-dasharray="4,2" opacity="{opacity}"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2}" '
            f'text-anchor="middle" fill="#999" font-size="10">[image]</text>'
        )
    elif t in ("frame", "embeddable"):
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="none" stroke="#ccc" stroke-width="1" '
            f'stroke-dasharray="6,3" opacity="{opacity}"/>'
            f'<text x="{x + 4}" y="{y + 12}" fill="#999" '
            f'font-size="10">{_escape(t)}</text>'
        )

    if angle != 0 and parts:
        cx = x + w / 2
        cy = y + h / 2
        deg = math.degrees(angle)
        parts = [f'<g transform="rotate({deg:.1f},{cx},{cy})">' + "".join(parts) + "</g>"]

    return "".join(parts)


def _escape(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class ExcalidrawRenderer(BaseRenderer):
    """Render Excalidraw JSON exports to SVG — pure Python, no CLI needed."""

    name = "excalidraw"

    def __init__(self, path: str | None = None) -> None:
        pass

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("excalidraw", "Excalidraw source is empty")
        if "\x00" in source:
            raise RenderError("excalidraw", "Excalidraw source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError(
                "excalidraw",
                f"Excalidraw source exceeds {_MAX_SIZE // 1024 // 1024} MB limit",
            )

        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise RenderError("excalidraw", f"Excalidraw source is not valid JSON: {exc}")

        elements = data if isinstance(data, list) else data.get("elements", [])

        # Compute bounding box
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for el in elements:
            ex = el.get("x", 0)
            ey = el.get("y", 0)
            ew = el.get("width", 100)
            eh = el.get("height", 30)
            min_x = min(min_x, ex)
            min_y = min(min_y, ey)
            max_x = max(max_x, ex + ew)
            max_y = max(max_y, ey + eh)

        if not elements:
            min_x = min_y = 0
            max_x = max_y = 600

        pad = 40
        vw = max_x - min_x + pad * 2
        vh = max_y - min_y + pad * 2

        svg_parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{min_x - pad} {min_y - pad} {vw} {vh}" '
            f'width="{vw}" height="{vh}" '
            f'style="background:#ffffff">'
            "<defs>"
            '<marker id="arrowhead" markerWidth="10" markerHeight="10" '
            'refX="9" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
            '<path d="M0,0 L10,5 L0,10 Z" fill="#000" stroke="#000" stroke-width="1"/>'
            "</marker>"
            "</defs>"
        ]

        # Per-element try/except — a single bad element must not abort the whole render
        for i, el in enumerate(elements):
            try:
                svg_parts.append(_render_element(el))
            except Exception as exc:
                svg_parts.append(f"<!-- excalidraw element {i} skipped: {_escape(str(exc))} -->")

        svg_parts.append("</svg>")
        svg = "".join(svg_parts)

        if "<svg" not in svg:
            raise RenderError("excalidraw", "Rendered output does not contain <svg>")

        return svg
