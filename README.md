# PiDraw

> Universal diagram rendering platform — convert any diagram language to SVG.

PiDraw is a Python library and CLI tool that renders source code from **14+ diagram languages** into optimized SVG. It supports native (pure Python) rendering for 7 formats, external CLI tools for the rest (auto-installed on first use), SVG optimization, quality enhancement, caching, parallel batch processing, watch mode, and a plugin architecture.

---

## Supported Formats

| Format | Language ID | File Extensions | Render Method |
|---|---|---|---|
| Mermaid | `mermaid` | `.mmd`, `.mermaid` | CLI (`mmdc`) or Native |
| PlantUML | `plantuml` | `.puml`, `.plantuml`, `.iuml` | CLI (`plantuml`) or Native |
| Graphviz DOT | `graphviz` | `.dot`, `.gv` | CLI (`dot`) or Native |
| D2 | `d2` | `.d2` | CLI (`d2`) or Native |
| ASCII Art | `ascii` | `.txt` | **Native** (pure Python) |
| BPMN 2.0 | `bpmn` | `.bpmn` | CLI (`bpmn-svg`) |
| Markmap | `markmap` | `.mm` | CLI (`markmap` + Playwright) |
| Nomnoml | `nomnoml` | `.noml` | CLI (`nomnoml`) |
| WaveDrom | `wavedrom` | `.json` | CLI (`wavedrom-cli`) |
| Structurizr | `structurizr` | `.dsl` | CLI (`structurizr-cli` → PlantUML) |
| Vega | `vega` | `.json` | CLI (`vg2svg`) |
| Vega-Lite | `vega-lite` | `.json` | **Native** (`vl-convert-python`) or CLI |
| Excalidraw | `excalidraw` | `.json`, `.excalidraw` | **Native** (pure Python) |
| Kroki | `kroki` | `.txt`, `.kroki` | **HTTP API** (no CLI needed) |
| TikZ | `tikz` | `.tex` | CLI (`pdflatex` + `pdf2svg`) |

**7 formats work immediately with no extra tools** — mermaid, plantuml, graphviz, d2, ascii, excalidraw, kroki.

---

## Installation

```bash
# Install from PyPI (recommended)
pip install pidraw

# Or install from source
git clone https://github.com/devasishpal/PiDraw.git
cd PiDraw
pip install -e .
```

On first import, missing CLI tools (npm packages, structurizr-cli, Playwright Chromium) are automatically installed in a background thread. You can also trigger setup manually:

```bash
pidraw setup
```

---

## Quick Start

```bash
# Render a single diagram
pidraw render diagram.mmd output.svg

# Auto-detect language
pidraw detect diagram.txt

# Full analysis with diagnostics
pidraw analyze diagram.puml

# Batch render all diagrams in a directory
pidraw batch *.mmd *.puml --output-dir ./svg

# Watch for changes and auto-render
pidraw watch *.mmd --output-dir ./svg

# List all supported formats with live availability
pidraw formats

# Optimize an existing SVG
pidraw optimize diagram.svg -o optimized.svg

# Run benchmarks
pidraw benchmark
```

### Python API

```python
from pidraw import render

# Explicit language
svg = render("graph TD; A-->B", language="mermaid")

# Auto-detect
svg = render("digraph { A -> B }")

# With optimization
svg = render(source, language="graphviz", optimize="balanced")

# With quality enhancement
svg = render(source, language="plantuml", quality=True)

# Render from file
from pidraw import render_file
svg = render_file("diagram.mmd")
```

---

## CLI Reference

### `pidraw render <file> [options]`

| Option | Description |
|---|---|
| `-o, --output FILE` | Output SVG file (default: stdout) |
| `-l, --language TEXT` | Explicit language (skip auto-detection) |
| `-O, --optimize` | Apply SVG optimization |
| `-q, --quiet` | Suppress non-error output |
| `-v, --verbose` | Verbose output |
| `-d, --debug` | Debug output |

### `pidraw batch <paths...> [options]`

| Option | Description |
|---|---|
| `--output-dir DIR` | Output directory for SVGs |
| `-l, --language TEXT` | Language override for all files |
| `-O, --optimize` | Enable optimization |
| `-r, --recursive` | Scan directories recursively |
| `-w, --workers INT` | Parallel worker count (default: CPU count) |
| `--debounce FLOAT` | Watch debounce seconds (default: 1.0) |

### `pidraw formats [options]`

Lists all supported diagram formats. Use `-v` for a live status table showing which engines and CLI tools are available on your system.

### `pidraw analyze <file> [options]`

Full diagnostic report: detected language, confidence, renderer, warnings, SVG length, optimization stats.

### `pidraw setup`

Auto-install missing CLI tools:
- npm: `nomnoml`, `markmap-cli`, `wavedrom-cli`, `vega-cli`, `vega-lite`, `bpmn-svg-generator`, `playwright`
- Java: structurizr-cli (98MB download from GitHub)
- Browser: Playwright Chromium (used by markmap and bpmn renderers)
- Python: `vl-convert-python`

### `pidraw benchmark [--quick]`

