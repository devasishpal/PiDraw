# PiDraw

Universal diagram rendering platform — converts any diagram language to SVG.

**Supported formats:** mermaid, plantuml, graphviz, d2, ascii, bpmn, markmap, nomnoml, wavedrom, structurizr, vega, vega-lite, excalidraw, kroki.

## Quick Start

```bash
pip install pidraw
pidraw render input.mmd output.svg
pidraw formats        # list supported formats
```

## Features

- **14+ diagram languages** — one tool for all your diagrams
- **Native rendering** for 7 formats (no CLI tools needed): mermaid, plantuml, graphviz, d2, ascii, excalidraw, kroki
- **Auto-install** — CLI tools are installed on first use
- **SVG optimization** — built-in optimizer with multiple levels
- **Quality enhancement** — improves diagram appearance
- **Batch processing** — render multiple files at once
- **Watch mode** — auto-render on file changes
- **Plugin system** — extend with custom renderers

## Auto-Install

`pip install pidraw` installs everything needed. On first import, missing CLI tools (npm packages, Java structurizr-cli, Playwright Chromium) are automatically installed in the background.

## Usage

```bash
# Single file
pidraw render diagram.mmd output.svg

# Multiple files
pidraw batch *.mmd *.puml --output-dir ./svg

# Watch for changes
pidraw watch *.mmd --output-dir ./svg

# Detect language
pidraw detect diagram.txt

# List supported formats with live status
pidraw formats
```

## License

MIT
