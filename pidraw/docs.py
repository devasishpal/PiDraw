from __future__ import annotations

import base64
import re
from pathlib import Path

from pidraw.detector import detect
from pidraw.renderer import render

_FENCED_BLOCK = re.compile(
    r"```(\w+)?\n(.*?)```",
    re.DOTALL,
)

_DIAGRAM_LANGUAGES = {
    "mermaid", "mmd",
    "plantuml", "puml", "iuml",
    "graphviz", "dot", "gv",
    "d2",
    "bpmn",
    "nomnoml",
    "wavedrom",
    "vega",
    "vega-lite",
}


def extract_diagrams(markdown: str) -> list[dict]:
    blocks: list[dict] = []
    for match in _FENCED_BLOCK.finditer(markdown):
        lang = (match.group(1) or "").strip().lower()
        code = match.group(2).strip()
        if not code:
            continue
        is_diagram = lang in _DIAGRAM_LANGUAGES
        if not is_diagram and lang in ("", "text", "plain"):
            detected = detect(code)
            is_diagram = detected != "unknown"
            if is_diagram:
                lang = detected
        if is_diagram:
            blocks.append({
                "match": match,
                "language": lang,
                "code": code,
                "start": match.start(),
                "end": match.end(),
            })
    return blocks


def render_diagrams(
    blocks: list[dict],
    fmt: str = "svg",
    scale: float = 1.0,
) -> list[dict]:
    for block in blocks:
        try:
            result = render(block["code"], language=block["language"], format=fmt, scale=scale)
            block["rendered"] = result
        except Exception as exc:
            block["error"] = str(exc)
    return blocks


def to_html(
    markdown: str,
    blocks: list[dict],
    fmt: str = "svg",
    title: str = "PiDraw Document",
) -> str:
    parts: list[str] = []
    last_end = 0

    for block in blocks:
        parts.append(markdown[last_end:block["start"]])
        parts.append(_render_block_html(block, fmt))
        last_end = block["end"]

    parts.append(markdown[last_end:])

    body = "".join(parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape_html(title)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
  img {{ max-width: 100%; height: auto; display: block; margin: 1em 0; }}
  svg {{ max-width: 100%; height: auto; display: block; margin: 1em 0; }}
  pre {{ background: #f5f5f5; padding: 1em; border-radius: 6px; overflow-x: auto; }}
  code {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.9em; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _render_block_html(block: dict, fmt: str) -> str:
    if "error" in block:
        return f'<pre>Diagram error: {_escape_html(block["error"])}</pre>\n'

    rendered = block["rendered"]
    if fmt == "png":
        b64 = base64.b64encode(rendered).decode("ascii")
        return f'<img src="data:image/png;base64,{b64}" alt="diagram">\n'
    return rendered + "\n"


def to_markdown(
    markdown: str,
    blocks: list[dict],
    fmt: str = "svg",
) -> str:
    parts: list[str] = []
    last_end = 0

    for block in blocks:
        parts.append(markdown[last_end:block["start"]])
        parts.append(_render_block_md(block, fmt))
        last_end = block["end"]

    parts.append(markdown[last_end:])
    return "".join(parts)


def _render_block_md(block: dict, fmt: str) -> str:
    if "error" in block:
        return f'```\nERROR: {block["error"]}\n```\n'

    rendered = block["rendered"]
    if fmt == "png":
        b64 = base64.b64encode(rendered).decode("ascii")
        return f'![diagram](data:image/png;base64,{b64})\n\n'
    return f'```svg\n{rendered}\n```\n'


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def process_markdown(
    source: str,
    *,
    fmt: str = "svg",
    scale: float = 1.0,
) -> tuple[str, list[dict]]:
    blocks = extract_diagrams(source)
    if not blocks:
        return source, []
    render_diagrams(blocks, fmt=fmt, scale=scale)
    return source, blocks


def process_markdown_file(
    path: str,
    *,
    fmt: str = "svg",
    scale: float = 1.0,
) -> tuple[str, list[dict]]:
    source = Path(path).read_text(encoding="utf-8-sig")
    return process_markdown(source, fmt=fmt, scale=scale)


def render_md(
    source: str,
    *,
    output_format: str = "html",
    fmt: str = "svg",
    scale: float = 1.0,
) -> str:
    markdown, blocks = process_markdown(source, fmt=fmt, scale=scale)
    if output_format == "html":
        return to_html(markdown, blocks, fmt=fmt)
    return to_markdown(markdown, blocks, fmt=fmt)


def render_md_file(
    path: str,
    *,
    output_format: str = "html",
    fmt: str = "svg",
    scale: float = 1.0,
) -> str:
    source = Path(path).read_text(encoding="utf-8-sig")
    return render_md(source, output_format=output_format, fmt=fmt, scale=scale)
