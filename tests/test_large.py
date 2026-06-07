"""Tests for the large file support module."""

from __future__ import annotations

import os
import tempfile

from pidraw.large import estimate_language_from_stream, stream_svg_write


class TestLargeFileSupport:
    def test_estimate_language_from_stream_mermaid(self) -> None:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8")
        tmp.write("graph TD\n    A-->B\n")
        tmp.close()
        try:
            lang = estimate_language_from_stream(tmp.name)
            assert lang == "mermaid" or lang == "unknown"
        finally:
            os.unlink(tmp.name)

    def test_estimate_language_from_stream_unknown(self) -> None:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write("hello world\n")
        tmp.close()
        try:
            lang = estimate_language_from_stream(tmp.name)
            assert lang == "unknown"
        finally:
            os.unlink(tmp.name)

    def test_stream_svg_write(self) -> None:
        svg = "<svg xmlns='http://www.w3.org/2000/svg'><circle r='5'/></svg>"
        tmp = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
        tmp.close()
        try:
            stream_svg_write(svg, tmp.name)
            with open(tmp.name, "rb") as f:
                content = f.read()
            assert content == svg.encode("utf-8")
        finally:
            os.unlink(tmp.name)
