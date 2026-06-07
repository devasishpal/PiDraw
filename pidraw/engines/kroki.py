"""Renderer for Kroki-compatible diagram formats.

Kroki is an HTTP API that renders many diagram types.  This renderer
posts source to a configurable Kroki endpoint.
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError

_MAX_SIZE = 100 * 1024
_DEFAULT_ENDPOINT = "https://kroki.io"


class KrokiRenderer(BaseRenderer):
    """Render diagrams via a Kroki-compatible API endpoint.

    Parameters
    ----------
    endpoint : str | None
        Base URL of the Kroki instance (e.g. ``http://localhost:8000``).

    """

    name = "kroki"

    def __init__(
        self,
        endpoint: str | None = None,
        diagram_type: str = "vega",
        output_format: str = "svg",
    ) -> None:
        """Initialise with optional Kroki endpoint URL."""
        self._endpoint = (endpoint or _DEFAULT_ENDPOINT).rstrip("/")
        self._diagram_type = diagram_type
        self._output_format = output_format

    def render(self, source: str) -> str:
        """Render diagram source via the Kroki API."""
        if not source or not source.strip():
            raise RenderingError("Kroki source is empty")
        if "\x00" in source:
            raise RenderingError("Kroki source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderingError(f"Kroki source exceeds {_MAX_SIZE // 1024} KB limit")

        url = f"{self._endpoint}/{self._diagram_type}/{self._output_format}"
        payload = json.dumps({"diagram_source": source}).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "pidraw/0.1.0",
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=30)
            raw = resp.read()
            svg: str = raw.decode("utf-8")

            if not svg.strip():
                raise RenderingError("Kroki returned empty response")
            if "<svg" not in svg:
                raise RenderingError("Kroki response does not contain <svg>")

            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderingError(f"Kroki returned malformed XML: {exc}") from exc

            return svg

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RenderingError(
                f"Kroki HTTP {exc.code}: {body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RenderingError(
                f"Kroki connection failed: {exc.reason}"
            ) from exc
        except subprocess.TimeoutExpired:
            raise RenderingError("Kroki request timed out after 30s")
        except RenderingError:
            raise
        except Exception as exc:
            raise RenderingError(f"Kroki error: {exc}") from exc
