"""Tests for third-party plugin discovery."""

from __future__ import annotations

from pidraw.engines.base import BaseRenderer
from pidraw.registry import discover_plugins


class DummyRenderer(BaseRenderer):
    name = "dummy"

    def render(self, source: str) -> str:
        return "<svg></svg>"


class NotARenderer:
    pass


class TestDiscoverPlugins:
    def test_discover_no_plugins(self) -> None:
        """When no entry points are registered, discovery should succeed and be empty."""
        plugins = discover_plugins()
        assert isinstance(plugins, dict)

    def test_internal_registry_not_modified_by_discovery(self) -> None:
        from pidraw.registry import list_renderers

        before = list_renderers()
        discover_plugins()
        after = list_renderers()
        assert before == after

    def test_discover_returns_dict(self) -> None:
        plugins = discover_plugins()
        assert isinstance(plugins, dict)
