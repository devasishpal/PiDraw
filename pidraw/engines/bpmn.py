"""Renderer for BPMN diagrams via ``bpmn-to-svg`` CLI (npm) or native fallback."""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Optional

try:
    import drawsvg as _dw

    _HAS_DRAWSVG = True
except ImportError:
    _dw = None
    _HAS_DRAWSVG = False

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError, RenderTimeoutError

_MAX_SIZE = 100 * 1024


BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"


def _ns(tag: str, ns: str) -> str:
    return f"{{{ns}}}{tag}"


class BPMNElement:
    def __init__(self, id: str, name: str, type: str) -> None:
        self.id = id
        self.name = name or id
        self.type = type  # startEvent, endEvent, task, exclusiveGateway, etc.
        self.x: float = 0
        self.y: float = 0
        self.w: float = 100
        self.h: float = 50


class BPMNFlow:
    def __init__(self, id: str, source: str, target: str, label: str = "") -> None:
        self.id = id
        self.source = source
        self.target = target
        self.label = label


def _parse_bpmn_xml(source: str) -> tuple[list[BPMNElement], list[BPMNFlow]]:
    root = ET.fromstring(source)
    elements: dict[str, BPMNElement] = {}
    flows: list[BPMNFlow] = []

    # Process bpmn:process
    for process in root.iter(_ns("process", BPMN_NS)):
        for child in process:
            tag = child.tag
            if "}" in tag:
                local = tag.split("}")[1]
            else:
                local = tag
            el_id = child.get("id", "")
            el_name = child.get("name", "") or el_id
            if local in (
                "startEvent",
                "endEvent",
                "task",
                "serviceTask",
                "userTask",
                "exclusiveGateway",
                "parallelGateway",
                "inclusiveGateway",
                "intermediateCatchEvent",
                "subProcess",
                "callActivity",
            ):
                el = BPMNElement(el_id, el_name, local)
                if local in ("startEvent", "endEvent", "intermediateCatchEvent"):
                    el.w, el.h = 36, 36
                elif local in ("exclusiveGateway", "parallelGateway", "inclusiveGateway"):
                    el.w, el.h = 50, 50
                elif local == "subProcess":
                    el.w, el.h = 140, 80
                else:
                    el.w, el.h = 100, 60
                elements[el_id] = el
            elif local == "sequenceFlow":
                sf_id = child.get("id", "")
                src = child.get("sourceRef", "")
                tgt = child.get("targetRef", "")
                name = child.get("name", "") or ""
                flows.append(BPMNFlow(sf_id, src, tgt, name))

    # Read positions from BPMNDiagram
    for diagram in root.iter(_ns("BPMNDiagram", BPMNDI_NS)):
        for plane in diagram.iter(_ns("BPMNPlane", BPMNDI_NS)):
            for shape in plane.iter(_ns("BPMNShape", BPMNDI_NS)):
                el_ref = shape.get("bpmnElement", "")
                if el_ref in elements:
                    bounds = shape.find(_ns("Bounds", DC_NS))
                    if bounds is not None:
                        el = elements[el_ref]
                        el.x = float(bounds.get("x", 0))
                        el.y = float(bounds.get("y", 0))
                        el.w = float(bounds.get("width", 100))
                        el.h = float(bounds.get("height", 50))
            for edge in plane.iter(_ns("BPMNEdge", BPMNDI_NS)):
                pass  # waypoints not needed for our simple rendering

    return list(elements.values()), flows


def _parse_bpmn_json(source: str) -> tuple[list[BPMNElement], list[BPMNFlow]]:
    data = json.loads(source)
    elements: dict[str, BPMNElement] = {}
    flows: list[BPMNFlow] = []

    # JSON format from bpmn.io / Camunda Modeler
    # Shape types: bpmn:StartEvent, bpmn:EndEvent, bpmn:Task, etc.
    for shape in data.get("shapes", []):
        shape_id = shape.get("id", "")
        labels = shape.get("labels", [])
        name = labels[0].get("text", "") if labels else ""
        # Extract type from resourceId or shape type
        raw_type = shape.get("type", "").split(":")[-1] if ":" in shape.get("type", "") else ""
        if raw_type:
            elements[shape_id] = BPMNElement(shape_id, name, raw_type)
            bounds = shape.get("bounds", {})
            if bounds:
                elements[shape_id].x = bounds.get("x", 0)
                elements[shape_id].y = bounds.get("y", 0)
                elements[shape_id].w = bounds.get("width", 100)
                elements[shape_id].h = bounds.get("height", 50)

    for edge in data.get("edges", []):
        edge_id = edge.get("id", "")
        src = edge.get("sourceId", "")
        tgt = edge.get("targetId", "")
        labels = edge.get("labels", [])
        label = labels[0].get("text", "") if labels else ""
        flows.append(BPMNFlow(edge_id, src, tgt, label))

    return list(elements.values()), flows


