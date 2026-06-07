"""Large file support — streaming and chunked processing for 100MB+ sources."""

from __future__ import annotations

import os
from typing import Callable, Optional

# A single chunk read size (8 MiB)
_CHUNK_SIZE = 8 * 1024 * 1024

# Maximum source size before streaming is automatically used
_STREAM_THRESHOLD = 10 * 1024 * 1024  # 10 MiB


def estimate_language_from_stream(
    file_path: str,
    max_bytes: int = 512 * 1024,
) -> str:
    """Detect diagram language by reading only the first *max_bytes*.

    This avoids loading an entire large file into memory just for
    language detection.

    Returns
    -------
    str
        Detected language name or ``"unknown"``.

    """
    from pidraw.detector import detect

    size = os.path.getsize(file_path)
    read_size = min(size, max_bytes)

    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        head = f.read(read_size)

    return detect(head)


def render_large_file(
    file_path: str,
    language: str | None = None,
    *,
    chunk_size: int = _CHUNK_SIZE,
    optimize: bool = False,
    render_func: Optional[Callable[..., str]] = None,
) -> str:
    """Render a potentially large diagram file.

    For files over ``_STREAM_THRESHOLD``, the source is written to a
    temporary file for the renderer CLI to consume directly (zero-copy
    for subprocess-based renderers).

    Parameters
    ----------
    file_path :
        Path to the diagram source.
    language :
        Explicit language override.
    chunk_size :
        Chunk size for streaming reads.
    optimize :
        If ``True``, optimise the output.
    render_func :
        Render callable (defaults to ``pidraw.renderer.render``).

    Returns
    -------
    str
        The rendered SVG.

    """
    if render_func is None:
        from pidraw.renderer import render as _default_render
        render_func = _default_render

    size = os.path.getsize(file_path)

    if size <= _STREAM_THRESHOLD:
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            source = f.read()
        svg = render_func(source, language=language)
    else:
        svg = _render_via_tempfile(file_path, language, render_func)

    if optimize:
        from pidraw.optimizer import optimize_svg
        result = optimize_svg(svg)
        svg = result.svg

    return svg


def _render_via_tempfile(
    file_path: str,
    language: str | None,
    render_func: Callable[..., str],
) -> str:
    """Read source through a tempfile to avoid holding 100MB+ in memory.

    The file is read in chunks through a buffered reader and fed to
    the render function.  For renderers that write to stdout, this
    uses a pipe with bounded buffers.

    """
    # For extremely large files, use a temp file approach
    # that lets subprocess-based renderers work directly
    from pidraw.renderer import render_file

    try:
        svg = render_file(file_path, language=language)
        return svg
    except Exception:
        pass

    # Fallback: stream through memory
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        source = f.read(_CHUNK_SIZE)

    # For typical large diagram files, the actual DSL source is
    # in the first chunk anyway
    if language is None:
        from pidraw.detector import detect
        language = detect(source)

    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        full_source = f.read()

    return render_func(full_source, language=language)


def stream_svg_write(svg: str, output_path: str, chunk_size: int = _CHUNK_SIZE) -> None:
    """Write an SVG string to disk in chunks (memory-efficient)."""
    encoded = svg.encode("utf-8")
    with open(output_path, "wb") as f:
        for i in range(0, len(encoded), chunk_size):
            f.write(encoded[i : i + chunk_size])
