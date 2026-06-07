from __future__ import annotations

from typing import Optional

from pidraw.core.converters.base import DiagramConverter, converter_registry
from pidraw.core.converters.ascii import ASCIIConverter
from pidraw.core.converters.d2 import D2Converter
from pidraw.core.converters.graphviz import GraphvizConverter
from pidraw.core.converters.mermaid import MermaidConverter
from pidraw.core.converters.plantuml import PlantUMLConverter
from pidraw.core.models import Diagram


def get_converter(language: str) -> Optional[DiagramConverter]:
    cls = converter_registry.get(language.lower())
    return cls() if cls is not None else None


def convert(source: str, language: str) -> Diagram:
    converter = get_converter(language)
    if converter is None:
        raise ValueError(f"No converter registered for language: {language}")
    return converter.parse(source)


def list_converters() -> list[str]:
    return list(converter_registry.keys())


__all__ = [
    "DiagramConverter",
    "MermaidConverter",
    "PlantUMLConverter",
    "GraphvizConverter",
    "D2Converter",
    "ASCIIConverter",
    "get_converter",
    "convert",
    "list_converters",
    "converter_registry",
]
