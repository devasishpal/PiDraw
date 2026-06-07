# Architecture

PiDraw is built as a modular pipeline that transforms diagram source code into optimised SVG through a series of pluggable stages.

---

## Overview

Diagram source flows through the pipeline as follows:

```
Source Input
    |
    v
[ Detector ]  -- regex-based, confidence-scored language identification
    |
    v
[ Renderer ]  -- dispatches to native or CLI-based engine via plugin registry
    |
    v
[ Optimizer ] -- multi-pass SVG cleanup, minification, and structural optimisation
    |
    v
Optimised SVG
```

Optional middleware hooks allow plugins to intercept and modify the source before rendering or the SVG after optimisation. A caching layer (memory + disk) sits transparently in the pipeline to avoid redundant re-renders.

---

## Component Descriptions

### Detector

The detector (`pidraw/detector.py`) identifies diagram languages from source text using a set of ordered regex rules. Each rule produces a confidence score between 0.0 and 1.0; the highest-scoring match wins. Rules are ordered from most specific (e.g. `^@start\w+` for PlantUML at 0.99) to more generic (e.g. ASCII art heuristics at 0.55). The detector also inspects file extensions when called from `render_file()`.

### Renderer Registry

The registry (`pidraw/registry.py`) is a plugin-based system for discovering and selecting renderer implementations. Renderers are registered by language name (e.g. `"mermaid"`) and retrieved at render time. Third-party packages can register custom renderers via the `pidraw.renderers` entry point group in their `pyproject.toml`. The registry supports registration, lookup, listing, and full clearing (useful in testing).

### Renderer Engines

Each diagram language has one or more renderer engines (`pidraw/engines/`). Engines are subclasses of `BaseRenderer` and come in two flavours:

- **Native renderers** — Built into PiDraw (Mermaid, Graphviz, PlantUML, D2, ASCII). They produce SVG directly in-process using PiDraw's own intermediate representation (IR).
- **CLI renderers** — Wrap external command-line tools (e.g. `mmdc`, `dot`, `plantuml`, `d2`). They invoke the tool as a subprocess, capture stdout, and return the SVG string. These are used for languages where a full native implementation is not yet available.

Engines are auto-registered by importing `pidraw.engines`, which triggers each engine module to call `register_renderer()`.

### SVG Optimizer

The optimizer (`pidraw/optimizer/`) is a multi-pass pipeline that reduces SVG size and normalises output. It is organised into three levels:

- **Fast** — Lightweight passes: remove comments, remove editor metadata, trim whitespace.
- **Balanced** (default) — All fast passes plus: remove unused defs, merge duplicate defs, collapse redundant groups, remove empty elements, normalise transforms, simplify paths, normalise attribute ordering.
- **Maximum** — All registered passes, including experimental or expensive ones.

Each pass is a function `(str) -> str` registered by name in `PASS_REGISTRY`. Passes can be selected individually, composed, or extended by plugins. The `optimize_svg()` and `optimize_by_level()` entry points validate input/output SVG structure and report metrics (bytes saved, reduction percentage, elapsed time).

### Native Rendering Engine

The native rendering pipeline (`pidraw/pipeline.py` and `pidraw/core/`) converts source code to SVG entirely in-process:

```
Source
  |
  v
[ Converter ]  -- language-specific parser (e.g. MermaidConverter, GraphvizConverter)
  |                produces an IR Diagram object (nodes, edges, shapes, labels)
  v
[ Layout ]     -- assigns positions to nodes and routes edges
  |
  v
[ Theme ]      -- applies visual styles (colours, fonts, stroke widths)
  |
  v
[ SVG Backend ]-- renders the styled Diagram IR to SVG string
```

The IR is defined in `pidraw/core/models.py` with types for `Diagram`, `Node`, `Edge`, `Shape`, `Group`, `Layout`, `Viewport`, and more. Converters in `pidraw/core/converters/` parse each language into this common representation. The `ExportPipeline` class orchestrates the full flow and exposes `render_native()` and `render_native_from_diagram()` as public entry points.

### Caching Layer

The cache (`pidraw/cache.py`) uses a two-tier architecture:

- **Memory tier** — LRU-evicted dict of `CacheEntry` objects for hot renders. Configurable max entries (default 10,000).
- **Disk tier** — JSON files keyed by SHA-256 digest of the source (plus optional language discriminator).

