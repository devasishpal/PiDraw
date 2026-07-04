# PiDraw — Agent Guidelines

## Overview
PiDraw is a universal diagram rendering platform that converts diagram source code (Mermaid, PlantUML, Graphviz, D2, etc.) into optimized SVG/PNG.

## Project Structure
```
pidraw/
├── backend/           # SVG/PNG output backends
├── cli/               # Typer CLI interface
├── core/              # Data models (Node, Edge, Diagram) + converters (parsers)
├── engines/           # Renderer engines (CLI wrappers + NativeRenderer)
├── equations/         # LaTeX equation rendering
├── layout/            # Layout engines (flow, grid, layered, tree)
├── optimizer/         # SVG optimization passes
├── quality/           # SVG quality enhancement
├── themes/            # Visual themes (light, dark, etc.)
└── renderer.py        # Public render() API
tests/                 # ~536 pytest tests
```

## Key Models (pidraw/core/models.py)
- **Position** {x, y} — top-left corner of a node
- **Size** {width, height}
- **Node** {id, label, shape, style, position, size, children}
- **Edge** {id, source, target, label, style, waypoints}
- **Diagram** {nodes, edges, groups, layout, viewport, style}
- **Layout** {layout_type, direction, node_spacing, layer_spacing, padding}
- **Viewport** {x, y, width, height, scale}

## Layout Engines (pidraw/layout/)
| Engine | LayoutType | Default Direction | Behavior |
|--------|-----------|-------------------|----------|
| FlowLayout | FLOW | TB | Topological sort, linear arrangement |
| GridLayout | GRID | — | sqrt-based grid, column-aligned widths |
| LayeredLayout | LAYERED | TB | Layer assignment, accumulated offsets |
| TreeLayout | TREE | — | Recursive subtree layout, centered parent |

## Critical Fixes Applied (v1.3.3)

### 1. LayeredLayout — Inter-layer overlap
**Bug**: Each layer used its own `max_dim` to compute X (TB) or Y (LR) position, but the offset was `layer_idx * (max_dim + gap) + padding`. This meant layer N+1 could start **before** layer N ended if layer N's max width was larger than layer N+1's.

**Fix**: Pre-compute `max_dim` for ALL layers first, then accumulate offsets:
- For TB: `x = padding + accumulated_width_of_all_prev_layers`
- Within a layer, all nodes share the same X (TB) or Y (LR) coordinate
- No incremental `max_dim` changes affect already-positioned nodes

### 2. GridLayout — Column misalignment
**Bug**: Each cell used its own node's width for X spacing. Different rows could have different X positions for the same column.

**Fix**: Pre-compute max width per column across all rows, then align all rows to those column widths.

### 3. Edge rendering — Center-to-boundary intersection
**Bug**: Edges drew from source-center to target-center, causing arrowheads to be hidden inside target nodes.

**Fix**: Added `_rect_boundary_point()` that computes where a line from center hits the rectangle edge. Edges now terminate at node boundaries.

### 4. Text overflow — Clip path per node
**Fix**: Each node now has an SVG `<clipPath>` that clips its label text to the node's bounding box, preventing text from overlapping neighboring elements.

## Conventions
- **Python 3.10+** target, uses `from __future__ import annotations`
- **No comments** in code (unless absolutely required by the framework/tooling)
- **pytest** for testing: `py -m pytest tests/ -v --tb=short`
- **ruff** for linting: `py -m ruff check pidraw/ tests/`
- **Version** tracked in `pyproject.toml` under `[project].version`
- Always use `py` launcher instead of `python` on Windows

## Testing
```powershell
py -m pytest tests/ -v --tb=short        # all tests
py -m pytest tests/test_layout.py -v     # layout tests only
```

## Common Tasks
- **Add new converter**: Create class in `core/converters/`, decorate with `@register_converter`
- **Add new engine**: Create class in `engines/`, subclass `BaseRenderer`
- **Add new theme**: Create class in `themes/`, decorate with `@register_theme`
- **Add new layout**: Create class in `layout/`, decorate with `@register_layout`
