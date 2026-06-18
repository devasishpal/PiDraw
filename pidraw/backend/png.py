from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from importlib import util as importlib_util
from io import BytesIO
from typing import Callable, Optional

from pidraw.exceptions import PngConversionError


# Pattern to match SVG background rectangles (solid fills that cover the full viewport)
_BG_RECT_RE = re.compile(
    r"<rect\s[^>]*?(?:width\s*=\s*['\"]100%(?:[^>]*?height\s*=\s*['\"]100%['\"])"
    r"|height\s*=\s*['\"]100%(?:[^>]*?width\s*=\s*['\"]100%['\"]))[^>]*?\/?\s*>",
    re.IGNORECASE,
)


def strip_svg_background(svg: str) -> str:
    return _BG_RECT_RE.sub("", svg)


def trim_png(png_bytes: bytes, padding: int = 0) -> bytes:
    try:
        from PIL import Image

        Image.MAX_IMAGE_PIXELS = None
        img = Image.open(BytesIO(png_bytes))
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        bbox = img.getbbox()
        if bbox is None:
            return png_bytes
        if padding <= 0:
            padding = max(50, int(min(img.width, img.height) * 0.08))
        left = max(0, bbox[0] - padding)
        upper = max(0, bbox[1] - padding)
        right = min(img.width, bbox[2] + padding)
        lower = min(img.height, bbox[3] + padding)
        cropped = img.crop((left, upper, right, lower))
        buf = BytesIO()
        cropped.save(buf, format="PNG")
        buf.seek(0)
        return buf.read()
    except Exception:
        return png_bytes


def svg_to_png(
    svg: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
    transparent: bool = True,
    trim: bool = True,
) -> bytes:
    if transparent:
        svg = strip_svg_background(svg)
    backend = _detect_backend()
    try:
        result = backend(
            svg,
            scale=scale,
            background_color=background_color if not transparent else None,
            output_width=output_width,
            output_height=output_height,
            transparent=transparent,
        )
    except Exception as exc:
        raise PngConversionError(f"{backend.__name__} failed: {exc}") from exc
    if transparent and trim:
        result = trim_png(result)
    return result


BackendFn = Callable[..., bytes]


def _detect_backend() -> BackendFn:
    errors: list[str] = []

    if shutil.which("resvg") is not None:
        return _render_resvg
    else:
        errors.append("resvg CLI not found on PATH")

    if importlib_util.find_spec("cairosvg") is not None:
        try:
            import sys as _sys
            _sys.modules.pop("cairosvg", None)
            import cairosvg  # type: ignore[import-not-found, import-untyped]
            _ = cairosvg.svg2png
            return _render_cairosvg
        except Exception as e:
            errors.append(f"cairosvg (not usable: {e})")
    else:
        errors.append("cairosvg not installed")

    if importlib_util.find_spec("playwright") is not None:
        return _render_playwright
    else:
        errors.append("playwright not installed")

    try:
        from PIL import Image  # noqa: F401
        return _render_pillow
    except ImportError:
        errors.append("Pillow not installed for fallback renderer")

    try:
        import svglib  # noqa: F401
        return _render_svglib
    except ImportError:
        errors.append("svglib not installed")

    raise ImportError(
        "No SVG-to-PNG backend available.\n\n"
        "Options:\n"
        "  Install resvg CLI:  https://github.com/RazrFalcon/resvg/releases\n"
        "  pip install pidraw[png-playwright] && playwright install chromium\n"
        "  pip install pidraw[png]        (cairosvg - needs Cairo DLLs)\n\n"
        "Detected issues:\n" + "\n".join(f"  - {e}" for e in errors)
    )