Runs performance benchmarks for render speed, optimization, cache efficiency, and large diagrams.

---

## Architecture

```
Source Code (string or file)
    │
    ▼
detect_language()  ──►  Language ID (e.g. "mermaid")
    │
    ▼
get_renderer(language)  ──►  Engine Registry
    │
    ├── CLI-Based Renderer
    │       └── subprocess → temp file/pipe → SVG
    │
    ├── NativeRenderer (for converter-supported languages)
    │       ├── converter.parse(source) → Diagram model
    │       ├── apply_layout(diagram) → positioned nodes
    │       ├── apply_theme(diagram) → styled diagram
    │       └── SvgBackend.render(diagram) → SVG string
    │
    ├── KrokiRenderer (HTTP POST to kroki.io)
    │
    └── ExcalidrawRenderer (pure Python JSON → SVG)
    │
    ▼
[Optional] optimize_svg(svg, level="balanced")
    │   10 passes: comments → metadata → defs → groups → paths → ...
    ▼
[Optional] QualityProcessor.process(svg)
    │   viewBox → text alignment → arrow heads → spacing → paths
    ▼
Output SVG string
```

### Engines

Each diagram format has a dedicated renderer engine in `pidraw/engines/`. Engines auto-register on import; if a CLI tool is missing and no native fallback exists, a `_BrokenRenderer` placeholder is registered instead (raises a helpful error at render time).

### Converters

5 formats have pure-Python parsers (`pidraw/core/converters/`) that produce an internal `Diagram` model, which `SvgBackend` renders to SVG — no CLI tools needed:

| Converter | What it parses |
|---|---|
| `MermaidConverter` | `graph TD`, `flowchart`, `sequenceDiagram`, `classDiagram`, etc. |
| `PlantUMLConverter` | `@startuml` blocks, participants, actors, arrows |
| `GraphvizConverter` | `digraph`/`graph` statements with attributes |
| `D2Converter` | D2 node/edge syntax with shapes and styles |
| `ASCIIConverter` | Simple box-drawing diagrams (`+--+` boxes, `-->` arrows) |

### SVG Optimizer

Three optimization levels (`pidraw/optimizer/`):

| Level | Passes | Description |
|---|---|---|
| `fast` | 3 | Remove comments, editor metadata, trim whitespace |
| `balanced` | 10 | All fast passes + unused defs, duplicate merging, group collapsing, empty elements, transform normalization, path simplification, attribute ordering |
| `maximum` | 10 | Same 10 passes (maximum available) |

### Layout Engines

4 layout strategies for native-rendered diagrams (`pidraw/layout/`):

| Engine | Algorithm |
|---|---|
| `FlowLayout` | Topological sort, single-row/column |
| `GridLayout` | Square-ish grid (√N columns) |
| `LayeredLayout` | Sugiyama-style layered layout |
| `TreeLayout` | Recursive subtree positioning |

### Themes

5 built-in themes (`pidraw/themes/`):

| Theme | Description |
|---|---|
| `light` | White background, dark text, sans-serif |
| `dark` | Dark background (`#1e1e1e`), light text |
| `minimal` | Light minimal (`#fafafa`), thin strokes, Helvetica |
| `professional` | Colorful node palette, shadows, Segoe UI |
| `blueprint` | Blue-on-light-blue, monospace, engineering aesthetic |

---

## Caching

PiDraw includes a two-tier content-addressable cache:

- **Memory tier**: LRU-eviction dict (default 10,000 entries)
- **Disk tier**: JSON files in configurable directory
- Cache key: SHA-256 hash of `language + "\x00" + source`
- Configurable TTL per entry

Used automatically by `RenderPool` (parallel rendering) and `IncrementalRenderer`.

---

## Plugin System

Extend PiDraw with custom renderers via entry points:

```toml
# pyproject.toml
[project.entry-points."pidraw.renderers"]
myengine = "mypackage:MyRenderer"
```

Your class must extend `BaseRenderer` and implement `render(source: str) -> str`.

```python
from pidraw.engines.base import BaseRenderer

class MyRenderer(BaseRenderer):
    name = "myformat"
    def render(self, source: str) -> str:
        # ... return SVG string
        pass
```

---

## Recovery & Error Handling

| Mechanism | Description |
|---|---|
| `render_with_retry()` | Exponential backoff retry with optional fallback renderer |
| `safe_render()` | Returns a red-box error SVG instead of raising |
| `RecoverableRenderingError` | Distinguishable from hard failures |

---

## Large File Support

Files up to 10 MB are handled with streaming reads and chunked SVG writes. Language detection reads only the first 512 KB for efficiency.

---

## Parallel Rendering

`RenderPool` uses `ThreadPoolExecutor` (I/O-bound subprocess calls) or `ProcessPoolExecutor` (CPU-bound work) with auto-configured worker count.

```python
from pidraw import render_many
svgs = render_many([source1, source2, source3], language="mermaid")
```

---

## Requirements

- Python >= 3.10
- Optional: Node.js + npm (for CLI-based formats)
- Optional: Java Runtime (for structurizr-cli)

---

## License

MIT
