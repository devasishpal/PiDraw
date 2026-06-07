"""Built-in renderer engines — all registered on import."""

from pidraw.engines.base import BaseRenderer
from pidraw.engines.bpmn import BPMNRenderer
from pidraw.engines.d2 import D2Renderer
from pidraw.engines.excalidraw import ExcalidrawRenderer
from pidraw.engines.graphviz import GraphvizRenderer
from pidraw.engines.kroki import KrokiRenderer
from pidraw.engines.markmap import MarkmapRenderer
from pidraw.engines.mermaid import MermaidRenderer
from pidraw.engines.nomnoml import NomnomlRenderer
from pidraw.engines.plantuml import PlantUMLRenderer
from pidraw.engines.structurizr import StructurizrRenderer
from pidraw.engines.tikz import TikzRenderer
from pidraw.engines.vega import VegaRenderer
from pidraw.engines.vega_lite import VegaLiteRenderer
from pidraw.engines.wavedrom import WaveDromRenderer
from pidraw.core.converters import get_converter
from pidraw.engines.native import NativeRenderer
from pidraw.exceptions import RenderingError, RendererNotFoundError
from pidraw.registry import get_renderer, register_renderer

_REGISTRATIONS: list[tuple[str, type[BaseRenderer], tuple[object, ...]]] = [
    ("mermaid", MermaidRenderer, ()),
    ("graphviz", GraphvizRenderer, ()),
    ("plantuml", PlantUMLRenderer, ()),
    ("d2", D2Renderer, ()),
    ("bpmn", BPMNRenderer, ()),
    ("markmap", MarkmapRenderer, ()),
    ("nomnoml", NomnomlRenderer, ()),
    ("wavedrom", WaveDromRenderer, ()),
    ("structurizr", StructurizrRenderer, ()),
    ("vega", VegaRenderer, ()),
    ("vega-lite", VegaLiteRenderer, ()),
    ("excalidraw", ExcalidrawRenderer, ()),
    ("tikz", TikzRenderer, ()),
    ("kroki", KrokiRenderer, ()),
]

class _BrokenRenderer(BaseRenderer):
    """Placeholder renderer for when the real engine could not be constructed."""

    name: str = ""

    def __init__(self, language: str, error: Exception) -> None:
        self._lang = language
        self._error = error

    def render(self, source: str) -> str:
        raise RenderingError(
            f"Renderer for '{self._lang}' is unavailable: {self._error}"
        ) from self._error


for _name, _cls, _args in _REGISTRATIONS:
    try:
        register_renderer(_name, _cls(*_args))
    except RenderingError as _exc:
        if get_converter(_name) is not None:
            register_renderer(_name, NativeRenderer(_name))
        else:
            register_renderer(_name, _BrokenRenderer(_name, _exc))

# Register native fallback for any converter-only language (e.g. ascii)
for _lang in ["ascii"]:
    if get_converter(_lang) is not None:
        try:
            get_renderer(_lang)
        except RendererNotFoundError:
            register_renderer(_lang, NativeRenderer(_lang))

__all__ = [
    "BaseRenderer",
    "MermaidRenderer",
    "GraphvizRenderer",
    "PlantUMLRenderer",
    "D2Renderer",
    "BPMNRenderer",
    "MarkmapRenderer",
    "NativeRenderer",
    "NomnomlRenderer",
    "WaveDromRenderer",
    "StructurizrRenderer",
    "VegaRenderer",
    "VegaLiteRenderer",
    "ExcalidrawRenderer",
    "KrokiRenderer",
    "TikzRenderer",
]