def _render_resvg(
    svg: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
    transparent: bool = True,
) -> bytes:
    tmp_dir: Optional[str] = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix="pidraw_resvg_")
        input_path = os.path.join(tmp_dir, "input.svg")
        output_path = os.path.join(tmp_dir, "output.png")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(svg)
        cmd = ["resvg", input_path, output_path]
        if output_width is not None and output_height is not None:
            cmd.extend(["--width", str(output_width), "--height", str(output_height)])
        if scale != 1.0:
            cmd.extend(["--dpi", str(int(96 * scale))])
        subprocess.run(cmd, capture_output=True, timeout=60, check=True)
        with open(output_path, "rb") as f:
            return f.read()
    except subprocess.TimeoutExpired:
        raise PngConversionError("resvg timed out after 60s")
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise PngConversionError(f"resvg failed: {stderr}")
    except FileNotFoundError:
        raise PngConversionError("resvg executable not found")
    finally:
        if tmp_dir is not None and os.path.isdir(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except OSError:
                pass


def _render_cairosvg(
    svg: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
    transparent: bool = True,
) -> bytes:
    import cairosvg  # type: ignore[import-untyped]

    kwargs: dict = {"scale": scale}
    bg = None if transparent else background_color
    if bg is not None:
        kwargs["background_color"] = bg
    elif transparent:
        kwargs["background_color"] = "transparent"
    if output_width is not None:
        kwargs["output_width"] = output_width
    if output_height is not None:
        kwargs["output_height"] = output_height

    return cairosvg.svg2png(bytestring=svg.encode("utf-8"), **kwargs)


def _render_pillow(
    svg: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
    transparent: bool = True,
) -> bytes:
    """Basic SVG-to-PNG via Pillow with simple SVG element parsing.

    Handles: <svg>, <rect>, <circle>, <ellipse>, <line>, <polyline>,
    <polygon>, <path>, <text> elements with basic styling.
    """
    try:
        return _render_svglib(
            svg, scale, background_color, output_width, output_height, transparent,
        )
    except Exception:
        pass

    from PIL import Image, ImageDraw, ImageFont
    import xml.etree.ElementTree as ET

    root = ET.fromstring(svg)

    svg_w = int(float(root.get("width", "800")))
    svg_h = int(float(root.get("height", "600")))
    viewbox = root.get("viewBox")
    if viewbox:
        parts = viewbox.strip().split()
        if len(parts) == 4:
            svg_w = int(float(parts[2]))
            svg_h = int(float(parts[3]))

    if output_width and output_height:
        final_w, final_h = output_width, output_height
    else:
        final_w, final_h = int(svg_w * scale), int(svg_h * scale)

    img = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", int(14 * scale))
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

    def _parse_color(val: str | None) -> tuple[int, int, int, int]:
        if not val or val in ("none", "transparent"):
            return (0, 0, 0, 0)
        val = val.strip()
        if val.startswith("#"):
            val = val.lstrip("#")
            if len(val) == 3:
                val = "".join(c * 2 for c in val)
            r, g, b = int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16)
            return (r, g, b, 255)
        named = {
            "black": (0, 0, 0, 255),
            "white": (255, 255, 255, 255),
            "red": (255, 0, 0, 255),
            "green": (0, 128, 0, 255),
            "blue": (0, 0, 255, 255),
            "gray": (128, 128, 128, 255),
            "grey": (128, 128, 128, 255),
            "yellow": (255, 255, 0, 255),
        }
        return named.get(val.lower(), (0, 0, 0, 255))

    def _scale_x(x: float) -> float:
        return x / svg_w * final_w

    def _scale_y(y: float) -> float:
        return y / svg_h * final_h

    def _render_element(el: ET.Element) -> None:
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag

        fill = _parse_color(el.get("fill"))
        stroke = _parse_color(el.get("stroke"))
        sw = float(el.get("stroke-width", "1"))

        if tag == "rect":
            x = float(el.get("x", "0"))
            y = float(el.get("y", "0"))
            w = float(el.get("width", "0"))
            h = float(el.get("height", "0"))
            rx = float(el.get("rx", "0"))
            if fill[3] > 0:
                draw.rounded_rectangle(
                    [_scale_x(x), _scale_y(y), _scale_x(x + w), _scale_y(y + h)],
                    radius=rx,
                    fill=fill if fill[3] > 0 else None,
                    outline=stroke if stroke[3] > 0 else None,
                    width=max(1, int(sw * scale)),
                )

        elif tag == "circle":
            cx = float(el.get("cx", "0"))
            cy = float(el.get("cy", "0"))
            r = float(el.get("r", "0"))
            draw.ellipse(
                [_scale_x(cx - r), _scale_y(cy - r), _scale_x(cx + r), _scale_y(cy + r)],
                fill=fill if fill[3] > 0 else None,
                outline=stroke if stroke[3] > 0 else None,
                width=max(1, int(sw * scale)),
            )

        elif tag == "ellipse":
            cx = float(el.get("cx", "0"))
            cy = float(el.get("cy", "0"))
            rx_el = float(el.get("rx", "0"))
            ry_el = float(el.get("ry", "0"))
            draw.ellipse(
                [_scale_x(cx - rx_el), _scale_y(cy - ry_el), _scale_x(cx + rx_el), _scale_y(cy + ry_el)],
                fill=fill if fill[3] > 0 else None,
                outline=stroke if stroke[3] > 0 else None,
                width=max(1, int(sw * scale)),
            )

        elif tag == "line":
            x1 = float(el.get("x1", "0"))
            y1 = float(el.get("y1", "0"))
            x2 = float(el.get("x2", "0"))
            y2 = float(el.get("y2", "0"))
            draw.line(
                [_scale_x(x1), _scale_y(y1), _scale_x(x2), _scale_y(y2)],
                fill=stroke if stroke[3] > 0 else (0, 0, 0, 255),
                width=max(1, int(sw * scale)),
            )

        elif tag == "text":
            x = float(el.get("x", "0"))
            y = float(el.get("y", "0"))
            text = el.text or ""
            if font and text.strip():
                draw.text(
                    (_scale_x(x), _scale_y(y)),
                    text.strip(),
                    fill=fill if fill[3] > 0 else (0, 0, 0, 255),
                    font=font,
                )

        for child in el:
            _render_element(child)

    _render_element(root)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def _render_svglib(
    svg: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
    transparent: bool = True,
) -> bytes:
    """Render SVG via svglib + reportlab."""
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
    except ImportError:
        raise PngConversionError("svglib/reportlab not installed for SVG rendering")

    try:
        import io
        drawing = svg2rlg(io.BytesIO(svg.encode("utf-8")))
        if drawing is None:
            raise PngConversionError("svglib returned None")
        if scale != 1.0:
            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)
        buf = io.BytesIO()
        renderPM.drawToFile(drawing, buf, fmt="PNG", bg=(0, 0, 0, 0) if transparent else None)
        buf.seek(0)
        return buf.read()
    except Exception as exc:
        raise PngConversionError(f"svglib rendering failed: {exc}") from exc


