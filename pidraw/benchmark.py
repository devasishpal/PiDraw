"""Benchmark suite for measuring PiDraw performance."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Callable

from pidraw.cache import CacheManager
from pidraw.optimizer import optimize_svg
from pidraw.pool import RenderPool


@dataclass
class BenchmarkResult:
    """Results from a single benchmark scenario."""

    name: str
    render_time_ms: float = 0.0
    optimize_time_ms: float = 0.0
    throughput_per_sec: float = 0.0
    memory_mb: float = 0.0
    cache_hit_rate: float = 0.0
    output_size_bytes: int = 0
    notes: str = ""


@dataclass
class BenchmarkReport:
    """Full benchmark report."""

    results: list[BenchmarkResult] = field(default_factory=list)
    total_elapsed_ms: float = 0.0
    system_info: str = ""


# ---------------------------------------------------------------------------
# Sample diagrams for benchmarking
# ---------------------------------------------------------------------------

_SAMPLE_MERMAID = """graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Process 1]
    B -->|No| D[Process 2]
    C --> E[End]
    D --> E
"""

_SAMPLE_LARGE_MERMAID = "graph TD\n" + "\n".join(
    f"    N{i}[Node {i}] --> N{i + 1}" for i in range(100)
)

_SAMPLE_GRAPHVIZ = """digraph G {
    rankdir=LR;
    a -> b -> c -> d -> e;
    a -> f -> g;
    b -> h;
    c -> i;
}
"""

_SAMPLE_PLANTUML = """@startuml
A -> B : message 1
B -> C : message 2
C -> D : message 3
@enduml
"""


def _mb_usage() -> float:
    """Return current RSS memory usage in MB (best-effort)."""
    try:
        import psutil  # type: ignore[import-untyped]

        return float(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024))
    except ImportError:
        return 0.0


# ---------------------------------------------------------------------------
# Benchmark scenarios
# ---------------------------------------------------------------------------


def benchmark_render_speed(
    render_func: Callable[..., str | bytes],
    iterations: int = 10,
) -> BenchmarkResult:
    """Measure raw render throughput."""
    samples = [_SAMPLE_MERMAID, _SAMPLE_GRAPHVIZ, _SAMPLE_PLANTUML]
    times: list[float] = []

    for _ in range(iterations):
        for src in samples:
            start = time.perf_counter()
            render_func(src)
            times.append((time.perf_counter() - start) * 1000)

    avg = sum(times) / len(times)
    throughput = len(samples) * iterations / (sum(times) / 1000)

    return BenchmarkResult(
        name="Render Speed",
        render_time_ms=round(avg, 2),
        throughput_per_sec=round(throughput, 1),
    )


def benchmark_optimization(
    render_func: Callable[..., str | bytes],
    iterations: int = 5,
) -> BenchmarkResult:
    """Measure optimisation pipeline speed."""
    svgs: list[str | bytes] = []
    for src in [_SAMPLE_MERMAID, _SAMPLE_LARGE_MERMAID, _SAMPLE_GRAPHVIZ]:
        try:
            svgs.append(render_func(src))
        except Exception:
            pass

    if not svgs:
        return BenchmarkResult(
            name="Optimization",
            notes="No SVGs could be rendered",
        )

    svg_strings = [s for s in svgs if isinstance(s, str)]
    if not svg_strings:
        return BenchmarkResult(
            name="Optimization",
            notes="No SVG strings could be rendered",
        )

    times: list[float] = []
    sizes_before: list[int] = []
    sizes_after: list[int] = []

    for _ in range(iterations):
        for svg in svg_strings:
            start = time.perf_counter()
            result = optimize_svg(svg)
            times.append((time.perf_counter() - start) * 1000)
            sizes_before.append(result.original_size)
            sizes_after.append(result.optimized_size)

    avg = sum(times) / len(times) if times else 0.0
    avg_saved = (sum(sizes_before) - sum(sizes_after)) / len(sizes_before) if sizes_before else 0

    return BenchmarkResult(
        name="Optimization",
        optimize_time_ms=round(avg, 2),
        output_size_bytes=int(avg_saved),
        notes=f"Avg {avg_saved:.0f} bytes saved per SVG" if avg_saved else "",
    )


def benchmark_cache_efficiency(
    render_func: Callable[..., str | bytes],
    iterations: int = 3,
) -> BenchmarkResult:
    """Measure cache hit rate and speedup."""
    cache = CacheManager(max_memory_entries=1000)
    pool = RenderPool(max_workers=1, cache=cache)

    # Warm-up: render once
    sources = [_SAMPLE_MERMAID, _SAMPLE_GRAPHVIZ, _SAMPLE_PLANTUML]
    pool.render_many(sources, show_progress=False)

    # Measure cache hits
    start = time.perf_counter()
    for _ in range(iterations):
        pool.render_many(sources, show_progress=False)
    elapsed = (time.perf_counter() - start) * 1000

    stats = cache.stats()
    total_accesses = stats.memory_hits + stats.memory_misses
    hit_rate = stats.memory_hits / total_accesses if total_accesses else 0.0

    return BenchmarkResult(
        name="Cache Efficiency",
        render_time_ms=round(elapsed / (iterations * len(sources)), 2),
        cache_hit_rate=round(hit_rate, 3),
        notes=f"Memory: {stats.entries} entries, {stats.memory_hits} hits",
    )


def benchmark_large_diagram(
    render_func: Callable[..., str | bytes],
) -> BenchmarkResult:
    """Render a large diagram to stress-test throughput."""
    # Generate a 500-node Mermaid diagram
    large = "graph TD\n" + "\n".join(f"    N{i}[Node {i}] --> N{i + 1}" for i in range(500))

    mem_before = _mb_usage()
    start = time.perf_counter()

    try:
        svg = render_func(large)
        elapsed = (time.perf_counter() - start) * 1000
        mem_after = _mb_usage()
    except Exception as exc:
        return BenchmarkResult(
            name="Large Diagram (500 nodes)",
            notes=f"Failed: {exc}",
        )

    return BenchmarkResult(
        name="Large Diagram (500 nodes)",
        render_time_ms=round(elapsed, 2),
        memory_mb=round(mem_after - mem_before, 1),
        output_size_bytes=len(svg.encode("utf-8") if isinstance(svg, str) else svg),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_benchmarks(
    render_func: Callable[..., str | bytes] | None = None,
    *,
    quick: bool = False,
) -> BenchmarkReport:
    """Run the full benchmark suite and return a report.

    Parameters
    ----------
    render_func :
        Render function to test (defaults to ``pidraw.renderer.render``).
    quick :
        If ``True``, run fewer iterations.

    """
    if render_func is None:
        from pidraw.renderer import render as _default_render

        render_func = _default_render

    report = BenchmarkReport()
    start_total = time.perf_counter()

    iters = 3 if quick else 10

    report.results.append(benchmark_render_speed(render_func, iterations=iters))
    report.results.append(benchmark_optimization(render_func, iterations=iters))
    report.results.append(benchmark_cache_efficiency(render_func, iterations=iters))
    report.results.append(benchmark_large_diagram(render_func))

    report.total_elapsed_ms = round((time.perf_counter() - start_total) * 1000, 1)
    report.system_info = f"Python {sys.version.split()[0]}, pid={os.getpid()}"

    return report


def format_report(report: BenchmarkReport) -> str:
    """Format a benchmark report as a human-readable string."""
    lines: list[str] = [
        "=" * 60,
        "PiDraw Benchmark Report",
        "=" * 60,
        f"  System:      {report.system_info}",
        f"  Total time:  {report.total_elapsed_ms:.1f} ms",
        "",
    ]

    for r in report.results:
        lines.append(f"  [{r.name}]")
        if r.render_time_ms:
            lines.append(f"    Render time:      {r.render_time_ms:.2f} ms")
        if r.optimize_time_ms:
            lines.append(f"    Optimize time:    {r.optimize_time_ms:.2f} ms")
        if r.throughput_per_sec:
            lines.append(f"    Throughput:       {r.throughput_per_sec:.1f} diag/s")
        if r.memory_mb:
            lines.append(f"    Memory delta:     {r.memory_mb:.1f} MB")
        if r.cache_hit_rate:
            lines.append(f"    Cache hit rate:   {r.cache_hit_rate:.1%}")
        if r.output_size_bytes:
            lines.append(f"    Output size:      {r.output_size_bytes} bytes")
        if r.notes:
            lines.append(f"    Notes:            {r.notes}")
        lines.append("")

    lines.append("-" * 60)
    return "\n".join(lines)
