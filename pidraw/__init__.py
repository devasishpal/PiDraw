"""PiDraw — universal diagram rendering platform.

Converts diagram source code from many diagram languages into
optimised SVG through a plugin-based renderer architecture.
"""

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Auto-setup: install missing CLI tools on first import (lazy, non-blocking)
# ---------------------------------------------------------------------------
import atexit
import os
import threading


def _auto_setup() -> None:
    """Run ``pidraw setup`` once in a background thread."""
    marker = os.path.join(os.path.dirname(__file__), ".setup_done")
    if os.path.exists(marker):
        return

    def _run():
        try:
            from pidraw.cli.setup import setup_all
            setup_all()
        except Exception:
            pass
        finally:
            try:
                open(marker, "w").close()
            except OSError:
                pass

    t = threading.Thread(target=_run, daemon=True, name="pidraw-setup")
    t.start()
    atexit.register(t.join)


_auto_setup()

# ---------------------------------------------------------------------------

import pidraw.engines  # noqa: F401 — trigger auto-registration
from pidraw.backend.svg import SvgBackend
from pidraw.benchmark import BenchmarkReport, BenchmarkResult, run_benchmarks
from pidraw.cache import CacheManager, CacheStats
from pidraw.core.converters import (
    ASCIIConverter,
    D2Converter,
    GraphvizConverter,
    MermaidConverter,
    PlantUMLConverter,
    convert,
    get_converter,
    list_converters,
)
from pidraw.core.models import (
    ArrowStyle,
    Diagram,
    Edge,
    EdgeStyle,
    FontWeight,
    Group,
    Label,
    Layout,
    LayoutType,
    Node,
    Point,
    Position,
    Shape,
    ShapeType,
    Size,
    Style,
    TextAlign,
    Viewport,
)
from pidraw.detector import detect, detect_language
from pidraw.diagnostics import analyze
from pidraw.engines.base import BaseRenderer
from pidraw.engines.d2 import D2Renderer
from pidraw.engines.graphviz import GraphvizRenderer
from pidraw.engines.mermaid import MermaidRenderer
from pidraw.engines.plantuml import PlantUMLRenderer
from pidraw.exceptions import (
    PiDrawError,
    PluginError,
    RendererNotFoundError,
    RenderingError,
    UnsupportedLanguageError,
)
from pidraw.formats import FormatInfo, format_table, list_formats
from pidraw.incremental import IncrementalRenderer
from pidraw.large import render_large_file
from pidraw.layout import apply_layout
from pidraw.models import AnalysisResult, DetectionResult, DiagramLanguage
from pidraw.optimizer import (
    OptimizationResult,
    optimize_by_level,
    optimize_many,
    optimize_svg,
)
from pidraw.pipeline import ExportPipeline, render_native, render_native_from_diagram
from pidraw.pool import RenderPool
from pidraw.quality import QualityProcessor
from pidraw.recovery import RecoverableRenderingError
from pidraw.registry import (
    clear_registry,
    discover_plugins,
    get_renderer,
    list_renderers,
    register_renderer,
)
from pidraw.renderer import render, render_file, render_many
from pidraw.themes import apply_theme, get_theme, list_themes
from pidraw.typography import FontSpec, estimate_text_size

__all__ = [
    "render",
    "render_file",
    "render_many",
    "render_large_file",
    "render_native",
    "render_native_from_diagram",
    "detect",
    "detect_language",
    "analyze",
    "register_renderer",
    "get_renderer",
    "list_renderers",
    "clear_registry",
    "discover_plugins",
    "BaseRenderer",
    "MermaidRenderer",
    "GraphvizRenderer",
    "PlantUMLRenderer",
    "D2Renderer",
    "DiagramLanguage",
    "DetectionResult",
    "AnalysisResult",
    "optimize_svg",
    "optimize_many",
    "optimize_by_level",
    "OptimizationResult",
    "CacheManager",
    "CacheStats",
    "RenderPool",
    "QualityProcessor",
    "IncrementalRenderer",
    "FormatInfo",
    "list_formats",
    "format_table",
    "run_benchmarks",
    "BenchmarkReport",
    "BenchmarkResult",
    "RecoverableRenderingError",
    "SvgBackend",
    "ExportPipeline",
    "Diagram",
    "Node",
    "Edge",
    "Label",
    "Shape",
    "ShapeType",
    "Style",
    "EdgeStyle",
    "ArrowStyle",
    "Layout",
    "LayoutType",
    "Group",
    "Viewport",
    "Position",
    "Size",
    "Point",
    "FontWeight",
    "TextAlign",
    "FontSpec",
    "estimate_text_size",
    "apply_layout",
    "apply_theme",
    "get_theme",
    "list_themes",
    "convert",
    "get_converter",
    "list_converters",
    "MermaidConverter",
    "PlantUMLConverter",
    "GraphvizConverter",
    "D2Converter",
    "ASCIIConverter",
    "PiDrawError",
    "UnsupportedLanguageError",
    "RendererNotFoundError",
    "RenderingError",
    "PluginError",
]
