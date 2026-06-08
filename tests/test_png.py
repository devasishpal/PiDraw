"""Tests for PNG output pipeline."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pidraw.backend.png import (
    strip_svg_background,
    trim_png,
    svg_to_png,
    _render_cairosvg,
    _render_playwright,
)
from pidraw.exceptions import PngConversionError


class TestStripBackground:
    def test_strips_full_viewport_rect(self) -> None:
        svg = '<svg><rect width="100%" height="100%" fill="white"/><g></g></svg>'
        result = strip_svg_background(svg)
        assert "<rect" not in result

    def test_leaves_content_untouched(self) -> None:
        svg = "<svg><g><text>hi</text></g></svg>"
        result = strip_svg_background(svg)
        assert result == svg

    def test_partial_rect_kept(self) -> None:
        svg = '<svg><rect width="50%" height="50%" fill="red"/></svg>'
        result = strip_svg_background(svg)
        assert "<rect" in result


class TestTrimPng:
    def test_returns_same_when_no_pil(self) -> None:
        with patch.dict("sys.modules", {"PIL": None}):
            result = trim_png(b"test")
            assert result == b"test"

    def test_returns_same_on_failure(self) -> None:
        with patch("pidraw.backend.png.BytesIO", side_effect=Exception):
            result = trim_png(b"test")
            assert result == b"test"


class TestSvgToPng:
    def test_raises_png_conversion_error(self) -> None:
        with patch("pidraw.backend.png._detect_backend", side_effect=ImportError("no backend")):
            with pytest.raises(ImportError):
                svg_to_png("<svg></svg>")

    def test_backend_error_wrapped(self) -> None:
        def failing_backend(svg: str, **kwargs: object) -> bytes:
            raise RuntimeError("backend crash")

        with patch("pidraw.backend.png._detect_backend", return_value=failing_backend):
            with pytest.raises(PngConversionError, match="backend crash"):
                svg_to_png("<svg></svg>")

    def test_backend_called_with_transparent(self) -> None:
        def fake_backend(svg: str, **kwargs: object) -> bytes:
            assert kwargs.get("transparent") is True
            assert kwargs.get("background_color") is None
            return b"PNG"

        with patch("pidraw.backend.png._detect_backend", return_value=fake_backend):
            with patch("pidraw.backend.png.trim_png", return_value=b"PNG"):
                result = svg_to_png("<svg></svg>")
                assert result == b"PNG"


class TestCairosvgBackend:
    def test_calls_cairosvg(self) -> None:
        mock_cairosvg = MagicMock()
        mock_cairosvg.svg2png.return_value = b"PNG"
        with patch.dict("sys.modules", {"cairosvg": mock_cairosvg}):
            result = _render_cairosvg("<svg></svg>")
            assert result == b"PNG"

    def test_scale_passed(self) -> None:
        mock_cairosvg = MagicMock()
        mock_cairosvg.svg2png.return_value = b"PNG"
        with patch.dict("sys.modules", {"cairosvg": mock_cairosvg}):
            _render_cairosvg("<svg></svg>", scale=2.0)
            kwargs = mock_cairosvg.svg2png.call_args[1]
            assert kwargs["scale"] == 2.0


class TestPlaywrightBackend:
    def test_calls_playwright(self) -> None:
        mock_page = MagicMock()
        mock_page.screenshot.return_value = b"PNG"
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright = MagicMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        with patch("playwright.sync_api.sync_playwright") as mock_sync:
            mock_sync.return_value.__enter__.return_value = mock_playwright
            result = _render_playwright("<svg></svg>")
            assert result == b"PNG"
            mock_page.screenshot.assert_called_once()
