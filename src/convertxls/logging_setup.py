"""Logging configuration that uses only the standard library.

We intentionally avoid pulling in ``loguru`` or any similar third-party
library — the project ships with zero runtime dependencies.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

LOGGER_NAME: Final[str] = "convertxls"
_DEFAULT_FORMAT: Final[str] = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(*, verbose: bool = False) -> logging.Logger:
    """Configure the ``convertxls`` logger and return it.

    Idempotent — calling this twice does not stack handlers.

    Parameters
    ----------
    verbose:
        When ``True``, sets the logger to ``DEBUG``. Otherwise ``INFO``.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Remove any handlers previously attached (e.g. on re-init in tests).
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    """Return the ``convertxls`` logger without reconfiguring it."""
    return logging.getLogger(LOGGER_NAME)