Both tiers support TTL-based expiry. The `CacheManager` class provides `get()`, `set()`, `clear()`, `remove()`, and `stats()` operations. Caching is transparently integrated into the `RenderPool` and can be used standalone with any `render()` call.

### Render Pool

The pool (`pidraw/pool.py`) provides parallel batch rendering using `concurrent.futures`. It selects between `ThreadPoolExecutor` (for I/O-bound subprocess renderers) and `ProcessPoolExecutor` (for CPU-bound native rendering). Key features:

- Configurable worker count (defaults to `CPU count * 2`).
- Cache integration: cached sources skip rendering entirely.
- Error isolation: a failure in one task does not affect others.
- Per-task `RenderResult` objects with timing, language, and error information.
- `BatchRenderSummary` for aggregate reporting.

### Incremental Renderer

The incremental renderer (`pidraw/incremental.py`) tracks source file state via SHA-256 hashes and modification times. It allows build pipelines to skip unchanged files entirely.

- `needs_render()` checks whether a file has changed since the last recorded render.
- `record_render()` persists the new state after a successful render.
- State is persisted to a JSON file for reuse across process restarts.
- Statistics (files checked, rendered, skipped, failed) are accumulated for reporting.

When combined with `pidraw watch`, the incremental renderer enables continuous diagram rebuilds with no redundant work.

---

## Data Flow Diagram

```
                        +-----------+
                        | Source    |
                        | File/Disk |
                        +-----+-----+
                              |
                              v
+-----------------------------+------------------------------+
|                       Pipeline                             |
|  +-----------+    +----------+    +-----------+            |
|  | Detector  |--->| Renderer |--->| Optimizer |---> SVG    |
|  | (regex    |    | (plugin  |    | (multi-   |            |
|  |  + conf.) |    |  lookup) |    |  pass)    |            |
|  +-----------+    +----------+    +-----------+            |
|       |               |                |                   |
|       v               v                v                   |
|  +-----------+  +----------+  +------------------+         |
|  | Extension |  | Registry |  | PASS_REGISTRY    |         |
|  | heuristics|  | (entry   |  | (10+ pass fns)   |         |
|  +-----------+  |  points) |  +------------------+         |
|                 +----------+                               |
+------------------------------------------------------------+
       |               |                |
       v               v                v
  +--------+      +---------+      +---------+
  | Native |      | CLI     |      | fast /  |
  | Engine |      | tools   |      | balanced|
  +--------+      +---------+      | maximum |
       |               |           +---------+
       v               v
  +---------+     +---------+
  | IR      |     | mmdc /  |
  | Pipeline|     | dot /   |
  |(conv. + |     | plantuml|
  | layout +|     | etc.    |
  | theme + |     +---------+
  | backend)|
  +---------+

  +------------------+   +-----------------+
  | CacheManager     |   | RenderPool      |
  | (memory + disk,  |   | (ThreadPool /   |
  |  TTL-based)      |   |  ProcessPool)   |
  +------------------+   +-----------------+

  +------------------+
  | Incremental      |
  | Renderer         |
  | (SHA-256 state)  |
  +------------------+
```

---

## Design Principles

1. **Unified API** — Every language is rendered through the same function call: `render()`. The pipeline abstracts all engine-specific details.

2. **Plugin-first** — Renderers, detectors, and optimisers are all discoverable at runtime via Python entry points. The core ships with native implementations for the most common languages; everything else is an installable plugin.

3. **Fail-safe isolation** — A crash in one renderer or plugin never brings down the entire pipeline. Errors are captured per-task in batch mode and per-plugin during discovery.

4. **Performance by default** — Parallel batch rendering, content-addressable caching, incremental builds, and lazy renderer loading ensure PiDraw scales from one-off diagrams to CI pipelines with thousands of files.

5. **Transparency** — Every stage reports metrics: detection confidence, render time, optimisation savings, cache hit rates. Users always know what happened and why.

6. **Standards-compliant output** — The SVG optimiser validates input and output structure, producing well-formed, standards-compliant SVG that works in any browser or tool.

7. **Extensible at every layer** — Plugins can provide new renderers, override detection, add optimisation passes, or inject middleware. The internal IR (Diagram model) allows third-party converters to integrate without touching the rendering engine.