def html_to_png(
    html: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
    transparent: bool = True,
) -> bytes:
    """Render an HTML page to PNG via Playwright.

    Parameters
    ----------
    html : str
        Full HTML document string.
    scale : float, default 1.0
        Device scale factor for HiDPI output.
    background_color : str or None, default None
        CSS background color (ignored if *transparent* is True).
    output_width : int or None, default None
        Viewport width.
    output_height : int or None, default None
        Viewport height.
    transparent : bool, default True
        Whether to omit the background (alpha transparency).

    Returns
    -------
    bytes
        PNG image data.

    Raises
    ------
    PngConversionError
        If Playwright is unavailable or rendering fails.

    Notes
    -----
    This is a convenience wrapper around Playwright's screenshot
    functionality, similar to ``_render_playwright`` but accepting
    arbitrary HTML instead of SVG wrapped in HTML.
    """
    if importlib_util.find_spec("playwright") is None:
        raise PngConversionError("playwright is required for html_to_png")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            device_scale_factor=scale,
            viewport={"width": output_width or 800, "height": output_height or 600},
        )
        page.set_content(html)
        png_bytes = page.screenshot(full_page=True, omit_background=transparent)
        browser.close()

    return png_bytes


def _render_playwright(
    svg: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
    transparent: bool = True,
) -> bytes:
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found, import-untyped]

    has_bg = background_color is not None and not transparent
    bg_css = f"background: {background_color};" if has_bg else ""
    html_parts = [
        "<!DOCTYPE html><html><head><style>",
        f"  body {{ margin: 0; {bg_css} }}",
        "  svg { max-width: 100%; height: auto; }",
        "</style></head><body>",
        svg,
        "</body></html>",
    ]
    html = "\n".join(html_parts)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            device_scale_factor=scale,
            viewport={"width": output_width or 800, "height": output_height or 600},
        )
        page.set_content(html)
        png_bytes = page.screenshot(full_page=True, omit_background=transparent)
        browser.close()

    return png_bytes