def _render_bpmn_svg(elements: list[BPMNElement], flows: list[BPMNFlow]) -> str:
    dw = _dw
    if dw is None:
        raise RuntimeError("drawsvg is required for native BPMN rendering (pip install drawsvg)")

    # Auto-layout if no positions set
    has_positions = any(el.x != 0 or el.y != 0 for el in elements)
    if not has_positions and elements:
        cx = 80
        cy = 60
        ygap = 40
        for i, el in enumerate(elements):
            el.x = cx
            el.y = cy + i * (max(el.h, 50) + ygap)

    # Compute canvas size
    min_x = min((el.x for el in elements), default=0)
    min_y = min((el.y for el in elements), default=0)
    max_x = max((el.x + el.w for el in elements), default=600)
    max_y = max((el.y + el.h for el in elements), default=400)
    pad = 40
    vw = max_x - min_x + pad * 2
    vh = max_y - min_y + pad * 2

    dwg = dw.Drawing(vw, vh, origin=(min_x - pad, min_y - pad))

    # Build element lookup
    el_map = {el.id: el for el in elements}

    # Draw edges (flows) first so they're behind nodes
    for flow in flows:
        src = el_map.get(flow.source)
        tgt = el_map.get(flow.target)
        if src and tgt:
            x1 = src.x + src.w / 2
            y1 = src.y + src.h
            x2 = tgt.x + tgt.w / 2
            y2 = tgt.y
            dwg.append(dw.Line(x1, y1, x2, y2, stroke="#333", stroke_width=1.5))
            _draw_arrowhead(dwg, x1, y1, x2, y2, dw)
            if flow.label:
                mx = (x1 + x2) / 2
                my = (y1 + y2) / 2
                dwg.append(
                    dw.Text(
                        flow.label,
                        font_size=11,
                        x=mx,
                        y=my - 5,
                        fill="#333",
                        text_anchor="middle",
                        font_family="sans-serif",
                    )
                )

    # Draw nodes
    for el in elements:
        _draw_bpmn_element(dwg, el, dw)

    return dwg.as_svg()


def _draw_bpmn_element(dwg: Any, el: BPMNElement, dw: Any) -> None:
    cx = el.x + el.w / 2
    cy = el.y + el.h / 2
    fill = "#fff"
    stroke = "#333"
    sw = 2

    if el.type == "startEvent":
        dwg.append(
            dw.Circle(cx, cy, min(el.w, el.h) / 2, fill=fill, stroke=stroke, stroke_width=sw)
        )
        dwg.append(
            dw.Text(
                el.name,
                font_size=11,
                x=cx,
                y=el.y + el.h + 14,
                fill="#333",
                text_anchor="middle",
                font_family="sans-serif",
            )
        )
    elif el.type == "endEvent":
        r = min(el.w, el.h) / 2
        dwg.append(dw.Circle(cx, cy, r, fill=fill, stroke=stroke, stroke_width=sw))
        dwg.append(dw.Circle(cx, cy, r - 4, fill="none", stroke=stroke, stroke_width=sw + 1))
        dwg.append(
            dw.Text(
                el.name,
                font_size=11,
                x=cx,
                y=el.y + el.h + 14,
                fill="#333",
                text_anchor="middle",
                font_family="sans-serif",
            )
        )
    elif el.type in ("exclusiveGateway",):
        path = f"M{cx},{el.y} L{el.x + el.w},{cy} L{cx},{el.y + el.h} L{el.x},{cy} Z"
        dwg.append(dw.Path(path, fill=fill, stroke=stroke, stroke_width=sw))
        dwg.append(
            dw.Text(
                el.name,
                font_size=11,
                x=cx,
                y=el.y + el.h + 14,
                fill="#333",
                text_anchor="middle",
                font_family="sans-serif",
            )
        )
    elif el.type in ("parallelGateway",):
        path = f"M{cx},{el.y} L{el.x + el.w},{cy} L{cx},{el.y + el.h} L{el.x},{cy} Z"
        dwg.append(dw.Path(path, fill=fill, stroke=stroke, stroke_width=sw))
        dwg.append(dw.Line(cx - 6, cy, cx + 6, cy, stroke=stroke, stroke_width=2))
        dwg.append(dw.Line(cx, cy - 6, cx, cy + 6, stroke=stroke, stroke_width=2))
        dwg.append(
            dw.Text(
                el.name,
                font_size=11,
                x=cx,
                y=el.y + el.h + 14,
                fill="#333",
                text_anchor="middle",
                font_family="sans-serif",
            )
        )
    elif el.type in ("intermediateCatchEvent",):
        r = min(el.w, el.h) / 2
        dwg.append(dw.Circle(cx, cy, r, fill=fill, stroke=stroke, stroke_width=sw))
        dwg.append(dw.Circle(cx, cy, r - 3, fill="none", stroke=stroke, stroke_width=1))
        dwg.append(
            dw.Text(
                el.name,
                font_size=11,
                x=cx,
                y=el.y + el.h + 14,
                fill="#333",
                text_anchor="middle",
                font_family="sans-serif",
            )
        )
    else:
        # task, serviceTask, userTask, subProcess, callActivity — rounded rect
        r = 6
        dwg.append(
            dw.Rectangle(
                el.x, el.y, el.w, el.h, rx=r, ry=r, fill=fill, stroke=stroke, stroke_width=sw
            )
        )
        dwg.append(
            dw.Text(
                el.name,
                font_size=12,
                x=cx,
                y=cy + 4,
                fill="#333",
                text_anchor="middle",
                font_family="sans-serif",
            )
        )


