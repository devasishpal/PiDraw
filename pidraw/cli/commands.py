"""Command implementations for the PiDraw CLI."""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

# Trigger auto-registration of built-in renderer engines
import pidraw.engines  # noqa: F401
from pidraw import __version__
from pidraw.cli.logging import get_logger
from pidraw.cli.setup import setup_all
from pidraw.detector import detect_language
from pidraw.diagnostics import analyze
from pidraw.exceptions import PiDrawError
from pidraw.formats import format_table, status_table
from pidraw.optimizer import optimize_svg
from pidraw.registry import discover_plugins, get_renderer, list_renderers

logger = get_logger()

# ---------------------------------------------------------------------------
# Recognised diagram file extensions
# ---------------------------------------------------------------------------

DIAGRAM_EXTENSIONS: set[str] = {
    ".mmd",
    ".mermaid",
    ".puml",
    ".plantuml",
    ".iuml",
    ".dot",
    ".gv",
    ".d2",
    ".bpmn",
    ".mm",
    ".noml",
    ".dsl",
    ".tex",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".md",
}


def _is_diagram_file(path: Path) -> bool:
    return path.suffix.lower() in DIAGRAM_EXTENSIONS and path.is_file()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _read_source(file: str | Path) -> str:
    path = Path(file)
    if not path.is_file():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)
    text = path.read_text(encoding="utf-8-sig")
    return text.lstrip("\ufeff")


def _write_output(output_path: str | Path, data: str | bytes) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class BatchResult:
    """Result of processing a single file in batch mode."""

    file: str
    status: str  # "ok", "skipped", "failed"
    message: str = ""
    elapsed_ms: float = 0.0
    language: str = ""
    original_size: int = 0
    optimized_size: int = 0


