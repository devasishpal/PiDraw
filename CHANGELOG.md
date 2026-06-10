# Changelog

## 1.3.0 (2026-06-10)

### Added
- **TikZ native renderer** (`core/converters/tikz.py`) — pure Python TikZ-to-SVG converter. Handles `\node`, `\draw`, `\path`, `\scope`, `matrix of nodes`, basic shapes (rectangle, circle, ellipse, diamond), arrow types, colors, dash styles, font sizes. Previously required `pdflatex` + `pdf2svg`.
- **Mermaid native support expanded** — added dedicated parsers for `sequenceDiagram`, `classDiagram`, `stateDiagram`/`stateDiagram-v2`, `erDiagram`, `pie` chart, and `gantt` chart. Previously only `graph`/`flowchart` worked natively.
- **BPMN native BPMN 2.0 renderer** (`engines/bpmn.py`) — parses XML/JSON BPMN 2.0 and renders via `drawsvg`. Previously required `bpmn-to-svg` CLI.

### Changed
- **Batteries-included dependencies** — `drawsvg`, `cairosvg`, and `python-docx` moved from optional extras to hard requirements. Single `pip install pidraw` now covers all renderers, PNG export, and DOCX export.
- **TikZ engine** (`engines/tikz.py`) — auto-detects LaTeX/PDF tooling; falls back to native TikZ converter when absent.
- **Mermaid engine** (`engines/mermaid.py`) — `stateDiagram-v2` and `stateDiagram` no longer require `mmdc` CLI.
- **All renderers** — BPMN, Vega, Vega-Lite, Structurizr, WaveDrom, Graphviz, D2, PlantUML now have native fallback when CLI is absent.

### Removed
- No more dependencies on `mmdc`, `bpmn-to-svg`, `pdflatex`, `pdf2svg`, `dvisvgm`, or `vg2svg` CLI tools for basic usage.

## 1.2.1 (2026-06-08)

### Fixed
- **CLI `render` crash on stdout** — `sys.stdout.write(result)` passed a `RenderResult` object instead of string; changed to `result.svg` so SVG output prints correctly without `-o` flag.
- **CLI `_write_output` type mismatch** — `_write_output` now accepts `RenderResult` objects and uses `.save()`, fixing file output for all callers.
- **Markmap import crash** — `markmap_render.js` missing from the wheel because `[tool.setuptools.package-data]` didn't include `*.js` files. Added `pidraw = ["**/*.js"]` so the script ships with the package.
- **Engine init crash on import** — `MarkmapRenderer.__init__` raised `RenderError` (not caught by `engines/__init__.py`), crashing the entire CLI. Added `except PiDrawError` catch-all so any engine failure registers a `_BrokenRenderer` instead.

### Changed
- `pyproject.toml` — added `[tool.setuptools.package-data]` to bundle JS assets

## 1.2.0 (2026-06-08)

### Added
- Mermaid `graph`/`flowchart` support for `-->|label|` edge label syntax
- 20 mermaid diagram files covering all standard diagram types (flowchart, sequence, class, state, ER, journey, gantt, pie, gitgraph, mindmap, timeline, block, C4, network, packet, quadrant, requirement, sankey, XY chart)

### Fixed
- **Stale viewport in all layout engines** — LayeredLayout, GridLayout, TreeLayout, FlowLayout overrode node positions but kept the converter's stale viewport, causing SVG `viewBox` to clip content. All engines now always recompute the viewport from actual positions after layout.
- **Insufficient viewport padding** — viewport padding changed from a fixed 20px to `max(40, content_width * 0.15, content_height * 0.15)`, ensuring the rendered PNG has ≥60px margins for `trim_png` to safely add padding without cropping content.
- **MermaidConverter edge pipe labels** — `_EDGE_PATTERN` now matches `A -->|label| B` syntax; previously the `|label|` between arrow and target caused the entire edge to fail to parse.
- **MermaidConverter node decoration fallthrough** — `_parse_node_decoration` returned the first word of the remainder (e.g. `-->`) as the label when no decoration matched. Changed to return empty string; caller falls back to node ID.
- **MermaidConverter arrow style detection** — `-.->`/`-..` correctly classified as DOTTED, `-.-` as DASHED (was incorrectly DOTTED due to `-.-` matching the DOTTED check before DASHED).

### Changed
- `trim_png()` default padding changed from 2px to `max(50, min_dim * 0.08)` to prevent content clipping during PNG trimming.

## 1.1.0 (2026-06-08)

### Added
- `EngineNotAvailableError`, `RenderError`, `RenderTimeoutError`, `ParseError`,
  `LayoutError`, `OptimizationError`, `PngConversionError` typed exceptions
- `RenderResult` dataclass with `.svg`, `.png`, `.language`, `.engine_used`,
  `.render_time_ms`, `.warnings`, `.cache_hit`, `.source_hash`, `.save()`, `__len__`
- Async API: `arender()` and `arender_file()` in `pidraw.async_api`
- `Renderer` class with `.render()`, `.render_file()`, `.arender()`, `.available_engines()`
- `resvg` CLI as first-priority PNG backend (falls back to cairosvg → playwright)
- SVG quality enhancement: font stack normalization, stroke normalization, marker dedup
- `PngConversionError` wrapping for all PNG backend failures
- `py.typed` marker file for PEP 561 compliance
- New test suites: `test_render_result.py`, `test_async.py`, `test_renderer_class.py`, `test_png.py`

### Changed
- `render()` now returns `RenderResult` instead of `str`/`bytes`
- `render()` accepts `timeout` and `theme` parameters
- All renderers raise typed exceptions (`EngineNotAvailableError`, `RenderError`, `RenderTimeoutError`)
- Mermaid renderer falls back to native converter for basic diagram types when `mmdc` is absent
- Kroki renderer uses `urllib.request` (stdlib), respects `PIDRAW_KROKI_URL` env var
- Excalidraw renderer handles per-element errors gracefully
- CLI-based engines raise `EngineNotAvailableError` with actionable `setup_command` hints
- `Development Status` updated from Alpha to Beta
- `pool.py` `RenderResult` renamed to `PoolRenderResult` to avoid naming conflict

### Removed
- Background-thread npm install on import (auto-install behavior removed)

### Fixed
- All 488 existing tests pass with new exception hierarchy
- Backward compatibility maintained via `RenderingError` and `UnsupportedLanguageError` aliases
