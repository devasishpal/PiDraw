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
        raise PngConversionError(
            f"{backend.__name__} failed: {exc}"
        ) from exc
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
            import cairosvg  # type: ignore[import-not-found, import-untyped]

            cairosvg.svg2png
            return _render_cairosvg
        except OSError as e:
            errors.append(f"cairosvg (Cairo library not found: {e})")
    else:
        errors.append("cairosvg not installed")

    if importlib_util.find_spec("playwright") is not None:
        return _render_playwright
    else:
        errors.append("playwright not installed")

    raise ImportError(
        "No SVG-to-PNG backend available.\n\n"
        "Options:\n"
        "  Install resvg CLI:  https://github.com/RazrFalcon/resvg/releases\n"
        "  pip install pidraw[png-playwright] && playwright install chromium\n"
        "  pip install pidraw[png]        (cairosvg - needs Cairo DLLs)\n\n"
        "Detected issues:\n"
        + "\n".join(f"  - {e}" for e in errors)
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
