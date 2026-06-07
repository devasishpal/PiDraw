"""Typer application definition for the PiDraw CLI."""

from __future__ import annotations

from typing import List, Optional

import typer

from pidraw.cli import logging as pidraw_logging
from pidraw.cli.commands import (
    analyze_cmd,
    batch_cmd,
    benchmark_cmd,
    detect_cmd,
    formats_cmd,
    optimize_cmd,
    plugins_cmd,
    render_cmd,
    setup_cmd,
    version_cmd,
    watch_cmd,
)

# ---------------------------------------------------------------------------
# Shared option definitions
# ---------------------------------------------------------------------------

_quiet_opt = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output")
_verbose_opt = typer.Option(False, "--verbose", "-v", help="Show detailed output")
_debug_opt = typer.Option(False, "--debug", "-d", help="Show debug messages")
_output_opt = typer.Option(None, "--output", "-o", help="Output file path")
_language_opt = typer.Option(None, "--language", "-l", help="Explicit diagram language")
_optimize_opt = typer.Option(False, "--optimize", "-O", help="Optimise the output SVG")
_recursive_opt = typer.Option(False, "--recursive", "-r", help="Scan subdirectories recursively")
_debounce_opt = typer.Option(1.0, "--debounce", help="Watch debounce interval in seconds")


# ---------------------------------------------------------------------------
# Callback for logging setup
# ---------------------------------------------------------------------------


def _setup_logging(ctx: typer.Context) -> None:
    """Read quiet/verbose/debug from the context and configure logging."""
    params = ctx.params
    pidraw_logging.configure_logging(
        quiet=params.get("quiet", False),
        verbose=params.get("verbose", False),
        debug=params.get("debug", False),
    )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="pidraw",
    help="Universal diagram rendering platform — convert diagram source to SVG",
    no_args_is_help=True,
    rich_markup_mode="rich",
    callback=_setup_logging,
)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


@app.command()
def render(
    file: str = typer.Argument(..., help="Diagram source file"),
    output: Optional[str] = _output_opt,
    language: Optional[str] = _language_opt,
    optimize: bool = _optimize_opt,
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Render a diagram file to SVG."""
    render_cmd(
        file=file,
        output=output,
        language=language,
        optimize=optimize,
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------


@app.command()
def detect(
    file: str = typer.Argument(..., help="Diagram source file"),
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Detect the diagram language used in a file."""
    detect_cmd(
        file=file,
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


@app.command()
def analyze(
    file: str = typer.Argument(..., help="Diagram source file"),
    render: bool = typer.Option(True, "--render/--no-render", help="Run the renderer"),
    optimize: bool = typer.Option(True, "--optimize/--no-optimize", help="Optimise the output SVG"),
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Analyse a diagram file with full diagnostics."""
    analyze_cmd(
        file=file,
        render=render,
        optimize=optimize,
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# optimize
# ---------------------------------------------------------------------------


@app.command()
def optimize(
    file: str = typer.Argument(..., help="SVG file to optimise"),
    output: Optional[str] = _output_opt,
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Optimise an SVG file."""
    optimize_cmd(
        file=file,
        output=output,
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------


@app.command()
def batch(
    paths: List[str] = typer.Argument(..., help="Files or directories to process"),
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", help="Output directory for SVGs"
    ),
    language: Optional[str] = _language_opt,
    optimize: bool = _optimize_opt,
    recursive: bool = _recursive_opt,
    workers: Optional[int] = typer.Option(
        None, "--workers", "-w", help="Number of parallel workers"
    ),
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Render multiple diagram files to SVG."""
    batch_cmd(
        paths=paths,
        output_dir=output_dir,
        language=language,
        optimize=optimize,
        recursive=recursive,
        workers=workers,
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# watch
# ---------------------------------------------------------------------------


@app.command()
def watch(
    paths: List[str] = typer.Argument(..., help="Files or directories to watch"),
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", help="Output directory for SVGs"
    ),
    language: Optional[str] = _language_opt,
    optimize: bool = _optimize_opt,
    recursive: bool = _recursive_opt,
    debounce: float = _debounce_opt,
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Watch diagram files for changes and auto-render."""
    watch_cmd(
        paths=paths,
        output_dir=output_dir,
        language=language,
        optimize=optimize,
        recursive=recursive,
        debounce=debounce,
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# plugins
# ---------------------------------------------------------------------------


@app.command()
def plugins(
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """List all registered and discovered renderer plugins."""
    plugins_cmd(
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


@app.command()
def version(
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Show the PiDraw version."""
    version_cmd(
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# formats
# ---------------------------------------------------------------------------


@app.command()
def formats(
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """List all supported diagram formats."""
    formats_cmd(
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# benchmark
# ---------------------------------------------------------------------------


@app.command()
def setup(
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Auto-install missing CLI tools for diagram formats."""
    setup_cmd(
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


@app.command()
def benchmark(
    quick: bool = typer.Option(False, "--quick", "-q", help="Run fewer iterations"),
    quiet: bool = _quiet_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
) -> None:
    """Run the PiDraw benchmark suite."""
    benchmark_cmd(
        quick=quick,
        quiet=quiet,
        verbose=verbose,
        debug=debug,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
