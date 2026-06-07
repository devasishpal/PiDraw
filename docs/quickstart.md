# Quick Start

Render your first diagram in seconds using the Python API or the command line.

---

## Python API

### Basic rendering

Render a diagram source string to SVG. Language is auto-detected when omitted.

```python
from pidraw import render

svg = render("graph TD; A-->B;", "mermaid")
```

### Render from a file

Read any supported diagram file and render it to SVG. The language is detected from the file extension and source content automatically.

```python
from pidraw import render_file

svg = render_file("input.mmd")
```

### Batch rendering

Render multiple source files in parallel using a thread pool. Results are returned in input order.

```python
from pidraw import render_many

results = render_many(["file1.mmd", "file2.dot"])
for svg in results:
    print(f"Rendered {len(svg)} chars")
```

### Native rendering

Bypass the plugin registry and use PiDraw's built-in native renderer directly. Supports themes, layout control, and optional SVG optimisation.

```python
from pidraw import render_native

svg = render_native("graph TD; A-->B;", "mermaid", theme="dark", layout=True, optimize=True)
```

### Language detection

Detect the diagram language from source code with confidence scoring.

```python
from pidraw import detect

result = detect("source code")
print(f"Detected: {result}")
```

### SVG optimization

Run the multi-pass SVG optimisation pipeline on any SVG string. Supports fast, balanced, and maximum levels.

```python
from pidraw import optimize_svg

result = optimize_svg(svg_string)
print(f"Reduced from {result.original_size} to {result.optimized_size} bytes")
```

---

## CLI

### Render a file

```bash
pidraw render input.mmd
```

Write to a specific output path with `-o`:

```bash
pidraw render input.mmd -o output.svg
```

### Detect language

```bash
pidraw detect input.mmd
```

Prints the detected language, confidence score, and registered renderer.

### Batch render

Render all diagram files matching a glob pattern into an output directory:

```bash
pidraw batch *.mmd --output-dir ./output
```

Supports recursive scanning (`-r`), explicit language override (`-l`), and parallel workers (`-w`).

---

## Supported Languages

PiDraw supports five languages natively (built-in renderer) and many more via CLI-based external tools:

| Language    | Syntax example                     | Renderer          |
|-------------|------------------------------------|--------------------|
| Mermaid     | `graph TD; A-->B;`                 | Native + mmdc      |
| Graphviz    | `digraph G { a -> b }`            | Native + dot       |
| PlantUML    | `@startuml a->b @enduml`          | Native + plantuml  |
| D2          | `x -> y`                           | Native + d2        |
| ASCII       | `+--+` box-and-line diagrams       | Native             |

For external languages (BPMN, Structurizr, Vega, TikZ, and more), PiDraw dispatches to the corresponding CLI tool automatically when installed.
