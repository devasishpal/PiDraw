"""RenderResult dataclass — the universal output container for PiDraw."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RenderResult:
    """The output of a single render operation.

    Attributes
    ----------
    svg : str
        The rendered SVG as a UTF-8 string.  Always populated regardless
        of *output_format* — SVG is the canonical intermediate form.
    png : bytes | None
        PNG bytes if ``output_format='png'`` was requested, else None.
    language : str
        The detected or specified diagram language.
    engine_used : str
        Which engine produced this: ``'native'``, ``'cli:mmdc'``, ``'kroki'``, etc.
    render_time_ms : float
        Wall-clock time for the render in milliseconds.
    warnings : list[str]
        Non-fatal warnings emitted during rendering.
    cache_hit : bool
        True if this result was served from cache.
    source_hash : str
        SHA-256 of (language + source), the cache key.
    """

    svg: str
    png: bytes | None = None
    language: str = ""
    engine_used: str = ""
    render_time_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)
    cache_hit: bool = False
    source_hash: str = ""
    success: bool = True
    error: str | None = None

    def __len__(self) -> int:
        return len(self.svg)

    def save(self, path: str) -> None:
        """Save SVG or PNG to a file path. Format inferred from extension."""
        import pathlib

        p = pathlib.Path(path)
        if p.suffix.lower() == ".png":
            if self.png is None:
                raise ValueError(
                    "No PNG data in this RenderResult. Re-render with output_format='png'."
                )
            p.write_bytes(self.png)
        else:
            p.write_text(self.svg, encoding="utf-8")
