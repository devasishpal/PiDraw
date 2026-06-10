"""Formats registry — list all supported diagram formats with metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FormatInfo:
    """Metadata for a supported diagram format."""

    language: str
    label: str
    extensions: list[str]
    description: str
    cli_tool: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# Canonical format registry
# ---------------------------------------------------------------------------

_FORMATS: list[FormatInfo] = [
    FormatInfo(
        language="mermaid",
        label="Mermaid",
        extensions=[".mmd", ".mermaid"],
        description="Flowcharts, sequence diagrams, class diagrams, Gantt charts, and more",
        cli_tool="mmdc",
    ),
    FormatInfo(
        language="plantuml",
        label="PlantUML",
        extensions=[".puml", ".plantuml", ".iuml"],
        description="Sequence, class, activity, component, state, object, and deployment diagrams",
        cli_tool="plantuml / java -jar plantuml.jar",
    ),
    FormatInfo(
        language="graphviz",
        label="Graphviz DOT",
        extensions=[".dot", ".gv"],
        description="Directed and undirected graphs with automatic layout",
        cli_tool="dot",
    ),
    FormatInfo(
        language="d2",
        label="D2",
        extensions=[".d2"],
        description="Declarative diagrams with a modern syntax",
        cli_tool="d2",
    ),
    FormatInfo(
        language="ascii",
        label="ASCII Art",
        extensions=[".txt"],
        description="Simple ASCII art diagrams rendered as SVG",
        cli_tool="",
        notes="Built-in; no CLI required for basic patterns",
    ),
    FormatInfo(
        language="bpmn",
        label="BPMN",
        extensions=[".bpmn"],
        description="Business Process Model and Notation diagrams (XML/JSON)",
        cli_tool="bpmn-to-svg",
    ),
    FormatInfo(
        language="markmap",
        label="Markmap",
        extensions=[".mm"],
        description="Markdown-based mind maps",
        cli_tool="markmap",
    ),
    FormatInfo(
        language="nomnoml",
        label="Nomnoml",
        extensions=[".noml"],
        description="UML diagrams with a simple syntax",
        cli_tool="nomnoml",
    ),
    FormatInfo(
        language="wavedrom",
        label="WaveDrom",
        extensions=[".json"],
        description="Digital timing diagrams / waveform renderer",
        cli_tool="wavedrom-cli",
    ),
    FormatInfo(
        language="structurizr",
        label="Structurizr",
        extensions=[".dsl"],
        description="C4 model diagrams for software architecture",
        cli_tool="structurizr-cli",
    ),
    FormatInfo(
        language="vega",
        label="Vega",
        extensions=[".json"],
        description="Declarative grammar for interactive graphics",
        cli_tool="vg2svg",
    ),
    FormatInfo(
        language="vega-lite",
        label="Vega-Lite",
        extensions=[".json"],
        description="High-level grammar for statistical graphics",
        cli_tool="vl2svg / vl-convert-python",
    ),
    FormatInfo(
        language="excalidraw",
        label="Excalidraw",
        extensions=[".json", ".excalidraw"],
        description="Hand-drawn style whiteboard diagrams",
        cli_tool="excalidraw",
    ),
    FormatInfo(
        language="kroki",
        label="Kroki",
        extensions=[".txt", ".kroki"],
        description="Universal diagram API (proxies to many backends)",
        cli_tool="",
        notes="HTTP API; no local CLI required",
    ),
]


def list_formats() -> list[FormatInfo]:
    """Return a list of all supported diagram formats."""
    return list(_FORMATS)


def format_table() -> str:
    """Return a human-readable table of all formats.

    Columns: Language, Extensions, CLI Tool, Description.
    """
    lines: list[str] = []
    lines.append(f"{'Language':<16} {'Extensions':<24} {'CLI Tool':<30} Description")
    lines.append("-" * 120)
    for fmt in _FORMATS:
        ext_str = ", ".join(fmt.extensions)
        cli = fmt.cli_tool or "(built-in)"
        lines.append(f"{fmt.language:<16} {ext_str:<24} {cli:<30} {fmt.description}")
    return "\n".join(lines)


def _get_cli_tool_name(cli_tool: str) -> str | None:
    """Extract the primary CLI tool name from format metadata."""
    if not cli_tool:
        return None
    tool = cli_tool.split("/")[0].split("+")[0].strip()
    return tool or None


# Possible CLI tool names per format (renderers may search multiple names)
_CLI_SEARCH_ORDER: dict[str, list[str]] = {
    "bpmn": ["bpmn-to-svg", "bpmn-svg"],
    "structurizr": ["structurizr-cli", "structurizr"],
}


def _resolve_cli(fmt: FormatInfo) -> tuple[str | None, str | None]:
    """Return (resolved_tool_name, resolved_path) for a format.

    Checks all possible CLI names for the format; returns the first
    one found on PATH, or (expected_name, None) if nothing is found.
    """
    import shutil

    names = _CLI_SEARCH_ORDER.get(fmt.language)
    if names is None:
        name = _get_cli_tool_name(fmt.cli_tool)
        names = [name] if name else []

    for n in names:
        p = shutil.which(n)
        if p is not None:
            return (n, p)
    return (names[0] if names else None, None)


def status_table() -> str:
    """Return a table of all formats with live status indicators.

    Columns: Status, Language, Converter, Engine, CLI Tool.
    All data is resolved live (actual engine class, actual CLI found).
    """
    from pidraw.core.converters import get_converter
    from pidraw.engines import NativeRenderer, _BrokenRenderer
    from pidraw.exceptions import RendererNotFoundError
    from pidraw.registry import get_renderer

    lines: list[str] = []
    lines.append(f"{'':5} {'Language':<14} {'Converter':<9} {'Engine':<16} {'CLI Tool':<20} Notes")
    lines.append("-" * 90)
    for fmt in _FORMATS:
        conv = get_converter(fmt.language)
        has_converter = conv is not None

        try:
            renderer = get_renderer(fmt.language)
            renderer_broken = isinstance(renderer, _BrokenRenderer)
            engine_name = type(renderer).__name__.replace("Renderer", "")
        except RendererNotFoundError:
            renderer = None
            renderer_broken = False
            engine_name = "-"

        cli_name, cli_path = _resolve_cli(fmt)

        # Determine status symbol
        if renderer is not None and not renderer_broken:
            status = "[OK]"
            notes = ""
        elif renderer_broken:
            status = "[--]"
            notes = f"CLI '{cli_name}' not on PATH" if cli_name else "Missing CLI"
        elif not fmt.cli_tool and has_converter:
            status = "[OK]"
            notes = "Native pipeline (no CLI)"
        elif has_converter:
            status = "[NA]"
            notes = "Converter only (use render_native)"
        else:
            status = "[--]"
            notes = "No converter or renderer"

        conv_str = "yes" if has_converter else "-"
        cli_display = "(none)"
        if cli_path:
            cli_display = cli_name or "(none)"
        elif renderer is not None and not renderer_broken and isinstance(renderer, NativeRenderer):
            cli_display = "native"
        elif fmt.cli_tool and renderer_broken:
            cli_display = f"{cli_name} (missing)"

        lines.append(
            f"{status:5} {fmt.language:<14} {conv_str:<9} {engine_name:<16} {cli_display:<20} {notes}"
        )

    lines.append("")
    lines.append("  [OK] = functional   [NA] = native only   [--] = unavailable")
    return "\n".join(lines)
