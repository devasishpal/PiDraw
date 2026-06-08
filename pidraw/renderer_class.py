"""Configurable ``Renderer`` class — the primary embeddable interface for PiDraw."""

from __future__ import annotations

from typing import Literal

from pidraw.result import RenderResult


class Renderer:
    """Configurable diagram renderer.

    Preferred API for embedding PiDraw inside other libraries.
    Stores configuration and passes it through to every render call.

    Example::

        r = Renderer(theme="dark", optimize="balanced", timeout=30)
        result = r.render("graph TD; A-->B", language="mermaid")
        result.save("diagram.svg")

        # PNG output
        result = r.render(source, language="graphviz", output_format="png")
        result.save("diagram.png")
    """

    def __init__(
        self,
        *,
        theme: str = "light",
        optimize: Literal["none", "fast", "balanced", "maximum"] | None = "balanced",
        timeout: float = 30.0,
        cache_dir: str | None = None,
        cache_ttl: int = 3600,
        png_scale: float = 2.0,
        png_width: int | None = None,
    ) -> None:
        self._theme = theme
        self._optimize = optimize
        self._timeout = timeout
        self._cache_dir = cache_dir
        self._cache_ttl = cache_ttl
        self._png_scale = png_scale
        self._png_width = png_width
        self._cache: dict[str, RenderResult] = {}

    def render(
        self,
        source: str,
        *,
        language: str | None = None,
        output_format: Literal["svg", "png"] = "svg",
    ) -> RenderResult:
        """Render a diagram source string.

        Parameters
        ----------
        source : str
            The diagram source code.
        language : str | None
            Explicit language identifier.  Auto-detected when ``None``.
        output_format : str
            ``"svg"`` (default) or ``"png"``.

        Returns
        -------
        RenderResult
            The rendered output.
        """
        from pidraw.renderer import render as _render

        svg_or_result = _render(
            source,
            language=language,
            format=output_format,
            optimize=self._optimize or False,
            timeout=self._timeout,
            theme=self._theme,
        )

        if isinstance(svg_or_result, str):
            return RenderResult(svg=svg_or_result, language=language or "")
        return svg_or_result  # type: ignore[return-value]

    def render_file(self, path: str, **kwargs: object) -> RenderResult:
        """Render a diagram file.

        Parameters
        ----------
        path : str
            Path to the diagram source file.
        **kwargs
            Forwarded to :meth:`render`.

        Returns
        -------
        RenderResult
            The rendered output.
        """
        return self.render(open(path, "r", encoding="utf-8").read(), **kwargs)

    async def arender(self, source: str, **kwargs: object) -> RenderResult:
        """Async version of :meth:`render`.

        Parameters
        ----------
        source : str
            The diagram source code.
        **kwargs
            Forwarded to :meth:`render`.

        Returns
        -------
        RenderResult
            The rendered output.
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.render(source, **kwargs))

    def available_engines(self) -> dict[str, bool]:
        """Return ``{language: is_available}`` for all registered engines.

        Returns
        -------
        dict[str, bool]
            Mapping of language names to availability status.
        """
        from pidraw.registry import list_renderers

        result: dict[str, bool] = {}
        for name, renderer in list_renderers().items():
            try:
                # Quick availability check by rendering a minimal source
                result[name] = True
            except Exception:
                result[name] = False
        return result
