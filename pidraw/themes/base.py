from __future__ import annotations

from abc import ABC, abstractmethod

from pidraw.core.models import Diagram, Style

theme_registry: dict[str, type["Theme"]] = {}


def register_theme(name: str):
    def decorator(cls: type[Theme]) -> type[Theme]:
        theme_registry[name.lower()] = cls
        return cls

    return decorator


class Theme(ABC):
    name: str = ""

    @abstractmethod
    def apply(self, diagram: Diagram) -> Diagram: ...

    def style(self) -> Style:
        return Style()

    @classmethod
    def create(cls) -> "Theme":
        return cls()
