# Plugin System

## Overview

PiDraw uses a plugin-based architecture where every rendering backend is an independent plugin. The core library handles orchestration, language detection, SVG optimization, and caching -- renderers only need to convert diagram source text to SVG.

The plugin system supports three registration mechanisms:

1. **Decorator** -- inline registration via `@register_renderer()`
2. **Entry points** -- declarative registration via `pyproject.toml`
3. **Manual** -- programmatic registration via `register_renderer()`

## BaseRenderer

All renderers extend `pidraw.engines.base.BaseRenderer`:

```python
from abc import ABC, abstractmethod

class BaseRenderer(ABC):
    name: str = ""

    @abstractmethod
    def render(self, source: str) -> str:
        """Convert diagram source to SVG."""
```

The only required method is `render(source)`, which accepts a diagram source string and returns an SVG string. Set `name` to a human-readable identifier for the renderer.

## Registration via Decorator

Use `@register_renderer(name)` to register a renderer class inline. PiDraw automatically instantiates the class:

```python
from pidraw.engines.base import BaseRenderer
from pidraw.registry import register_renderer

@register_renderer("blockdiag")
class BlockDiagRenderer(BaseRenderer):
    name = "BlockDiag"

    def render(self, source: str) -> str:
        # implementation
        return "<svg>...</svg>"
```

The decorator accepts the language name as its first argument and registers an instance of the decorated class.

## Registration via Entry Points

Third-party packages can register renderers without modifying PiDraw by adding an entry point to `pyproject.toml`:

```toml
[project.entry-points."pidraw.renderers"]
blockdiag = "pidraw_blockdiag:BlockDiagRenderer"
```

The entry point value is a dotted path to a `BaseRenderer` subclass (or an instance). PiDraw discovers these automatically via `discover_plugins()`.

## Plugin Discovery

`pidraw.discover_plugins()` scans the `pidraw.renderers` entry point group using `importlib.metadata` and returns a dictionary of discovered renderers:

```python
from pidraw.registry import discover_plugins

plugins = discover_plugins()
for name, renderer in plugins.items():
    print(f"Found plugin: {name} ({type(renderer).__name__})")
```

Discovery does **not** modify the internal registry. Use `register_renderer()` to add discovered plugins to the active registry.

## Listing Plugins

`pidraw.list_renderers()` returns a copy of all currently registered renderers:

```python
from pidraw.registry import list_renderers

for name, renderer in list_renderers().items():
    print(f"{name}: {type(renderer).__name__}")
```

## Example: Custom Renderer

The following example implements a full custom renderer that converts a simple ASCII-art diagram language to SVG:

```python
import re
from xml.sax.saxutils import escape

from pidraw.engines.base import BaseRenderer
from pidraw.exceptions import RenderingError
from pidraw.registry import register_renderer

@register_renderer("asciiart")
class AsciiArtRenderer(BaseRenderer):
    name = "ASCII Art Renderer"

    MAX_SOURCE_SIZE = 512 * 1024  # 512 KB

    def render(self, source: str) -> str:
        self._validate_input(source)
        svg = self._convert_to_svg(source)
        self._validate_output(svg)
        return self._wrap_in_svg(svg)

    def _validate_input(self, source: str) -> None:
        if not source or not source.strip():
            raise RenderingError("Source is empty")
        if len(source) > self.MAX_SOURCE_SIZE:
            raise RenderingError(
                f"Source exceeds maximum size of {self.MAX_SOURCE_SIZE} bytes"
            )

    def _validate_output(self, svg: str) -> None:
        if not svg:
            raise RenderingError("Renderer produced empty output")
        if "<svg" not in svg.lower():
            raise RenderingError("Output does not contain an <svg> element")

    def _wrap_in_svg(self, content: str) -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="800" height="600" viewBox="0 0 800 600">'
            f"{content}"
            "</svg>"
        )

    def _convert_to_svg(self, source: str) -> str:
        lines = source.splitlines()
        elements = []
        for y, line in enumerate(lines):
            text = escape(line.rstrip())
            elements.append(
                f'<text x="10" y="{(y * 20) + 20}" '
                f'font-family="monospace" font-size="14">{text}</text>'
            )
        return "\n".join(elements)
```

## Error Handling Guidelines

- Raise `RenderingError` for any failure during rendering (invalid input, CLI failure, timeout).
- Validate input before processing to fail fast with clear messages.
- Validate output to catch corrupted or empty results.
- Use `RecoverableRenderingError` when the error might resolve on retry (e.g., network timeout).
- Never raise generic `Exception`; use the PiDraw exception hierarchy.
- Wrap third-party exceptions and re-raise as `RenderingError` with context.
