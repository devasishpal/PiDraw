# PiDraw

PiDraw is a universal diagram rendering engine for Python that converts textual diagram descriptions into clean, scalable SVG output. Whether you are documenting architecture, designing flowcharts, or visualizing data structures, PiDraw provides a single unified interface across 15+ diagram languages.

## Key Features

- **Universal rendering** — Supports Mermaid, PlantUML, Graphviz (DOT), BlockDiag, D2, ASCII art, and 10+ additional formats through a single API
- **Automatic language detection** — Identifies diagram language from input with confidence scoring, so you can render without specifying a format
- **Multi-pass SVG optimization** — Three optimization levels (basic, balanced, aggressive) that minify, reorganize, and compress SVG output
- **Plugin system** — Extend PiDraw with custom renderers, optimizers, and themes using decorators or entry points
- **Batch and parallel rendering** — Process hundreds of diagrams concurrently with configurable parallelism
- **Render caching** — In-memory and disk-based caching with TTL, LRU eviction, and cache warming
- **Incremental builds** — Re-render only changed files by comparing content hashes
- **Watch mode** — Watch directories for file changes and auto-render with live reload
- **Native rendering pipeline** — Convert textual input through an engine pipeline (converters -> layout -> themes -> SVG) for full control
- **CLI** — 10 commands covering render, batch, watch, cache, diagnose, analyze, benchmark, init, config, and plugin management
- **Recovery mechanisms** — Automatic retry with exponential backoff and configurable retry policies
- **Large file streaming** — Stream large diagrams efficiently without loading entirely into memory
- **Diagnostics and analysis** — Built-in tools for cache hit-rate analysis, render profiling, and diagram complexity scoring
- **Benchmarking suite** — Measure and compare rendering performance across engines and configurations

## Quick Start

```python
from pidraw import Drawing

# Auto-detect language and render
drawing = Drawing("graph TD; A-->B; A-->C;")
svg = drawing.render()

# Or specify the language explicitly
drawing = Drawing.from_string(
    "graph TD; A-->B; A-->C;",
    language="mermaid"
)
svg = drawing.render(optimize=True)

# Batch render multiple diagrams
drawings = Drawing.from_files("diagrams/*.puml")
results = Drawing.batch(drawings, parallel=True)

# Save to file
drawing.save("output.svg")
```

## Supported Languages

Mermaid, PlantUML, Graphviz (DOT), BlockDiag (blockdiag, seqdiag, actdiag, nwdiag), D2, ASCII art (ditaa, svgbob), Excalidraw, TikZ, PGF, MSG, and more via plugins.

## Links

- Documentation: https://pidraw.dev
- Repository: https://github.com/example/pidraw
- Issue tracker: https://github.com/example/pidraw/issues
- PyPI: https://pypi.org/project/pidraw/
