from __future__ import annotations

from pidraw.core.models import Diagram, Layout, LayoutType
from pidraw.layout.base import LayoutEngine, layout_registry
from pidraw.layout.flow import FlowLayout
from pidraw.layout.grid import GridLayout
from pidraw.layout.layered import LayeredLayout
from pidraw.layout.tree import TreeLayout


def apply_layout(diagram: Diagram) -> Diagram:
    layout_spec = diagram.layout
    if layout_spec is None or layout_spec.layout_type == LayoutType.NONE:
        return diagram

    engine_cls = layout_registry.get(layout_spec.layout_type)
    if engine_cls is None:
        return diagram

    engine = engine_cls()
    return engine.layout(diagram)


def get_layout_engine(layout_type: LayoutType) -> LayoutEngine | None:
    cls = layout_registry.get(layout_type)
    return cls() if cls is not None else None


__all__ = [
    "LayoutEngine",
    "FlowLayout",
    "GridLayout",
    "LayeredLayout",
    "TreeLayout",
    "Layout",
    "apply_layout",
    "get_layout_engine",
]
