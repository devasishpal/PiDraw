"""High-performance parallel rendering pool."""

from __future__ import annotations

import os
import time
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Iterable

from pidraw.cache import CacheManager
from pidraw.exceptions import PiDrawError


@dataclass
class RenderTask:
    """A single render task submitted to a pool."""

    source: str
    language: str | None = None
    file_path: str | None = None
    task_id: int = 0


@dataclass
class RenderResult:
    """Result of a single render task."""

    svg: str
    task_id: int = 0
    elapsed_ms: float = 0.0
    language: str | None = None
    file_path: str | None = None
    cached: bool = False
    error: str | None = None


@dataclass
class BatchRenderSummary:
    """Aggregate results of a batch render operation."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    cached: int = 0
    total_elapsed_ms: float = 0.0
    results: list[RenderResult] = field(default_factory=list)


class RenderPool:
    """Parallel rendering pool with automatic worker selection.

    Uses ``ThreadPoolExecutor`` for I/O-bound work (subprocess calls)
    and ``ProcessPoolExecutor`` for CPU-bound optimisation.

    Parameters
    ----------
    max_workers : int or None
        Maximum number of worker threads.  ``None`` = CPU count * 2.
    use_processes : bool
        If ``True``, use ``ProcessPoolExecutor`` (for CPU-heavy loads).
    cache : CacheManager or None
        Optional render cache.

    """

    def __init__(
        self,
        max_workers: int | None = None,
        use_processes: bool = False,
        cache: CacheManager | None = None,
    ) -> None:
        self._max_workers = max_workers or (os.cpu_count() or 1) * 2
        self._use_processes = use_processes
        self._cache = cache

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def render_many(
        self,
        sources: Iterable[str],
        language: str | None = None,
        *,
        optimize: bool = False,
        show_progress: bool = False,
        task_id_offset: int = 0,
        file_paths: Iterable[str | None] | None = None,
    ) -> list[RenderResult]:
        """Render multiple diagram sources in parallel.

        Parameters
        ----------
        sources :
            Iterable of diagram source strings.
        language :
            Explicit language override for all sources.
        optimize :
            If ``True``, optimise each rendered SVG.
        show_progress :
            If ``True``, print progress to stderr.
        task_id_offset :
            Starting task ID.
        file_paths :
            Optional file paths corresponding to each source.

        Returns
        -------
        list[RenderResult]
            One result per input, in input order.

        """
        source_list = list(sources)
        fp_list: list[str | None] = (
            list(file_paths)
            if file_paths is not None
            else [None] * len(source_list)
        )

        n = len(source_list)
        results: list[RenderResult | None] = [None] * n

        # Check cache first
        if self._cache is not None:
            for i, src in enumerate(source_list):
                cached_svg = self._cache.get(src, language=language)
                if cached_svg is not None:
                    results[i] = RenderResult(
                        svg=cached_svg,
                        task_id=i + task_id_offset,
                        language=language,
                        file_path=fp_list[i],
                        cached=True,
                    )

        # Build task list for uncached items
        tasks: list[int] = [
            i for i, r in enumerate(results) if r is None
        ]

        if not tasks:
            return self._finalize_results(
                results, source_list, language, task_id_offset, fp_list
            )

        executor_cls = ProcessPoolExecutor if self._use_processes else ThreadPoolExecutor

        with executor_cls(max_workers=self._max_workers) as executor:
            future_map: dict[Future[RenderResult], int] = {}
            for idx in tasks:
                future = executor.submit(
                    _render_wrapper,
                    source_list[idx],
                    language=language,
                    file_path=fp_list[idx],
                    task_id=idx + task_id_offset,
                )
                future_map[future] = idx

            done = 0
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    result = future.result()
                    results[idx] = result
                    if self._cache is not None and result.error is None:
                        self._cache.set(
                            source_list[idx], result.svg, language=language
                        )
                except Exception as exc:
                    results[idx] = RenderResult(
                        svg="",
                        task_id=idx + task_id_offset,
                        error=str(exc),
                        language=language,
                        file_path=fp_list[idx],
                    )
                done += 1
                if show_progress:
                    self._print_progress(done, len(tasks))

        return self._finalize_results(
            results, source_list, language, task_id_offset, fp_list
        )

    def _finalize_results(
        self,
        results: list[RenderResult | None],
        sources: list[str],
        language: str | None,
        offset: int,
        file_paths: list[str | None],
    ) -> list[RenderResult]:
        finalized: list[RenderResult] = []
        for i, r in enumerate(results):
            if r is None:
                finalized.append(
                    RenderResult(
                        svg="",
                        task_id=i + offset,
                        error="No result produced",
                        language=language,
                        file_path=file_paths[i],
                    )
                )
            else:
                finalized.append(r)
        return finalized

    @staticmethod
    def _print_progress(done: int, total: int) -> None:
        import sys
        pct = done / total * 100 if total else 100
        sys.stderr.write(f"\r  [{done}/{total}] {pct:.0f}%")
        if done == total:
            sys.stderr.write("\n")


def _render_wrapper(
    source: str,
    language: str | None = None,
    file_path: str | None = None,
    task_id: int = 0,
) -> RenderResult:
    """Standalone wrapper for parallel execution."""
    from pidraw.renderer import render as _render_single
    start = time.perf_counter()
    try:
        svg = _render_single(source, language=language)
        elapsed = (time.perf_counter() - start) * 1000
        return RenderResult(
            svg=svg,
            task_id=task_id,
            elapsed_ms=elapsed,
            language=language,
            file_path=file_path,
        )
    except PiDrawError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return RenderResult(
            svg="",
            task_id=task_id,
            elapsed_ms=elapsed,
            error=str(exc),
            language=language,
            file_path=file_path,
        )


def summarize(results: list[RenderResult]) -> BatchRenderSummary:
    """Aggregate a list of render results into a summary."""
    summary = BatchRenderSummary(total=len(results))
    total_elapsed = 0.0
    for r in results:
        total_elapsed += r.elapsed_ms
        if r.error:
            summary.failed += 1
        else:
            summary.succeeded += 1
            if r.cached:
                summary.cached += 1
    summary.total_elapsed_ms = total_elapsed
    summary.results = results
    return summary
