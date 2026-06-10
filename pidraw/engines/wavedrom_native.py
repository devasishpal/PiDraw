from __future__ import annotations

import json
from typing import Any

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderError

_MAX_SIZE = 500 * 1024

_WDT = 20
_WDT2 = _WDT / 2
_HGH = 20
_HGH2 = _HGH / 2


def _escape(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _parse_wave_char(ch: str, prev: str) -> str:
    if ch == "p":
        return "0"
    if ch == "n":
        return "1"
    if ch == "h":
        return "1"
    if ch == "l":
        return "0"
    if ch == "=":
        return prev if prev else "0"
    if ch == ".":
        return prev if prev else "0"
    if ch in "012zx":
        return ch
    return prev if prev else "0"


def _build_wave_signal(
    wave: str, data: list[str] | None
) -> tuple[list[str], list[str | None], list[float]]:
    if not wave:
        return [], [], []

    points: list[str] = []
    labels: list[str | None] = []
    markers: list[float] = []

    prev = "0"
    x = 0.0
    i = 0

    while i < len(wave):
        ch = wave[i]
        if ch == "|":
            markers.append(x)
            i += 1
            continue

        if ch in "23456789":
            val = "1" if ch in "2468" else "0"
            label_idx = int(ch) - 2
            lbl = data[label_idx] if data and label_idx < len(data) else None
            points.append(val)
            labels.append(lbl)
            prev = val
            x += _WDT
            i += 1
            continue

        val = _parse_wave_char(ch, prev)
        points.append(val)
        labels.append(None)
        prev = val
        x += _WDT
        i += 1

    return points, labels, markers


def _render_wave_signal(
    y: float,
    name: str,
    wave: str,
    labels: list[str | None],
    points: list[str],
    phase: int = 0,
    hgap: float = _WDT,
) -> list[str]:
    parts: list[str] = []
    x0 = hgap * phase
    svg_y = y

    for idx, (pt, lbl) in enumerate(zip(points, labels)):
        x1 = x0 + idx * hgap
        x2 = x1 + hgap
        mid_x = (x1 + x2) / 2

        if pt == "0":
            parts.append(
                f'  <line x1="{x1}" y1="{svg_y + _HGH}" x2="{x2}" y2="{svg_y + _HGH}" '
                f'stroke="#333" stroke-width="2"/>'
            )
        elif pt == "1":
            parts.append(
                f'  <line x1="{x1}" y1="{svg_y}" x2="{x2}" y2="{svg_y}" '
                f'stroke="#333" stroke-width="2"/>'
            )
        elif pt == "z":
            parts.append(
                f'  <line x1="{x1}" y1="{svg_y + _HGH}" x2="{x2}" y2="{svg_y + _HGH}" '
                f'stroke="#333" stroke-width="2" stroke-dasharray="3,3"/>'
            )
        elif pt == "x":
            fill = "#ffcccc"
            parts.append(
                f'  <rect x="{x1}" y="{svg_y}" width="{hgap}" height="{_HGH}" '
                f'fill="{fill}" stroke="none"/>'
            )
            parts.append(
                f'  <line x1="{x1}" y1="{svg_y}" x2="{x2}" y2="{svg_y + _HGH}" '
                f'stroke="#c00" stroke-width="1" stroke-dasharray="2,2"/>'
            )
            parts.append(
                f'  <line x1="{x1}" y1="{svg_y + _HGH}" x2="{x2}" y2="{svg_y}" '
                f'stroke="#c00" stroke-width="1" stroke-dasharray="2,2"/>'
            )

        if idx > 0:
            prev_pt = points[idx - 1]
            if prev_pt in ("0", "l", "h", "1") and pt in ("0", "l", "h", "1"):
                prev_y = svg_y if prev_pt in ("1", "h") else svg_y + _HGH
                curr_y = svg_y if pt in ("1", "h") else svg_y + _HGH
                if prev_y != curr_y:
                    parts.append(
                        f'  <line x1="{x1}" y1="{prev_y}" x2="{x1}" y2="{curr_y}" '
                        f'stroke="#333" stroke-width="2"/>'
                    )

        if lbl:
            parts.append(
                f'  <text x="{mid_x}" y="{svg_y + _HGH2}" text-anchor="middle" '
                f'dominant-baseline="central" font-family="monospace" font-size="12" '
                f'fill="#0066cc">{_escape(lbl)}</text>'
            )

    parts.append(
        f'  <text x="-8" y="{svg_y + _HGH2}" text-anchor="end" '
        f'dominant-baseline="central" font-family="monospace" font-size="13" '
        f'fill="#333" font-weight="bold">{_escape(name)}</text>'
    )

    return parts


def _render_clock(y: float, wave: str, hgap: float = _WDT) -> list[str]:
    parts: list[str] = []
    if not wave:
        return parts

    for i, ch in enumerate(wave):
        x1 = int(i * hgap)
        x2 = int((i + 1) * hgap)
        mid = int(x1 + hgap / 2)

        if ch == "p":
            parts.append(
                f'  <polyline points="{x1},{y + _HGH} {x1},{y} {mid},{y} {mid},{y + _HGH} {x2},{y + _HGH}" '
                f'fill="none" stroke="#333" stroke-width="2"/>'
            )
        elif ch == "n":
            parts.append(
                f'  <polyline points="{x1},{y} {x1},{y + _HGH} {mid},{y + _HGH} {mid},{y} {x2},{y}" '
                f'fill="none" stroke="#333" stroke-width="2"/>'
            )
        elif ch == "0":
            parts.append(
                f'  <line x1="{x1}" y1="{y + _HGH}" x2="{x2}" y2="{y + _HGH}" '
                f'stroke="#333" stroke-width="2"/>'
            )
        elif ch == "1":
            parts.append(
                f'  <line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#333" stroke-width="2"/>'
            )
        elif ch == "h":
            parts.append(
                f'  <polyline points="{x1},{y + _HGH} {x1},{y} {x2},{y}" '
                f'fill="none" stroke="#333" stroke-width="2"/>'
            )
        elif ch == "l":
            parts.append(
                f'  <polyline points="{x1},{y} {x1},{y + _HGH} {x2},{y + _HGH}" '
                f'fill="none" stroke="#333" stroke-width="2"/>'
            )

    return parts


def _parse_wavedrom_json(data: dict[str, Any]) -> list[dict[str, Any]]:
    signals_raw = data.get("signal", [])
    if not isinstance(signals_raw, list):
        raise RenderError("wavedrom", "signal must be an array")

    signals_flat: list[dict[str, Any]] = []
    for item in signals_raw:
        if isinstance(item, dict):
            if "name" in item:
                signals_flat.append(item)
            else:
                for k, v in item.items():
                    if isinstance(v, list):
                        signals_flat.append({"name": k, "wave": "", "children": v})
    return signals_flat


class WaveDromNativeRenderer(BaseRenderer):
    name = "wavedrom"

    def __init__(self) -> None:
        pass

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("wavedrom", "WaveDrom source is empty")
        if "\x00" in source:
            raise RenderError("wavedrom", "WaveDrom source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError("wavedrom", f"WaveDrom source exceeds {_MAX_SIZE // 1024} KB limit")

        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise RenderError("wavedrom", f"Invalid JSON: {exc}")

        signals = _parse_wavedrom_json(data)
        if not signals:
            raise RenderError("wavedrom", "No signals found")

        head = data.get("head", {})
        foot = data.get("foot", {})
        tick_labels = data.get("tick", [])

        hgap = float(data.get("hgap", _WDT))
        row_h = float(data.get("rowheight", _HGH + 40))

        config = data.get("config", {})
        if config:
            hgap = float(config.get("hgap", hgap))

        max_periods = 1
        parsed_signals: list[dict[str, Any]] = []
        for sig in signals:
            wave_str = sig.get("wave", "")
            sig_data = sig.get("data", [])
            points, labels, markers = _build_wave_signal(wave_str, sig_data)
            parsed_signals.append(
                {
                    "name": sig.get("name", ""),
                    "points": points,
                    "labels": labels,
                    "markers": markers,
                    "wave": wave_str,
                }
            )
            max_periods = max(max_periods, len(points))

        canvas_w = max(max_periods * hgap + 120, 200)
        total_signals = len(parsed_signals)
        header_h = 0
        if head:
            header_h = 30

        footer_h = 0
        if foot:
            footer_h = 30

        tick_h = 0
        if tick_labels:
            tick_h = 20

        canvas_h = total_signals * row_h + header_h + footer_h + tick_h + 40

        svg_parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {canvas_w} {canvas_h}" '
            f'width="{canvas_w}" height="{canvas_h}" '
            f'style="background:#ffffff;font-family:monospace">',
        ]

        if head:
            head_text = head.get("text", "")
            svg_parts.append(
                f'  <text x="{canvas_w / 2}" y="20" text-anchor="middle" '
                f'font-family="sans-serif" font-size="14" fill="#333">{_escape(str(head_text))}</text>'
            )

        current_y = header_h + 20
        for idx, sig in enumerate(parsed_signals):
            name = sig["name"]
            points = sig["points"]
            wave_str = sig["wave"]
            svg_parts.append(f'  <g id="signal-{idx}">')

            if wave_str and all(c in "pPnN01hl" for c in wave_str):
                svg_parts.extend(_render_clock(current_y, wave_str, hgap))
            else:
                svg_parts.extend(
                    _render_wave_signal(
                        current_y,
                        name,
                        wave_str,
                        sig["labels"],
                        points,
                        0,
                        hgap,
                    )
                )

            for m_x in sig["markers"]:
                mx = m_x + 100
                svg_parts.append(
                    f'  <line x1="{mx}" y1="{current_y}" x2="{mx}" y2="{current_y + _HGH}" '
                    f'stroke="#999" stroke-width="1" stroke-dasharray="2,2"/>'
                )

            svg_parts.append("  </g>")
            current_y += row_h

        if tick_labels:
            tick_y = current_y
            svg_parts.append('  <g id="ticks">')
            for i, tl in enumerate(tick_labels):
                tx = 100 + i * hgap + hgap / 2
                svg_parts.append(
                    f'  <text x="{tx}" y="{tick_y}" text-anchor="middle" '
                    f'font-family="monospace" font-size="11" fill="#666">{_escape(str(tl))}</text>'
                )
            svg_parts.append("  </g>")

        if foot:
            foot_text = foot.get("text", "")
            svg_parts.append(
                f'  <text x="{canvas_w / 2}" y="{canvas_h - 10}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="12" fill="#666">{_escape(str(foot_text))}</text>'
            )

        svg_parts.append("</svg>")
        return "".join(svg_parts)
