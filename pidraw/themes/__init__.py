from __future__ import annotations

from typing import Optional

from pidraw.themes.base import Theme, theme_registry
from pidraw.themes.blueprint import BlueprintTheme
from pidraw.themes.dark import DarkTheme
from pidraw.themes.light import LightTheme
from pidraw.themes.minimal import MinimalTheme
from pidraw.themes.professional import ProfessionalTheme


def get_theme(name: str) -> Optional[Theme]:
    cls = theme_registry.get(name.lower())
    return cls() if cls is not None else None


def list_themes() -> list[str]:
    return list(theme_registry.keys())


def apply_theme(diagram, theme_name: str):
    theme = get_theme(theme_name)
    if theme is not None:
        return theme.apply(diagram)
    return diagram


__all__ = [
    "Theme",
    "LightTheme",
    "DarkTheme",
    "MinimalTheme",
    "ProfessionalTheme",
    "BlueprintTheme",
    "get_theme",
    "list_themes",
    "apply_theme",
]
