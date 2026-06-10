from __future__ import annotations

from abc import ABC, abstractmethod

from pidraw.core.models import Diagram

converter_registry: dict[str, type["DiagramConverter"]] = {}


def register_converter(language: str):
    def decorator(cls: type[DiagramConverter]) -> type[DiagramConverter]:
        converter_registry[language.lower()] = cls
        return cls

    return decorator


class DiagramConverter(ABC):
    language: str = ""

    @abstractmethod
    def parse(self, source: str) -> Diagram: ...

    def detect(self, source: str) -> float:
        return 0.0

    @classmethod
    def create(cls) -> "DiagramConverter":
        return cls()