def _draw_arrowhead(dwg: Any, x1: float, y1: float, x2: float, y2: float, dw: Any) -> None:
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 8
    ax = x2 - size * math.cos(angle)
    ay = y2 - size * math.sin(angle)
    p1x = ax - size * 0.4 * math.sin(angle)
    p1y = ay + size * 0.4 * math.cos(angle)
    p2x = ax + size * 0.4 * math.sin(angle)
    p2y = ay - size * 0.4 * math.cos(angle)
    path = f"M{x2},{y2} L{p1x},{p1y} L{p2x},{p2y} Z"
    dwg.append(dw.Path(path, fill="#333", stroke="none"))


class BPMNRenderer(BaseRenderer):
    """Render BPMN 2.0 XML/JSON diagrams to SVG."""

    name = "bpmn"

    def __init__(self, path: str | None = None) -> None:
        self._path = path
        self._resolved: str | None = None
        try:
            self._resolved = path or self._find_bpmn()
            if not self._resolved:
                raise EngineNotAvailableError("bpmn-to-svg")
        except EngineNotAvailableError:
            self._resolved = None

    @staticmethod
    def _find_bpmn() -> str | None:
        return shutil.which("bpmn-to-svg") or shutil.which("bpmn-svg")

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("bpmn", "BPMN source is empty")
        if "\x00" in source:
            raise RenderError("bpmn", "BPMN source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError("bpmn", f"BPMN source exceeds {_MAX_SIZE // 1024} KB limit")

        if self._resolved is not None:
            try:
                return self._run_cli(source)
            except (RenderError, RenderTimeoutError):
                pass
        return self._run_native(source)

    def _run_cli(self, source: str) -> str:
        tmp_dir: Optional[str] = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="pidraw_bpmn_")
            ext = ".json" if source.strip().startswith("{") else ".bpmn"
            input_path = os.path.join(tmp_dir, f"input{ext}")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write(source)
            assert self._resolved is not None
            cmd = [self._resolved, "generate", "--input", input_path, "--output-dir", tmp_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RenderError(
                    "bpmn",
                    f"bpmn-to-svg failed (code {result.returncode}): {result.stderr.strip()}",
                )
            svg_files = [f for f in os.listdir(tmp_dir) if f.endswith(".svg")]
            if not svg_files:
                raise RenderError("bpmn", "bpmn-to-svg produced no SVG output file")
            output_path = os.path.join(tmp_dir, svg_files[0])
            with open(output_path, "r", encoding="utf-8") as f:
                svg = f.read()
            if not svg.strip():
                raise RenderError("bpmn", "bpmn-to-svg returned empty SVG")
            if "<svg" not in svg:
                raise RenderError("bpmn", "bpmn-to-svg output does not contain <svg>")
            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("bpmn", f"bpmn-to-svg returned malformed XML: {exc}")
            if self._cli_output_is_empty(svg):
                raise RenderError("bpmn", "bpmn-to-svg produced SVG with no visible content")
            return svg
        except subprocess.TimeoutExpired:
            raise RenderTimeoutError("bpmn", 60)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("bpmn", f"bpmn-to-svg error: {exc}")
        finally:
            if tmp_dir and os.path.isdir(tmp_dir):
                import shutil as sh

                sh.rmtree(tmp_dir, ignore_errors=True)

    @staticmethod
    def _cli_output_is_empty(svg: str) -> bool:
        """Check if CLI-produced SVG has no visible diagram content."""
        after_defs = svg.split("</defs>")[-1] if "</defs>" in svg else svg
        visible = len(
            re.findall(
                r"<(rect|circle|ellipse|path|text|line|polygon)[\s>]", after_defs, re.IGNORECASE
            )
        )
        return visible < len(re.findall(r"<marker[\s>]", svg, re.IGNORECASE)) + 1

    def _run_native(self, source: str) -> str:
        """Native BPMN renderer using drawsvg — no CLI needed."""
        try:
            stripped = source.strip()
            if stripped.startswith("{"):
                elements, flows = _parse_bpmn_json(source)
            else:
                elements, flows = _parse_bpmn_xml(source)
            if not elements:
                raise RenderError("bpmn", "No BPMN elements found in source")
            svg = _render_bpmn_svg(elements, flows)
            if "<svg" not in svg:
                raise RenderError("bpmn", "Native renderer produced invalid SVG")
            return svg
        except ET.ParseError as exc:
            raise RenderError("bpmn", f"Failed to parse BPMN XML: {exc}")
        except json.JSONDecodeError as exc:
            raise RenderError("bpmn", f"Failed to parse BPMN JSON: {exc}")
        except ImportError as exc:
            raise RenderError("bpmn", f"Missing dependency: pip install drawsvg — {exc}")
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("bpmn", f"Native BPMN render failed: {exc}")
