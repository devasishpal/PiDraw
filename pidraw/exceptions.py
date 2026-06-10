"""Custom exception hierarchy for PiDraw errors."""


class PiDrawError(Exception):
    """Base exception for all PiDraw errors."""


class LanguageNotSupportedError(PiDrawError):
    """Raised when the requested diagram language has no registered renderer."""

    def __init__(self, language: str) -> None:
        self.language = language
        super().__init__(f"No renderer registered for language: {language!r}")


class EngineNotAvailableError(PiDrawError):
    """Raised when the required CLI tool or dependency is missing."""

    def __init__(self, engine: str, setup_command: str = "") -> None:
        self.engine = engine
        self.setup_command = setup_command
        msg = f"Engine {engine!r} is not available."
        if setup_command:
            msg += f" Run: {setup_command}"
        super().__init__(msg)


class RenderError(PiDrawError):
    """Raised when a renderer fails to produce output."""

    def __init__(self, language: str, reason: str, stderr: str = "") -> None:
        self.language = language
        self.reason = reason
        self.stderr = stderr
        super().__init__(f"Render failed for {language!r}: {reason}")


class ParseError(RenderError):
    """Raised when the diagram source cannot be parsed."""


class LayoutError(RenderError):
    """Raised when the layout engine fails to position nodes."""


class RenderTimeoutError(PiDrawError):
    """Raised when a render exceeds the configured timeout."""

    def __init__(self, language: str, timeout: float) -> None:
        self.language = language
        self.timeout = timeout
        super().__init__(f"Render of {language!r} timed out after {timeout}s")


class OptimizationError(PiDrawError):
    """Raised when SVG optimization fails."""


class PngConversionError(PiDrawError):
    """Raised when SVG to PNG conversion fails."""


class UnsupportedLanguageError(LanguageNotSupportedError):
    """Backward-compatible alias for LanguageNotSupportedError.

    Deprecated: use LanguageNotSupportedError instead.
    """

    def __init__(self, message: str = "") -> None:
        if message and not message.startswith("No renderer registered"):
            super(LanguageNotSupportedError, self).__init__(message)
        else:
            super().__init__(message)  # type: ignore[arg-type]


class RendererNotFoundError(PiDrawError):
    """Raised when no renderer is registered for a language.

    Deprecated: use LanguageNotSupportedError instead.
    """


class RenderingError(PiDrawError):
    """Backward-compatible alias for RenderError.

    Deprecated: use RenderError instead.
    """

    def __init__(self, message: str = "", language: str = "", stderr: str = "") -> None:
        self.language = language
        self.stderr = stderr
        if message and not language:
            super().__init__(message)
        else:
            super().__init__(f"Render failed for {language!r}: {message}")


class PluginError(PiDrawError):
    """Raised when plugin discovery or loading fails."""


class RecoverableRenderingError(PiDrawError):
    """A rendering error that may be recoverable via retry or fallback."""
