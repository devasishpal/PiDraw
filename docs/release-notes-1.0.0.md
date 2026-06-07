# PiDraw 1.0.0 Release Notes

**Release date:** 2026-06-07

We are pleased to announce the first stable release of PiDraw, a universal diagram rendering engine for Python. After extensive development and testing, version 1.0.0 delivers a production-ready tool for converting textual diagram descriptions into high-quality SVG output across a wide range of diagram languages.

## What Is PiDraw?

PiDraw is a Python library and CLI tool that provides a unified interface for rendering diagrams written in popular textual formats. It features automatic language detection, an extensible plugin system, SVG optimization, caching, incremental builds, watch mode, and comprehensive diagnostics. PiDraw is designed for documentation pipelines, automated CI workflows, and developer tooling.

## Key Features

- **Universal diagram rendering** with support for 15+ languages including Mermaid, PlantUML, Graphviz (DOT), BlockDiag, D2, ASCII art, and more
- **Automatic language detection** with confidence scoring to identify diagram languages from raw input
- **Multi-pass SVG optimization pipeline** with three levels (basic, balanced, aggressive) for size and structure improvements
- **Plugin system** with decorator-based registration and setuptools entry point discovery
- **Batch and parallel rendering** with configurable worker pools for high-throughput processing
- **Render caching** with in-memory and disk-based stores, TTL expiration, and LRU eviction
- **Incremental builds** that detect file changes via content hashing and re-render only what changed
- **Watch mode** for live file monitoring and automatic re-rendering
- **Native rendering engine** with a configurable pipeline of converters, layout engines, theme applicators, and SVG exporters
- **CLI with 10 commands** covering rendering, batch processing, watch, cache management, diagnostics, analysis, benchmarking, initialization, configuration, and plugins
- **Recovery mechanisms** including automatic retry with configurable exponential backoff policies
- **Large file streaming** support for efficient processing of diagrams exceeding available memory
- **Comprehensive diagnostics and analysis** tools for cache performance, render timing, and diagram complexity
- **Benchmarking suite** for measuring throughput, latency, and optimization effectiveness

## Installation

```bash
pip install pidraw
```

To install with optional rendering engine dependencies:

```bash
pip install pidraw[mermaid,plantuml,graphviz]
```

## Links

- Homepage: https://pidraw.dev
- Documentation: https://pidraw.dev/docs
- Repository: https://github.com/example/pidraw
- Issue tracker: https://github.com/example/pidraw/issues
- PyPI: https://pypi.org/project/pidraw/
