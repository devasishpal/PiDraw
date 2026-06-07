# Performance

## Overview

PiDraw is designed for performance at every layer of the rendering pipeline. Key features include:

- **Multi-pass SVG optimisation** with configurable levels
- **Parallel rendering** via process/thread pools
- **Two-tier caching** (memory + disk) with LRU eviction and TTL
- **Incremental builds** that skip unchanged files
- **Large file support** with streaming I/O
- **Automatic retry** with exponential backoff for transient errors

## SVG Optimisation

The SVG optimisation pipeline consists of ten passes, each a pure function. Passes are safe -- they never remove visible content or alter rendering.

### Passes

| # | Pass | Description |
|---|------|-------------|
| 1 | `remove_comments` | Strip all XML comments |
| 2 | `remove_editor_metadata` | Remove Inkscape/Sodipodi attributes, namespace declarations, and `<metadata>` blocks |
| 3 | `remove_unused_defs` | Remove `<defs>` children whose `id` is not referenced |
| 4 | `merge_duplicate_defs` | Merge identical definitions, rewriting references |
| 5 | `collapse_redundant_groups` | Remove `<g>` elements with no attributes and a single child |
| 6 | `remove_empty_elements` | Strip elements with no visual impact |
| 7 | `normalize_transforms` | Canonicalise `transform` attribute values (consistent spacing, lowercase, no trailing zeros) |
| 8 | `simplify_paths` | Normalise path `d` attribute numbers (trailing zeros removed) |
| 9 | `trim_whitespace` | Collapse whitespace runs (preserving `<text>`, `<tspan>`, `<style>` content) |
| 10 | `normalize_attribute_ordering` | Sort attributes: `id` first, then namespace declarations, then alphabetically |

### Optimisation Levels

| Level | Passes | Use Case |
|-------|--------|----------|
| `fast` | 1, 2, 9 | Quick cleanup with minimal CPU |
| `balanced` (default) | 1-10 | Full cleanup for everyday use |
| `maximum` | 1-10 + all available | Deepest compression for production |

```python
from pidraw.optimizer import optimize_by_level

# Fast pass
result = optimize_by_level(svg, level="fast")

# Balanced (default)
result = optimize_by_level(svg, level="balanced")

# Maximum compression
result = optimize_by_level(svg, level="maximum")

print(f"{result.original_size} -> {result.optimized_size} bytes "
      f"({result.reduction_percent:.1f}%)")
```

## Parallel Rendering

`RenderPool` provides parallel rendering using `ThreadPoolExecutor` (for I/O-bound subprocess calls) or `ProcessPoolExecutor` (for CPU-bound optimisation).

```python
from pidraw.pool import RenderPool

pool = RenderPool(max_workers=8)
results = pool.render_many(sources, language="mermaid")

for result in results:
    print(f"Task {result.task_id}: {len(result.svg)} bytes, "
          f"cached={result.cached}, error={result.error}")
```

The pool automatically selects worker count as `CPU count * 2` when `max_workers` is `None`. Results are returned in input order.

`BatchRenderSummary` aggregates results:

```python
from pidraw.pool import summarize

summary = summarize(results)
print(f"{summary.succeeded} succeeded, {summary.failed} failed, "
      f"{summary.cached} cached in {summary.total_elapsed_ms:.0f}ms")
```

## Caching

`CacheManager` provides two-tier caching with memory-first, disk-backed storage.

```python
from pidraw.cache import CacheManager

cache = CacheManager(
    cache_dir="./.pidraw-cache",   # disk tier directory (None to disable)
    ttl_seconds=3600,              # entries expire after 1 hour (0 = no expiry)
    max_memory_entries=10_000,     # LRU eviction (0 = unlimited)
)
```

### Features

- **Content-addressed keys** -- cache key is SHA-256 of source + language, so identical content never duplicates.
- **Memory tier** -- in-process dict with LRU eviction. Access order is tracked; oldest entries are evicted first when `max_memory_entries` is reached.
- **Disk tier** -- JSON files named by content hash; automatically promoted to memory on hit.
- **TTL expiry** -- entries past their TTL are skipped and cleaned up.
- **Statistics** -- `cache.stats()` returns hit/miss counts for both tiers.

```python
stats = cache.stats()
print(f"Memory: {stats.memory_hits} hits, {stats.memory_misses} misses")
print(f"Disk:   {stats.disk_hits} hits, {stats.disk_misses} misses")
```

## Incremental Builds

`IncrementalRenderer` tracks source content hashes across runs, skipping files that have not changed.

```python
from pidraw.incremental import IncrementalRenderer

incr = IncrementalRenderer(
    state_dir="./.pidraw-state",
    cache=cache,
)

if incr.needs_render("diagram.mmd"):
    svg = render(source, language="mermaid")
    incr.record_render("diagram.mmd", source, svg)
else:
    incr.skip_file("diagram.mmd")
```

State is persisted to `incremental_state.json` inside `state_dir` and survives restarts. Call `incr.stats()` to get `IncrementalStats` (files checked, rendered, skipped, failed, elapsed).

## Large File Support

Files over 10 MiB automatically use streaming I/O to avoid loading the entire source into memory.

- **Language detection** reads only the first 512 KB of the file.
- **Rendering** writes large sources to a temp file for zero-copy subprocess consumption.
- **SVG output** is written to disk in configurable chunks (default 8 MiB).

```python
from pidraw.large import render_large_file, stream_svg_write

svg = render_large_file("huge_diagram.mmd", language="mermaid")
stream_svg_write(svg, "output.svg")
```

## Recovery Mechanisms

`render_with_retry` handles transient render failures with exponential backoff and optional fallback:

```python
from pidraw.recovery import render_with_retry

svg = render_with_retry(
    source,
    language="mermaid",
    render_func=render,
    max_retries=2,
    retry_delay=0.5,
    backoff=2.0,
)
```

On first failure it waits 0.5s, then 1.0s, then 2.0s. If all retries fail and a `fallback_renderer` is provided, it attempts the fallback before raising `RecoverableRenderingError`.

`safe_render` returns a fallback SVG on failure instead of raising:

```python
from pidraw.recovery import safe_render

svg = safe_render(source, language="mermaid", fallback_svg=error_svg)
```

When no fallback is provided, a minimal error SVG is generated automatically.

## Benchmarks

Run the full benchmark suite to measure performance on your system:

```bash
pidraw benchmark
```

For a quick result with fewer iterations:

```bash
pidraw benchmark --quick
```

Benchmarks cover four scenarios:

| Scenario | What it measures |
|----------|------------------|
| Render Speed | Raw throughput across Mermaid, Graphviz, and PlantUML samples |
| Optimisation | Pipeline speed and byte savings |
| Cache Efficiency | Hit rate and speedup with warm cache |
| Large Diagram | Memory delta and render time for a 500-node Mermaid diagram |

```python
from pidraw.benchmark import run_benchmarks, format_report

report = run_benchmarks(quick=True)
print(format_report(report))
```

Programmatic access to individual benchmarks:

```python
from pidraw.benchmark import (
    benchmark_render_speed,
    benchmark_optimization,
    benchmark_cache_efficiency,
    benchmark_large_diagram,
)

speed = benchmark_render_speed(render_func, iterations=5)
print(f"Average render time: {speed.render_time_ms} ms")
```
