"""Custom exception hierarchy for PiDraw errors."""

class PiDrawError(Exception):
    """Base exception for all PiDraw errors."""


class UnsupportedLanguageError(PiDrawError):
    """Raised when the diagram language is not supported."""


class RendererNotFoundError(PiDrawError):
    """Raised when no renderer is registered for a language."""


class RenderingError(PiDrawError):
    """Raised when rendering fails."""


class PluginError(PiDrawError):
    """Raised when plugin discovery or loading fails."""


class RecoverableRenderingError(PiDrawError):
    """A rendering error that may be recoverable via retry or fallback."""
