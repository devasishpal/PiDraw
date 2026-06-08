from __future__ import annotations

import re
from xml.etree.ElementTree import Element, fromstring, register_namespace, tostring

_SVG_NS = "http://www.w3.org/2000/svg"

_XML_DECL_RE = re.compile(r"^<\?xml[^>]*>\s*", re.IGNORECASE)

_WEB_SAFE_FONTS: dict[str, str] = {
    "sans-serif": "Arial, Helvetica, sans-serif",
    "serif": "Georgia, 'Times New Roman', serif",
    "monospace": "'Courier New', Courier, monospace",
}


class QualityProcessor:
    def __init__(
        self,
        normalize_viewbox: bool = True,
        fix_text_alignment: bool = True,
        fix_arrow_heads: bool = True,
        clean_spacing: bool = True,
        sharp_paths: bool = True,
        normalize_fonts: bool = True,
        normalize_strokes: bool = True,
        dedup_markers: bool = True,
    ) -> None:
        self._normalize_viewbox = normalize_viewbox
        self._fix_text_alignment = fix_text_alignment
        self._fix_arrow_heads = fix_arrow_heads
        self._clean_spacing = clean_spacing
        self._sharp_paths = sharp_paths
        self._normalize_fonts = normalize_fonts
        self._normalize_strokes = normalize_strokes
        self._dedup_markers = dedup_markers

    def process(self, svg: str) -> str:
        svg = _strip_xml_declaration(svg)
        root = _parse(svg)

        if self._normalize_viewbox:
            self._apply_viewbox(root)
        if self._fix_text_alignment:
            self._apply_text_alignment(root)
        if self._fix_arrow_heads:
            self._apply_arrow_normalization(root)
        if self._clean_spacing:
            self._apply_spacing_cleanup(root)
        if self._sharp_paths:
            self._apply_path_sharpening(root)
        if self._normalize_fonts:
            self._apply_font_normalization(root)
        if self._normalize_strokes:
            self._apply_stroke_normalization(root)
        if self._dedup_markers:
            self._apply_marker_dedup(root)

        return _serialize(root)

    @staticmethod
    def _apply_viewbox(root: Element) -> None:
        vb = root.get("viewBox")
        if vb:
            parts = re.split(r"[\s,]+", vb.strip())
            if len(parts) == 4:
                try:
                    x, y, w, h = map(float, parts)
                    root.set("viewBox", f"{x:.0f} {y:.0f} {w:.0f} {h:.0f}")
                except ValueError:
                    pass
        elif root.get("width") and root.get("height"):
            try:
                w = _parse_length(root.get("width", ""))
                h = _parse_length(root.get("height", ""))
                root.set("viewBox", f"0 0 {w:.0f} {h:.0f}")
            except (ValueError, TypeError):
                pass

    _TEXT_TAGS = frozenset({"text", "tspan", "textPath"})

    @classmethod
    def _apply_text_alignment(cls, root: Element) -> None:
        for elem in root.iter():
            tag = _local_name(elem.tag)
            if tag in cls._TEXT_TAGS:
                if "dominant-baseline" not in (elem.get("dominant-baseline") or ""):
                    if "text-anchor" not in (elem.get("text-anchor") or ""):
                        elem.set("dominant-baseline", "central")
                        elem.set("text-anchor", "middle")

    @staticmethod
    def _apply_arrow_normalization(root: Element) -> None:
        for marker in root.iter(f"{{{_SVG_NS}}}marker"):
            orient = marker.get("orient", "auto")
            if orient not in ("auto", "auto-start-reverse"):
                marker.set("orient", "auto")

    @staticmethod
    def _apply_spacing_cleanup(root: Element) -> None:
        parent_map = {c: p for p in root.iter() for c in p}

        changed = True
        while changed:
            changed = False
            for elem in list(root.iter()):
                if elem is root:
                    continue
                tag = _local_name(elem.tag)
                if tag == "g" and len(elem.attrib) == 0 and len(elem) == 0:
                    parent = parent_map.get(elem)
                    if parent is not None:
                        parent.remove(elem)
                        changed = True

    _PATH_RE = re.compile(r"(-?\d+\.?\d*)")

    @classmethod
    def _apply_path_sharpening(cls, root: Element) -> None:
        for elem in root.iter():
            tag = _local_name(elem.tag)
            d = elem.get("d", "")
            if tag in ("path",) and d:
                elem.set("d", cls._sharpen_path(d))
            points = elem.get("points", "")
            if tag in ("polygon", "polyline") and points:
                elem.set("points", cls._sharpen_path(points))

    @classmethod
    def _sharpen_path(cls, d: str) -> str:
        def _round(m: re.Match[str]) -> str:
            try:
                n = float(m.group(1))
                if abs(n - round(n)) < 0.0001:
                    return f"{round(n):g}"
                return f"{n:.1f}"
            except ValueError:
                return m.group(1)

        return cls._PATH_RE.sub(_round, d)

    @staticmethod
    def _apply_font_normalization(root: Element) -> None:
        for elem in root.iter():
            tag = _local_name(elem.tag)
            if tag in ("text", "tspan", "textPath"):
                ff = elem.get("font-family", "")
                if ff and ff in _WEB_SAFE_FONTS:
                    elem.set("font-family", _WEB_SAFE_FONTS[ff])

    @staticmethod
    def _apply_stroke_normalization(root: Element) -> None:
        for elem in root.iter():
            sw = elem.get("stroke-width", "")
            if sw:
                try:
                    val = float(sw)
                    if val <= 0:
                        elem.set("stroke-width", "1")
                except ValueError:
                    pass
            elem.attrib.pop("stroke-dashoffset", None)

    @staticmethod
    def _apply_marker_dedup(root: Element) -> None:
        markers: dict[str, str] = {}
        to_remove: list[Element] = []

        for marker in root.iter(f"{{{_SVG_NS}}}marker"):
            mid = marker.get("id", "")
            if not mid:
                continue
            marker_xml = tostring(marker, encoding="unicode")
            if marker_xml in markers:
                existing_id = markers[marker_xml]
                to_remove.append(marker)
                marker.set("id", existing_id)
            else:
                markers[marker_xml] = mid

        parent_map = {c: p for p in root.iter() for c in p}
        for marker in to_remove:
            parent = parent_map.get(marker)
            if parent is not None:
                parent.remove(marker)
            dup_id = marker.get("id", "")
            if dup_id:
                for elem in root.iter():
                    for attr in ("marker-start", "marker-mid", "marker-end"):
                        val = elem.get(attr, "")
                        if val and dup_id in val:
                            elem.set(attr, val)


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse(svg: str) -> Element:
    register_namespace("", _SVG_NS)
    root = fromstring(svg)
    return root


def _serialize(root: Element) -> str:
    raw = tostring(root, encoding="unicode")
    return raw


def _strip_xml_declaration(svg: str) -> str:
    return _XML_DECL_RE.sub("", svg)


def _parse_length(value: str) -> float:
    value = value.strip()
    match = re.match(r"([+-]?\d+\.?\d*)(px|pt|em|ex|cm|mm|in|%)?", value)
    if match:
        return float(match.group(1))
    raise ValueError(f"Cannot parse length: {value!r}")


def default_quality() -> QualityProcessor:
    return QualityProcessor(
        normalize_viewbox=True,
        fix_text_alignment=True,
        fix_arrow_heads=True,
        clean_spacing=True,
        sharp_paths=True,
        normalize_fonts=True,
        normalize_strokes=True,
        dedup_markers=True,
    )


def minimal_quality() -> QualityProcessor:
    return QualityProcessor(
        normalize_viewbox=True,
        fix_text_alignment=False,
        fix_arrow_heads=False,
        clean_spacing=False,
        sharp_paths=False,
        normalize_fonts=False,
        normalize_strokes=False,
        dedup_markers=False,
    )