@dataclass
class BatchSummary:
    """Summary statistics for a batch operation."""

    total: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    elapsed_ms: float = 0.0
    results: list[BatchResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def render_cmd(
    file: str,
    output: Optional[str] = None,
    language: Optional[str] = None,
    format: str = "svg",
    optimize: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    debug: bool = False,
) -> None:
    """Render a diagram file to SVG or PNG."""
    from pidraw.renderer import render

    fmt = format.lower()
    if fmt not in ("svg", "png"):
        logger.error("Unsupported format: %s (use 'svg' or 'png')", format)
        raise SystemExit(1)

    source = _read_source(file)
    start = time.perf_counter()

    try:
        result = render(source, language=language, format=fmt)
    except PiDrawError as exc:
        logger.error("Render failed: %s", exc)
        raise SystemExit(1) from exc

    elapsed = (time.perf_counter() - start) * 1000

    if fmt == "svg" and optimize and isinstance(result, str):
        try:
            opt = optimize_svg(result)
            result = opt.svg
            if verbose or debug:
                logger.info(
                    "Optimised: %d \u2192 %d bytes (%.1f%%)",
                    opt.original_size,
                    opt.optimized_size,
                    opt.reduction_percent,
                )
        except Exception as exc:
            logger.warning("Optimisation skipped: %s", exc)

    if output:
        _write_output(output, result)
        logger.info("Wrote %s", output)
    elif fmt == "png":
        out_path = Path(file).with_suffix(".png")
        _write_output(str(out_path), result)
        logger.info("Wrote %s", out_path)
    else:
        sys.stdout.write(result)  # type: ignore[arg-type]
        sys.stdout.write("\n")

    if verbose or debug:
        logger.info("Rendered %s in %.0f ms", file, elapsed)


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------


def detect_cmd(
    file: str,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Detect the diagram language used in a file."""
    source = _read_source(file)
    result = detect_language(source)

    lang = result.language.value
    conf = result.confidence * 100

    renderer_name = "none"
    try:
        r = get_renderer(lang)
        renderer_name = type(r).__name__
    except Exception:
        pass

    output = f"Language:   {lang}\nConfidence: {conf:.0f}%\nRenderer:   {renderer_name}"
    if verbose or debug:
        pattern = result.matched_pattern or "(none)"
        output += f"\nPattern:    {pattern}"

    sys.stdout.write(output)
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


def analyze_cmd(
    file: str,
    render: bool = True,
    optimize: bool = True,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Analyse a diagram file with full diagnostics."""
    source = _read_source(file)
    result = analyze(source, render=render, optimize=optimize)

    lines: list[str] = [
        f"Language:     {result.detected_language}",
        f"Confidence:   {result.confidence * 100:.0f}%",
        f"Renderer:     {result.renderer_chosen or '(none)'}",
    ]

    if result.warnings:
        lines.append("Warnings:")
        for w in result.warnings:
            lines.append(f"  - {w}")

    if result.svg:
        lines.append(f"SVG length:   {len(result.svg)} chars")

    if result.original_size and result.optimized_size:
        lines.append(f"Original:     {result.original_size} bytes")
        lines.append(f"Optimized:    {result.optimized_size} bytes")
        lines.append(f"Reduction:    {result.reduction_percent:.1f}%")
        lines.append(f"Bytes saved:  {result.bytes_saved}")

    sys.stdout.write("\n".join(lines))
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# optimize
# ---------------------------------------------------------------------------


def optimize_cmd(
    file: str,
    output: Optional[str] = None,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Optimise an SVG file."""
    source_svg = _read_source(file)

    try:
        result_obj = optimize_svg(source_svg)
    except Exception as exc:
        logger.error("Optimisation failed: %s", exc)
        raise SystemExit(1) from exc

    if output:
        _write_output(output, result_obj.svg)
        logger.info(
            "Optimised %s (%d → %d bytes, %.1f%%)",
            output,
            result_obj.original_size,
            result_obj.optimized_size,
            result_obj.reduction_percent,
        )
    else:
        sys.stdout.write(result_obj.svg)
        sys.stdout.write("\n")

    if verbose or debug:
        passes = ", ".join(result_obj.passes_applied)
        logger.info("Passes applied: %s", passes)
        logger.info(
            "Size: %d → %d bytes (%.1f%%) in %.0f ms",
            result_obj.original_size,
            result_obj.optimized_size,
            result_obj.reduction_percent,
            result_obj.elapsed_ms,
        )


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------


def _process_single(args: tuple[str, str | None, bool, str | None]) -> BatchResult:
    file, output_dir_str, do_optimize, lang_override = args
    output_dir = Path(output_dir_str) if output_dir_str else None
    start = time.perf_counter()
    basename = os.path.splitext(os.path.basename(file))[0]
    orig_size = 0
    opt_size = 0
    detected_lang = ""

    try:
        from pidraw.renderer import render

        source = _read_source(file)

        detected = detect_language(source)
        detected_lang = detected.language.value
        use_lang = lang_override or detected_lang

        if use_lang == "unknown":
            return BatchResult(
                file=file,
                status="skipped",
                message="Unknown diagram language",
            )

        result = render(source, language=use_lang)
        orig_size = len(result.encode("utf-8") if isinstance(result, str) else result)

        if do_optimize and isinstance(result, str):
            opt = optimize_svg(result)
            result = opt.svg
            orig_size = opt.original_size
            opt_size = opt.optimized_size

        if output_dir:
            out_path = output_dir / f"{basename}.svg"
            _write_output(out_path, result)

        elapsed = (time.perf_counter() - start) * 1000
        return BatchResult(
            file=file,
            status="ok",
            elapsed_ms=elapsed,
            language=detected_lang,
            original_size=orig_size,
            optimized_size=opt_size or orig_size,
        )
    except PiDrawError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return BatchResult(
            file=file,
            status="failed",
            message=str(exc),
            elapsed_ms=elapsed,
            language=detected_lang,
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return BatchResult(
            file=file,
            status="failed",
            message=str(exc),
            elapsed_ms=elapsed,
            language=detected_lang,
        )


def _print_progress(result: BatchResult, show_all: bool) -> None:
    if result.status == "ok":
        marker = "OK"
        lang_part = f" [{result.language}]" if result.language else ""
        size_part = (
            f" ({result.original_size}b)"
            if result.optimized_size == result.original_size
            else f" ({result.original_size}→{result.optimized_size}b)"
        )
        if show_all:
            logger.info("  %s%s%s  (%.0f ms)", marker, lang_part, size_part, result.elapsed_ms)
    elif result.status == "skipped":
        logger.info("  SKIP  %s", result.message)
    else:
        logger.info("  FAIL  %s", result.message)


def _scan_files(paths: Sequence[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_file() and _is_diagram_file(path):
            files.append(path)
        elif path.is_dir():
            method = path.rglob if recursive else path.glob
            for f in method("*"):
                if _is_diagram_file(f):
                    files.append(f)
    return sorted(set(files))


def batch_cmd(
    paths: List[str],
    output_dir: Optional[str] = None,
    language: Optional[str] = None,
    optimize: bool = False,
    recursive: bool = False,
    workers: Optional[int] = None,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Render multiple diagram files to SVG."""
    start_total = time.perf_counter()
    files = _scan_files(paths, recursive=recursive)

    if not files:
        logger.warning("No diagram files found in %s", paths)
        raise SystemExit(0)

    use_for = "recursive " if recursive else ""
    logger.info("Found %d %sdiagram file(s)", len(files), use_for)

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    n_workers = workers or os.cpu_count() or 4
    args_list = [
        (str(f), output_dir, optimize, language) for f in files
    ]

    results: list[BatchResult] = []
    n_ok = n_fail = n_skip = 0

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(_process_single, a): a for a in args_list}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            _print_progress(result, show_all=(verbose or debug))
            if result.status == "ok":
                n_ok += 1
            elif result.status == "failed":
                n_fail += 1
            else:
                n_skip += 1

            if not quiet and not verbose and not debug:
                _show_simple_progress(i, len(files), n_fail)

    elapsed = (time.perf_counter() - start_total) * 1000

    _print_batch_summary(BatchSummary(
        total=len(files),
        succeeded=n_ok,
        skipped=n_skip,
        failed=n_fail,
        elapsed_ms=elapsed,
        results=results,
    ))

    if n_fail > 0:
        raise SystemExit(1)


def _show_simple_progress(current: int, total: int, failures: int) -> None:
    pct = current / total * 100
    msg = f"\r  [{current}/{total}] {pct:.0f}%"
    if failures:
        msg += f" ({failures} failed)"
    sys.stderr.write(msg)
    if current == total:
        sys.stderr.write("\n")


def _print_batch_summary(summary: BatchSummary) -> None:
    """Print a formatted batch summary."""
    sep = "─" * 40
    lines = [
        "",
        sep,
        "  Batch Summary",
        sep,
        f"  Files found:    {summary.total}",
        f"  Rendered:       {summary.succeeded}",
        f"  Skipped:        {summary.skipped}",
        f"  Failed:         {summary.failed}",
        f"  Time taken:     {summary.elapsed_ms / 1000:.1f}s",
        sep,
    ]
    logger.info("\n".join(lines))


# ---------------------------------------------------------------------------
# watch
# ---------------------------------------------------------------------------


def watch_cmd(
    paths: List[str],
    output_dir: Optional[str] = None,
    language: Optional[str] = None,
    optimize: bool = False,
    recursive: bool = False,
    debounce: float = 1.0,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Watch diagram files for changes and auto-render."""
    import time as time_module


    files = _scan_files(paths, recursive=recursive)
    if not files:
        logger.warning("No diagram files found in %s", paths)
        raise SystemExit(0)

    mtimes: dict[str, float] = {}
    for f in files:
        mtimes[str(f)] = f.stat().st_mtime

    logger.info(
        "Watching %d file(s) for changes (debounce=%.1fs)...",
        len(files),
        debounce,
    )

    try:
        while True:
            changed = _detect_changes(files, mtimes)
            if changed:
                for file_path in changed:
                    _watch_handle_change(
                        file=str(file_path),
                        output_dir=output_dir,
                        language=language,
                        optimize=optimize,
                    )
            time_module.sleep(debounce)
    except KeyboardInterrupt:
        logger.info("Watch stopped.")


def _detect_changes(files: list[Path], mtimes: dict[str, float]) -> list[Path]:
    changed: list[Path] = []
    for f in files:
        key = str(f)
        try:
            current = f.stat().st_mtime
        except OSError:
            continue
        if key not in mtimes:
            changed.append(f)
        elif current != mtimes[key]:
            changed.append(f)
        mtimes[key] = current
    return changed


def _watch_handle_change(
    file: str,
    output_dir: str | None,
    language: str | None,
    optimize: bool,
) -> None:
    from pidraw.renderer import render

    path = Path(file)
    logger.info("Change detected: %s", file)
    try:
        source = _read_source(file)
        result = render(source, language=language)
        if optimize and isinstance(result, str):
            try:
                opt = optimize_svg(result)
                result = opt.svg
            except Exception:
                pass

        if output_dir:
            out_path = Path(output_dir) / f"{path.stem}.svg"
            _write_output(str(out_path), result)
            logger.info("  Wrote %s", out_path)
        else:
            out_path = path.with_suffix(".svg")
            _write_output(str(out_path), result)
            logger.info("  Wrote %s", out_path)
    except PiDrawError as exc:
        logger.error("  Failed: %s", exc)


# ---------------------------------------------------------------------------
# plugins
# ---------------------------------------------------------------------------


def plugins_cmd(
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """List all registered and discovered renderer plugins."""
    registered = list_renderers()
    discovered = discover_plugins()

    lines: list[str] = []
    if registered:
        lines.append("Registered renderers:")
        for name, r in sorted(registered.items()):
            cls_name = type(r).__name__
            discovered_mark = " [discovered]" if name in discovered else ""
            lines.append(f"  {name:<15}  {cls_name}{discovered_mark}")
    else:
        lines.append("No registered renderers.")

    external = {k: v for k, v in discovered.items() if k not in registered}
    if external:
        lines.append("")
        lines.append("External plugins (not in registry):")
        for name, r in sorted(external.items()):
            lines.append(f"  {name:<15}  {type(r).__name__}")

    lines.append("")
    lines.append(f"Total: {len(registered)} registered, {len(discovered)} discovered")
    sys.stdout.write("\n".join(lines))
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


def version_cmd(
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Show the PiDraw version."""
    sys.stdout.write(f"pidraw v{__version__}\n")


# ---------------------------------------------------------------------------
# formats
# ---------------------------------------------------------------------------


def formats_cmd(
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """List all supported diagram formats with live status."""
    stat = status_table() if not quiet else format_table()
    sys.stdout.write(stat)
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------


def setup_cmd(
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Auto-install missing CLI tools for diagram formats."""
    results = setup_all()

    lines: list[str] = [
        "",
        "  Setup Results",
        "-" * 40,
    ]
    for lang, msg in sorted(results.items()):
        lines.append(f"  {lang:<15}  {msg}")
    lines.append("-" * 40)
    sys.stdout.write("\n".join(lines))
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# docs
# ---------------------------------------------------------------------------


def docs_cmd(
    file: str,
    output: Optional[str] = None,
    output_format: str = "html",
    format: str = "svg",
    language: Optional[str] = None,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Render diagram blocks in a markdown file to a rendered document."""
    from pidraw.docs import render_md_file

    start = time.perf_counter()

    try:
        result = render_md_file(file, output_format=output_format, fmt=format)
    except Exception as exc:
        logger.error("Docs render failed: %s", exc)
        raise SystemExit(1) from exc

    elapsed = (time.perf_counter() - start) * 1000

    if output:
        _write_output(output, result)
        logger.info("Wrote %s", output)
    else:
        sys.stdout.write(result)
        sys.stdout.write("\n")

    if verbose or debug:
        logger.info("Processed %s in %.0f ms", file, elapsed)


# ---------------------------------------------------------------------------
# benchmark
# ---------------------------------------------------------------------------


def benchmark_cmd(
    quick: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Run the PiDraw benchmark suite."""
    from pidraw.benchmark import format_report, run_benchmarks

    if not quiet:
        logger.info("Running benchmarks (this may take a moment)...")

    report = run_benchmarks(quick=quick)

    output = format_report(report)
    sys.stdout.write(output)
    sys.stdout.write("\n")
