"""Abstract base renderer for all diagram engines."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseRenderer(ABC):
    """Abstract base class for all diagram renderers.

    Subclasses must implement ``render`` to convert diagram source
    text into an SVG string.
    """

    name: str = ""

    @abstractmethod
    def render(self, source: str) -> str:
        """Render a diagram source string into SVG.

        Parameters
        ----------
        source : str
            The diagram source code.

        Returns
        -------
        str
            The rendered SVG output.

        Raises
        ------
        RenderingError
            If the rendering process fails.

        """
