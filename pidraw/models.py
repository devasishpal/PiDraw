"""Data models for the PiDraw library."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DiagramLanguage(str, Enum):
    """Supported diagram description languages.

    Each member maps a language name to its canonical identifier.
    """

    MERMAID = "mermaid"
    PLANTUML = "plantuml"
    GRAPHVIZ = "graphviz"
    D2 = "d2"
    ASCII = "ascii"
    BPMN = "bpmn"
    MARKMAP = "markmap"
    NOMNOML = "nomnoml"
    WAVEDROM = "wavedrom"
    STRUCTURIZR = "structurizr"
    VEGA = "vega"
    VEGA_LITE = "vega-lite"
    EXCALIDRAW = "excalidraw"
    KROKI = "kroki"
    TIKZ = "tikz"
    UNKNOWN = "unknown"


@dataclass
class DetectionResult:
    """Result of diagram language detection with confidence scoring."""

    language: DiagramLanguage
    confidence: float
    matched_pattern: str | None = None


@dataclass
class AnalysisResult:
    """Full analysis of a diagram source string."""

    detected_language: str
    confidence: float
    renderer_chosen: str | None = None
    warnings: list[str] = field(default_factory=list)
    svg: str | None = None
    original_size: int = 0
    optimized_size: int = 0
    bytes_saved: int = 0
    reduction_percent: float = 0.0
