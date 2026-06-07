from __future__ import annotations

from importlib import util as importlib_util
from typing import Optional


def svg_to_png(
    svg: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
) -> bytes:
    backend = _detect_backend()
    return backend(
        svg,
        scale=scale,
        background_color=background_color,
        output_width=output_width,
        output_height=output_height,
    )


def _detect_backend():
    errors: list[str] = []

    if importlib_util.find_spec("cairosvg") is not None:
        try:
            import cairosvg  # type: ignore[import-not-found, import-untyped]
            cairosvg.svg2png  # verify it actually works
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
        "  pip install pidraw[png]        (cairosvg - needs Cairo DLLs)\n"
        "  pip install playwright && playwright install chromium  (headless browser)\n\n"
        "Detected issues:\n"
        + "\n".join(f"  - {e}" for e in errors)
    )


def _render_cairosvg(
    svg: str,
    scale: float = 1.0,
    background_color: Optional[str] = None,
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
) -> bytes:
    import cairosvg  # type: ignore[import-untyped]

    kwargs: dict = {"scale": scale}
    if background_color is not None:
        kwargs["background_color"] = background_color
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
) -> bytes:
    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found, import-untyped]

    has_bg = background_color is not None
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
        png_bytes = page.screenshot(full_page=True, omit_background=True)
        browser.close()

    return png_bytes
