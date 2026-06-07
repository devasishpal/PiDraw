"""Individual SVG optimization passes.

Each pass is a pure function ``(svg: str) -> str`` that performs one
specific optimisation.  Passes are designed to be safe — they never remove
visible content, corrupt text, or alter rendering.
"""

from __future__ import annotations

import re
from collections import defaultdict
from copy import deepcopy
from typing import Iterable
from xml.etree.ElementTree import Element, fromstring, register_namespace, tostring

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SVG_NS = "http://www.w3.org/2000/svg"
_XML_DECL_RE = re.compile(r"^<\?xml[^>]*\?>")

register_namespace("", _SVG_NS)


def _local_name(tag: str) -> str:
    """Return the local (unprefixed) part of a namespaced tag name."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _ns_tag(ns: str, local: str) -> str:
    """Build a namespaced tag ``{ns}local``, or bare *local* if *ns* is empty."""
    return f"{{{ns}}}{local}" if ns else local


def _svg_ns_from_text(svg: str) -> str:
    """Detect the SVG namespace URI used in *svg* (or ``''`` if absent)."""
    m = re.search(r'\bxmlns(?::\w+)?="([^"]+)"', svg)
    return m.group(1) if m else ""


def _strip_xml_declaration(svg: str) -> str:
    """Remove any ``<?xml …?>`` processing instruction."""
    return _XML_DECL_RE.sub("", svg).strip()


def _parse(svg: str) -> Element:
    """Parse *svg* into an ElementTree, stripping the XML declaration first."""
    return fromstring(_strip_xml_declaration(svg))


def _serialize(root: Element) -> str:
    """Return pretty-ish XML string for *root*."""
    return tostring(root, encoding="unicode", xml_declaration=False)


def _children(elem: Element) -> list[Element]:
    """Return list of child elements."""
    return list(elem)


def _iter_all(elem: Element) -> Iterable[Element]:
    """Iterate over *elem* and all its descendants."""
    return elem.iter()


# ---------------------------------------------------------------------------
# Pass 1 – Remove XML comments
# ---------------------------------------------------------------------------

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def remove_comments(svg: str) -> str:
    """Strip all XML comments from the SVG."""
    return _COMMENT_RE.sub("", svg)


# ---------------------------------------------------------------------------
# Pass 2 – Remove editor metadata
# ---------------------------------------------------------------------------

_EDITOR_ATTR_RE = re.compile(r'\s+(inkscape|sodipodi):\w+="[^"]*"', re.IGNORECASE)
_EDITOR_NS_RE = re.compile(r'\s+xmlns:(inkscape|sodipodi)="[^"]*"', re.IGNORECASE)
_NAMEDVIEW_RE = re.compile(r"<sodipodi:namedview[^>]*/>", re.IGNORECASE)
_METADATA_BLOCK_RE = re.compile(r"<metadata>.*?</metadata>", re.DOTALL | re.IGNORECASE)


def remove_editor_metadata(svg: str) -> str:
    """Remove Inkscape / Sodipodi attributes, namespace declarations, and ``<metadata>`` blocks."""
    svg = _EDITOR_ATTR_RE.sub("", svg)
    svg = _EDITOR_NS_RE.sub("", svg)
    svg = _NAMEDVIEW_RE.sub("", svg)
    svg = _METADATA_BLOCK_RE.sub("", svg)
    return svg


# ---------------------------------------------------------------------------
# Pass 3 – Remove unused definitions
# ---------------------------------------------------------------------------

_URL_REF_RE = re.compile(r"url\(#([^)]+)\)")
_HREF_REF_RE = re.compile(r'(?:href|xlink:href)\s*=\s*"#([^"]+)"')
_CSS_ID_REF_RE = re.compile(r"#([a-zA-Z_][\w.-]*)")


def _collect_referenced_ids(root: Element) -> set[str]:
    """Return all IDs referenced via ``url(#…)``, ``href``, or CSS selectors."""
    refs: set[str] = set()

    for elem in _iter_all(root):
        for value in elem.attrib.values():
            for m in _URL_REF_RE.finditer(value):
                refs.add(m.group(1))
            for m in _HREF_REF_RE.finditer(value):
                refs.add(m.group(1))

        if _local_name(elem.tag) == "style" and elem.text:
            text = elem.text
            for m in _URL_REF_RE.finditer(text):
                refs.add(m.group(1))
            for m in _CSS_ID_REF_RE.finditer(text):
                refs.add(m.group(1))

    return refs


def remove_unused_defs(svg: str) -> str:
    """Remove ``<defs>`` children whose ``id`` is not referenced elsewhere.

    References are detected inside attributes (``url(#…)``,
    ``href="#…"``) and ``<style>`` text content.
    """
    root = _parse(svg)
    ns = _svg_ns_from_text(svg)
    defs_tag = _ns_tag(ns, "defs")

    defs_elem = None
    for child in root:
        if child.tag == defs_tag:
            defs_elem = child
            break

    if defs_elem is None:
        return svg

    referenced = _collect_referenced_ids(root)

    for child in list(defs_elem):
        if _local_name(child.tag) != "style":
            eid = child.get("id")
            if eid is not None and eid not in referenced:
                defs_elem.remove(child)

    return _serialize(root)


# ---------------------------------------------------------------------------
# Pass 4 – Merge duplicate definitions
# ---------------------------------------------------------------------------


def _def_content_key(elem: Element) -> str:
    """Return a serialised representation of *elem* with the ``id`` omitted."""
    copy = deepcopy(elem)
    copy.attrib.pop("id", None)
    copy.attrib.pop(f"{{{_SVG_NS}}}id", None)
    for e in copy.iter():
        e.tail = None
    return tostring(copy, encoding="unicode")


def merge_duplicate_defs(svg: str) -> str:
    """Merge ``<defs>`` children that have identical content (ignoring ``id``).

    All references to the removed ID are rewritten to point to the kept ID.
    """
    root = _parse(svg)
    ns = _svg_ns_from_text(svg)
    defs_tag = _ns_tag(ns, "defs")

    defs_elem = None
    for child in root:
        if child.tag == defs_tag:
            defs_elem = child
            break

    if defs_elem is None:
        return svg

    content_to_ids: dict[str, list[str]] = defaultdict(list)
    for child in list(defs_elem):
        eid = child.get("id")
        if eid is not None:
            content_to_ids[_def_content_key(child)].append(eid)

    rename: dict[str, str] = {}
    remove_ids: set[str] = set()
    for content, ids in content_to_ids.items():
        if len(ids) > 1:
            kept = ids[0]
            for old in ids[1:]:
                rename[old] = kept
                remove_ids.add(old)

    if not rename:
        return svg

    for child in list(defs_elem):
        eid = child.get("id")
        if eid in remove_ids:
            defs_elem.remove(child)

    for elem in _iter_all(root):
        for key, value in elem.attrib.items():
            for old_id, new_id in rename.items():
                if f"#{old_id}" in value:
                    elem.set(key, value.replace(f"#{old_id}", f"#{new_id}"))

    return _serialize(root)


# ---------------------------------------------------------------------------
# Pass 5 – Collapse redundant groups
# ---------------------------------------------------------------------------


def _should_collapse(elem: Element) -> bool:
    """Return ``True`` if *elem* is a ``<g>`` that can be safely removed."""
    if _local_name(elem.tag) != "g":
        return False
    if any(_local_name(k) == "id" for k in elem.attrib):
        return False
    sig = {k for k in elem.attrib if _local_name(k) != "id"}
    if sig:
        return False
    kids = _children(elem)
    if len(kids) == 1:
        return True
    if not kids and not (elem.text or "").strip():
        return True
    return False


def _collapse_recursive(parent: Element) -> bool:
    """Walk *parent*'s children and collapse redundant ``<g>``.  Returns ``True`` if changed."""
    changed = False
    for child in list(parent):
        changed = _collapse_recursive(child) or changed
        if _should_collapse(child):
            idx = list(parent).index(child)
            grandchildren = _children(child)
            parent.remove(child)
            for gc in reversed(grandchildren):
                parent.insert(idx, gc)
            changed = True
    return changed


def collapse_redundant_groups(svg: str) -> str:
    """Remove ``<g>`` elements that have no attributes and are unnecessary."""
    root = _parse(svg)
    _collapse_recursive(root)
    return _serialize(root)


# ---------------------------------------------------------------------------
# Pass 6 – Remove empty elements
# ---------------------------------------------------------------------------

_SIGNIFICANT_ATTRS = frozenset(
    {
        "width", "height", "x", "y", "d", "points", "r", "cx", "cy",
        "rx", "ry", "viewBox", "dx", "dy", "x1", "y1", "x2", "y2",
    }
)


def _is_visually_empty(elem: Element) -> bool:
    """Return ``True`` if *elem* has no visual impact on the rendering."""
    if _local_name(elem.tag) in ("svg", "defs", "style"):
        return False
    if _children(elem):
        return False
    if (elem.text or "").strip():
        return False
    for key in elem.attrib:
        local = _local_name(key)
        if local in _SIGNIFICANT_ATTRS:
            val = elem.attrib[key].strip()
            if val not in ("0", "none", ""):
                return False
        if local == "id":
            return False
    return True


def _remove_empty_recursive(parent: Element) -> bool:
    """Walk *parent* and remove visually empty children.  Returns ``True`` if changed."""
    changed = False
    for child in list(parent):
        changed = _remove_empty_recursive(child) or changed
        if _is_visually_empty(child):
            parent.remove(child)
            changed = True
    return changed


def remove_empty_elements(svg: str) -> str:
    """Strip elements that have no children, text, or meaningful geometry."""
    root = _parse(svg)
    _remove_empty_recursive(root)
    return _serialize(root)


# ---------------------------------------------------------------------------
# Pass 7 – Normalize transforms
# ---------------------------------------------------------------------------

_TRANSFORM_RE = re.compile(
    r"(translate|rotate|scale|skewX|skewY|matrix)\s*\(([^)]*)\)",
    re.IGNORECASE,
)


def _format_number(n: float) -> str:
    """Format a number without trailing zeros or scientific notation."""
    s = f"{n:.10f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def _normalize_transform_string(transform: str) -> str:
    """Reformat a ``transform`` attribute value in a canonical form."""
    parts: list[str] = []
    for m in _TRANSFORM_RE.finditer(transform):
        name = m.group(1).lower()
        raw_args = m.group(2)
        args = re.split(r"[\s,]+", raw_args.strip())
        nums: list[float] = []
        for a in args:
            a = a.strip()
            if a:
                try:
                    nums.append(float(a))
                except ValueError:
                    pass
        formatted = ", ".join(_format_number(n) for n in nums)
        parts.append(f"{name}({formatted})")
    return " ".join(parts)


def normalize_transforms(svg: str) -> str:
    """Canonicalise all ``transform`` attribute values.

    Converts consistent spacing, lower-case function names, and removes
    trailing zeros from numbers.  *Does not* combine separate transform
    functions or convert to matrix form — this pass is guaranteed safe.
    """
    root = _parse(svg)
    for elem in _iter_all(root):
        t = elem.get("transform")
        if t is not None:
            elem.set("transform", _normalize_transform_string(t))
    return _serialize(root)


# ---------------------------------------------------------------------------
# Pass 8 – Simplify path data
# ---------------------------------------------------------------------------

_PATH_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def _simplify_path_number(m: re.Match[str]) -> str:
    """Format a matched path number without trailing zeros."""
    try:
        return _format_number(float(m.group(0)))
    except ValueError:
        return m.group(0)


def _simplify_path_data(d: str) -> str:
    """Normalise numbers in SVG path ``d`` data.

    Removes trailing zeros, unnecessary decimal points, and normalises
    whitespace around commands.
    """
    if not d or not d.strip():
        return d

    simplified = _PATH_NUM_RE.sub(_simplify_path_number, d)

    result: list[str] = []
    prev_was_cmd = False
    for ch in simplified:
        if ch in "MLHVCSQTAZmlhvcsqtaz":
            if result and result[-1] not in (" ", "\t", "\n", "\r"):
                result.append(" ")
            result.append(ch)
            prev_was_cmd = True
        elif ch in " \t\n\r,":
            if not prev_was_cmd:
                result.append(" ")
            prev_was_cmd = True
        elif ch in "+-":
            if result and result[-1] == "e":
                result.append(ch)
            else:
                if result and result[-1] not in (" ", "\t", "\n", "\r", "(", "-"):
                    result.append(" ")
                result.append(ch)
            prev_was_cmd = False
        elif ch == ".":
            result.append(ch)
            prev_was_cmd = False
        else:
            result.append(ch)
            prev_was_cmd = False

    return "".join(result)


def simplify_paths(svg: str) -> str:
    """Normalise all path ``d`` attribute values.

    Removes trailing zeros, normalises number formatting.  The path
    structure (commands and sequencing) is preserved.
    """
    root = _parse(svg)
    for elem in _iter_all(root):
        d = elem.get("d")
        if d is not None:
            elem.set("d", _simplify_path_data(d))
    return _serialize(root)


# ---------------------------------------------------------------------------
# Pass 9 – Trim whitespace
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")


def trim_whitespace(svg: str) -> str:
    """Collapse runs of whitespace and strip leading/trailing space.

    Preserves whitespace inside ``<text>``, ``<tspan>``, ``<style>``,
    ``<script>`` elements.
    """
    preserve_tags = frozenset({"text", "tspan", "style", "script", "pre"})

    def _should_preserve(elem: Element) -> bool:
        return _local_name(elem.tag) in preserve_tags

    def _is_preserved_ancestor(elem: Element, root: Element) -> bool:
        cur: Element | None = elem
        while cur is not None:
            if cur is not root and _should_preserve(cur):
                return True
            cur = _find_parent(root, cur)
        return False

    def _find_parent(root: Element, child: Element) -> Element | None:
        for parent in root.iter():
            if child in _children(parent):
                return parent
        return None

    root = _parse(svg)

    for elem in _iter_all(root):
        if _is_preserved_ancestor(elem, root):
            continue
        if elem.text:
            elem.text = _WHITESPACE_RE.sub(" ", elem.text).strip()
        if elem.tail:
            elem.tail = _WHITESPACE_RE.sub(" ", elem.tail).strip()
            if elem.tail == " ":
                elem.tail = ""

    raw = _serialize(root)  # do first serialization without xml decl

    raw = raw.replace("> <", "><")
    raw = _WHITESPACE_RE.sub(" ", raw)

    raw = raw.replace(" />", "/>")

    return raw.strip()


# ---------------------------------------------------------------------------
# Pass 10 – Normalize attribute ordering
# ---------------------------------------------------------------------------

_XMLNS_ATTR_RE = re.compile(r"^xmlns(?::\w+)?$")


def _sort_attributes(elem: Element) -> None:
    """Reorder *elem*'s attributes into a canonical order in-place."""
    if not elem.attrib:
        return

    def sort_key(item: tuple[str, str]) -> tuple[int, str]:
        k = item[0]
        if k == "id":
            return (0, k)
        if _XMLNS_ATTR_RE.match(k):
            return (1, k)
        return (2, k)

    sorted_attribs = dict(sorted(elem.attrib.items(), key=sort_key))
    elem.attrib.clear()
    elem.attrib.update(sorted_attribs)


def normalize_attribute_ordering(svg: str) -> str:
    """Canonicalise attribute order.

    Order: ``id``, namespace declarations, then all other attributes
    alphabetically.  Has no effect on rendering.
    """
    root = _parse(svg)
    for elem in _iter_all(root):
        _sort_attributes(elem)
    return _serialize(root)
