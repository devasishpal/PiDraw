"""Logging configuration for the PiDraw CLI."""

from __future__ import annotations

import logging
import sys


def configure_logging(
    *,
    level: str = "WARNING",
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Set up the root pidraw logger.

    Priority: *debug* > *verbose* > *quiet* > *level*.
    """
    if debug:
        resolved = "DEBUG"
    elif verbose:
        resolved = "INFO"
    elif quiet:
        resolved = "ERROR"
    else:
        resolved = level.upper()

    logger = logging.getLogger("pidraw")
    logger.setLevel(resolved)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(resolved)

    if resolved == "DEBUG":
        fmt = "[%(asctime)s] %(name)s %(levelname)s %(message)s"
    else:
        fmt = "%(message)s"

    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)


def get_logger() -> logging.Logger:
    """Return the pidraw CLI logger."""
    return logging.getLogger("pidraw")
