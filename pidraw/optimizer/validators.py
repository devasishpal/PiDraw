"""SVG validation for the optimization engine."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET


class SVGValidationError(ValueError):
    """Raised when SVG content fails validation."""


def validate_svg(svg: str) -> bool:
    """Ensure *svg* is well-formed XML with a root ``<svg>`` element.

    Returns ``True`` on success and raises :class:`SVGValidationError`
    on failure.
    """
    if not svg or not svg.strip():
        raise SVGValidationError("SVG content is empty")

    if not re.search(r'<svg[\s>]', svg, re.IGNORECASE):
        raise SVGValidationError("No <svg> root element found")

    try:
        ET.fromstring(svg)
    except ET.ParseError as exc:
        raise SVGValidationError(f"XML parsing failed: {exc}") from exc

    return True
