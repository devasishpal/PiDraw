"""Language detection for diagram source code.

Recognises all built-in formats via regex patterns with confidence
scoring.  The first match wins; ties are broken by rule order (most
specific first).
"""

from __future__ import annotations

import re

from pidraw.models import DetectionResult, DiagramLanguage

# Each rule: (compiled_pattern, language, confidence)
# Rules are ordered from most specific / high-confidence to generic / low.
_DETECTION_RULES: list[tuple[re.Pattern[str], DiagramLanguage, float]] = [
    # --- PlantUML (very distinctive syntax) ---
    (re.compile(r"^@start\w+", re.MULTILINE), DiagramLanguage.PLANTUML, 0.99),
    (re.compile(r"^@end\w+", re.MULTILINE), DiagramLanguage.PLANTUML, 0.97),
    # --- Mermaid (keyword-diagram) ---
    (re.compile(r"^graph\s+(TB|BT|RL|LR|TD)"), DiagramLanguage.MERMAID, 0.98),
    (re.compile(r"^flowchart\s+(TB|BT|RL|LR|TD)"), DiagramLanguage.MERMAID, 0.98),
    (re.compile(r"^sequenceDiagram"), DiagramLanguage.MERMAID, 0.98),
    (re.compile(r"^classDiagram"), DiagramLanguage.MERMAID, 0.98),
    (re.compile(r"^stateDiagram"), DiagramLanguage.MERMAID, 0.98),
    (re.compile(r"^erDiagram"), DiagramLanguage.MERMAID, 0.98),
    (re.compile(r"^gantt"), DiagramLanguage.MERMAID, 0.98),
    (re.compile(r"^pie"), DiagramLanguage.MERMAID, 0.96),
    (re.compile(r"^journey"), DiagramLanguage.MERMAID, 0.96),
    (re.compile(r"^mindmap"), DiagramLanguage.MERMAID, 0.96),
    (re.compile(r"^timeline"), DiagramLanguage.MERMAID, 0.96),
    (re.compile(r"^gitgraph"), DiagramLanguage.MERMAID, 0.96),
    # --- Graphviz DOT ---
    (re.compile(r"^digraph\s+\w+"), DiagramLanguage.GRAPHVIZ, 0.95),
    (re.compile(r"^digraph\s*\{"), DiagramLanguage.GRAPHVIZ, 0.94),
    (re.compile(r"^strict\s+digraph"), DiagramLanguage.GRAPHVIZ, 0.95),
    (re.compile(r"^graph\s+\w+\s*\{"), DiagramLanguage.GRAPHVIZ, 0.93),
    (re.compile(r"^graph\s*\{"), DiagramLanguage.GRAPHVIZ, 0.90),
    (re.compile(r"^strict\s+graph"), DiagramLanguage.GRAPHVIZ, 0.93),
    # --- D2 ---
    (re.compile(r"^direction:\s+(right|left|up|down)", re.MULTILINE), DiagramLanguage.D2, 0.93),
    (re.compile(r"^\s*shape:\s+\w+", re.MULTILINE), DiagramLanguage.D2, 0.92),
    (re.compile(r"^\s*style\s*:\s*\{", re.MULTILINE), DiagramLanguage.D2, 0.91),
    (re.compile(r"^\s*style\s+\w+", re.MULTILINE), DiagramLanguage.D2, 0.88),
    (re.compile(r"^\w[\w.]*\s*:\s*\{"), DiagramLanguage.D2, 0.85),
    (re.compile(r"^\s*\w[\w.]*\s*<[-][>]\s*\w[\w.]*"), DiagramLanguage.D2, 0.87),
    (re.compile(r"^\s*\w[\w.]*\s*[-][>]\s*\w[\w.]*"), DiagramLanguage.D2, 0.85),
    # --- TikZ ---
    (re.compile(r"\\begin\{tikzpicture\}"), DiagramLanguage.TIKZ, 0.98),
    (re.compile(r"\\tikz"), DiagramLanguage.TIKZ, 0.92),
    (re.compile(r"\\node\["), DiagramLanguage.TIKZ, 0.85),
    (re.compile(r"\\draw\["), DiagramLanguage.TIKZ, 0.85),
    # --- BPMN (XML/JSON schema) ---
    (re.compile(r'xmlns:bpmn=["\']http://www\.omg\.org/spec/BPMN'), DiagramLanguage.BPMN, 0.99),
    (re.compile(r"bpmn:definitions"), DiagramLanguage.BPMN, 0.98),
    (re.compile(r"bpmn:process"), DiagramLanguage.BPMN, 0.97),
    (re.compile(r'xmlns=["\']http://www\.omg\.org/spec/BPMN'), DiagramLanguage.BPMN, 0.95),
    (re.compile(r"definitions.*targetNamespace.*omg"), DiagramLanguage.BPMN, 0.90),
    # --- Structurizr DSL ---
    (re.compile(r"^workspace\s*\{", re.MULTILINE), DiagramLanguage.STRUCTURIZR, 0.97),
    (re.compile(r"^\s*model\s*\{", re.MULTILINE), DiagramLanguage.STRUCTURIZR, 0.95),
    (re.compile(r"^\s*views\s*\{", re.MULTILINE), DiagramLanguage.STRUCTURIZR, 0.95),
    # --- Vega (JSON-based) ---
    (re.compile(r'"\$schema"\s*:\s*"[^"]*vega[^"]*"'), DiagramLanguage.VEGA, 0.95),
    (re.compile(r'"mark"\s*:\s*\{'), DiagramLanguage.VEGA, 0.88),
    # --- Vega-Lite ---
    (re.compile(r'"\$schema"\s*:\s*"[^"]*vega-lite[^"]*"'), DiagramLanguage.VEGA_LITE, 0.97),
    (re.compile(r'"mark"\s*:\s*"[a-z]+"'), DiagramLanguage.VEGA_LITE, 0.85),
    # --- WaveDrom ---
    (re.compile(r'\{\s*"signal"\s*:\s*\['), DiagramLanguage.WAVEDROM, 0.97),
    (re.compile(r'\{\s*signal\s*:\s*\['), DiagramLanguage.WAVEDROM, 0.96),
    (re.compile(r'"wave":\s*["\']'), DiagramLanguage.WAVEDROM, 0.96),
    # --- Excalidraw ---
    (re.compile(r'"type"\s*:\s*"excalidraw"'), DiagramLanguage.EXCALIDRAW, 0.98),
    (re.compile(r'"elements"\s*:\s*\['), DiagramLanguage.EXCALIDRAW, 0.85),
    # --- Markmap ---
    (re.compile(r"^#{1,6}\s+\S+.*\n#{1,6}\s+\S+", re.MULTILINE), DiagramLanguage.MARKMAP, 0.50),
    # --- Nomnoml ---
    (re.compile(r"^#[\w:]+\s*:", re.MULTILINE), DiagramLanguage.NOMNOML, 0.90),
    (re.compile(r"^\[<[^>]+>\]", re.MULTILINE), DiagramLanguage.NOMNOML, 0.88),
    (re.compile(r"^\[[\w]+\]", re.MULTILINE), DiagramLanguage.NOMNOML, 0.80),
    # --- ASCII art ---
    (re.compile(r"^\s*\+--\+", re.MULTILINE), DiagramLanguage.ASCII, 0.65),
    (re.compile(r"^\s*\.-\.", re.MULTILINE), DiagramLanguage.ASCII, 0.60),
    (re.compile(r"^\s*\|.*\|", re.MULTILINE), DiagramLanguage.ASCII, 0.55),
    (re.compile(r"^\s*[\+\-\.]+\s*[\+\-\.]+\s*$", re.MULTILINE), DiagramLanguage.ASCII, 0.55),
]


def detect_language(source: str) -> DetectionResult:
    """Detect the diagram language with confidence scoring.

    Parameters
    ----------
    source : str
        The diagram source code.

    Returns
    -------
    DetectionResult
        Result containing the detected language and confidence score.

    """
    if not source or not source.strip():
        return DetectionResult(DiagramLanguage.UNKNOWN, 0.0)

    trimmed = source.strip()
    best_lang: DiagramLanguage = DiagramLanguage.UNKNOWN
    best_conf: float = 0.0
    best_pattern: str | None = None

    for pattern, language, confidence in _DETECTION_RULES:
        if pattern.search(trimmed):
            if confidence > best_conf:
                best_lang = language
                best_conf = confidence
                best_pattern = pattern.pattern

    return DetectionResult(best_lang, best_conf, best_pattern)


def detect(source: str) -> str:
    """Detect the diagram language used in *source* (legacy).

    Returns the canonical language name string (e.g. ``"mermaid"``)
    or ``"unknown"``.

    This is a convenience wrapper around :func:`detect_language`.
    """
    return detect_language(source).language.value
