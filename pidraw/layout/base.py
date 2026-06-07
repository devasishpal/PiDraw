from __future__ import annotations

from abc import ABC, abstractmethod

from pidraw.core.models import Diagram, LayoutType

layout_registry: dict[LayoutType, type["LayoutEngine"]] = {}


def register_layout(layout_type: LayoutType):
    def decorator(cls: type[LayoutEngine]) -> type[LayoutEngine]:
        layout_registry[layout_type] = cls
        return cls
    return decorator


class LayoutEngine(ABC):
    @abstractmethod
    def layout(self, diagram: Diagram) -> Diagram:
        ...
