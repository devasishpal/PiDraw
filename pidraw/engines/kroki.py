"""Renderer for Kroki-compatible diagram formats."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import EngineNotAvailableError, RenderError

_MAX_SIZE = 100 * 1024
_DEFAULT_ENDPOINT = "https://kroki.io"


class KrokiRenderer(BaseRenderer):
    """Render diagrams via a Kroki-compatible API endpoint."""

    name = "kroki"

    def __init__(
        self,
        endpoint: str | None = None,
        diagram_type: str = "vega",
        output_format: str = "svg",
    ) -> None:
        self._endpoint = (
            endpoint or os.environ.get("PIDRAW_KROKI_URL") or _DEFAULT_ENDPOINT
        ).rstrip("/")
        self._diagram_type = diagram_type
        self._output_format = output_format
        self._timeout = 15

    def render(self, source: str) -> str:
        if not source or not source.strip():
            raise RenderError("kroki", "Kroki source is empty")
        if "\x00" in source:
            raise RenderError("kroki", "Kroki source contains null bytes")
        if len(source.encode("utf-8")) > _MAX_SIZE:
            raise RenderError(
                "kroki", f"Kroki source exceeds {_MAX_SIZE // 1024} KB limit"
            )

        url = f"{self._endpoint}/{self._diagram_type}/{self._output_format}"
        payload = json.dumps({"diagram_source": source}).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "pidraw/0.2.0",
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=self._timeout)
            raw = resp.read()
            svg: str = raw.decode("utf-8")

            if not svg.strip():
                raise RenderError("kroki", "Kroki returned empty response")
            if "<svg" not in svg:
                raise RenderError("kroki", "Kroki response does not contain <svg>")

            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(svg)
            except ET.ParseError as exc:
                raise RenderError("kroki", f"Kroki returned malformed XML: {exc}")

            return svg

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RenderError(
                "kroki", f"Kroki HTTP {exc.code}: {body}"
            )
        except urllib.error.URLError:
            raise EngineNotAvailableError(
                "kroki",
                setup_command="Check network access to kroki.io",
            )
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError("kroki", f"Kroki error: {exc}")
