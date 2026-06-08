# Changelog

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
