"""Plugin registry for diagram renderers.

Supports registering, retrieving, listing, and discovering
``BaseRenderer`` instances by language name.  Third-party packages
can register renderers via the ``pidraw.renderers`` entry point group.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from pidraw.exceptions import PluginError, RendererNotFoundError

if TYPE_CHECKING:
    from pidraw.engines.base import BaseRenderer

_registry: Dict[str, "BaseRenderer"] = {}


def register_renderer(name: str, renderer: "BaseRenderer") -> None:
    """Register a renderer for a given language name.

    Parameters
    ----------
    name : str
        The language identifier (e.g. ``"mermaid"``).
    renderer : BaseRenderer
        An instance of a ``BaseRenderer`` subclass.

    Raises
    ------
    TypeError
        If *renderer* is not a ``BaseRenderer`` instance.

    """
    from pidraw.engines.base import BaseRenderer as _BaseRenderer

    if not isinstance(renderer, _BaseRenderer):
        raise TypeError(f"Expected BaseRenderer instance, got {type(renderer).__name__}")
    _registry[name.lower()] = renderer


def get_renderer(name: str) -> "BaseRenderer":
    """Retrieve a renderer by language name.

    Parameters
    ----------
    name : str
        The language identifier.

    Returns
    -------
    BaseRenderer
        The registered renderer instance.

    Raises
    ------
    RendererNotFoundError
        If no renderer is registered for *name*.

    """
    key = name.lower()
    if key not in _registry:
        raise RendererNotFoundError(f"No renderer registered for '{name}'")
    return _registry[key]


def list_renderers() -> Dict[str, "BaseRenderer"]:
    """Return a copy of the internal renderer registry.

    Returns
    -------
    dict[str, BaseRenderer]
        A mapping of language names to renderer instances.

    """
    return dict(_registry)


def clear_registry() -> None:
    """Remove all registered renderers (useful in testing)."""
    _registry.clear()


def discover_plugins() -> dict[str, "BaseRenderer"]:
    """Discover third-party renderer plugins.

    Plugins register via the ``pidraw.renderers`` entry point group.
    Packages can opt in by adding to ``pyproject.toml``::

        [project.entry-points."pidraw.renderers"]
        myengine = "pidraw_myengine:MyRenderer"

    Returns
    -------
    dict[str, BaseRenderer]
        Discovered renderers keyed by language name.  Does **not**
        modify the internal registry.

    """
    from pidraw.engines.base import BaseRenderer as _BaseRenderer

    discovered: dict[str, "BaseRenderer"] = {}
    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="pidraw.renderers")
        for ep in eps:
            try:
                cls = ep.load()
                instance = cls() if isinstance(cls, type) else cls
                if not isinstance(instance, _BaseRenderer):
                    raise PluginError(f"Plugin '{ep.name}' is not a BaseRenderer instance")
                discovered[ep.name] = instance
            except Exception as exc:
                raise PluginError(f"Failed to load plugin '{ep.name}': {exc}") from exc
    except Exception as exc:
        raise PluginError(f"Plugin discovery failed: {exc}") from exc
    return discovered
