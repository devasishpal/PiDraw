# PiDraw Documentation

## Introduction

PiDraw is a universal diagram rendering platform for Python. It provides a unified interface for generating diagrams using multiple rendering backends -- Mermaid, Graphviz, PlantUML, D2, and more -- without locking you into any single tool. Write your diagram once, render with any engine.

## Quick Navigation

- [Installation](installation.md) -- Install PiDraw and configure renderers
- [Usage Guide](usage.md) -- Getting started with diagrams
- [API Reference](api.md) -- Full API documentation
- [Renderers](renderers.md) -- Supported rendering backends
- [Contributing](contributing.md) -- How to contribute

## Supported Languages

PiDraw supports diagrams defined in:

- **Mermaid** -- Flowcharts, sequence diagrams, Gantt charts, and more
- **Graphviz (DOT)** -- Directed and undirected graphs, hierarchies
- **PlantUML** -- UML diagrams, activity diagrams, component diagrams
- **D2** -- Modern declarative diagramming language
- **Custom renderers** -- Pluggable architecture for additional backends

## Project Philosophy

PiDraw is built on three principles:

1. **Unified interface** -- One API to generate diagrams across all major rendering engines, so you can switch backends without rewriting code.
2. **Render anywhere** -- Abstract away CLI tool discovery, subprocess management, and output format handling so your diagrams work in notebooks, web apps, and CI pipelines.
3. **Pluggable by design** -- Every renderer is an independent plugin. The core library orchestrates, the renderers execute. Add new backends as the ecosystem evolves.
