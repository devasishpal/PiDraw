"""Async rendering API for PiDraw.

Provides ``arender`` and ``arender_file`` as async counterparts to
the synchronous ``render`` / ``render_file`` functions.
"""

from __future__ import annotations

from pidraw.renderer import render, render_file
from pidraw.result import RenderResult


async def arender(
    source: str,
    *,
    language: str | None = None,
    optimize: str | None = None,
    output_format: str = "svg",
    timeout: float = 30.0,
    theme: str = "light",
) -> RenderResult:
    """Async version of :func:`render`. Safe to call from any async framework.

    Parameters
    ----------
    source : str
        The diagram source code.
    language : str | None
        Explicit language identifier.  Auto-detected when ``None``.
    optimize : str | None
        Optimisation level (``"fast"``, ``"balanced"``, ``"maximum"``).
    output_format : str
        Output format.  ``"svg"`` (default) or ``"png"``.
    timeout : float
        Maximum render time in seconds.
    theme : str
        Theme name to apply.

    Returns
    -------
    RenderResult
        The rendered output.

    Raises
    ------
    PiDrawError
        On any rendering failure.
    """
    import asyncio

    loop = asyncio.get_event_loop()

    def _sync_render() -> RenderResult:
        return render(
            source,
            language=language,
            format=output_format,
            optimize=optimize or False,
            timeout=timeout,
            theme=theme,
        )

    return await loop.run_in_executor(None, _sync_render)


async def arender_file(path: str, **kwargs: object) -> RenderResult:
    """Async version of :func:`render_file`.

    Parameters
    ----------
    path : str
        Path to the diagram source file.
    **kwargs
        Forwarded to :func:`arender`.

    Returns
    -------
    RenderResult
        The rendered output.
    """
    import asyncio

    source: str
    try:
        import aiofiles  # noqa: F401

        async with aiofiles.open(path, encoding="utf-8") as f:  # type: ignore[union-attr]
            source = await f.read()  # type: ignore[union-attr]
    except ImportError:
        source = await asyncio.to_thread(
            lambda: open(path, "r", encoding="utf-8").read()
        )
    return await arender(source, **kwargs)
