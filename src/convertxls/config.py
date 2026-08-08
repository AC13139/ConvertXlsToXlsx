"""Frozen dataclasses describing public configuration options."""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_WORKERS = 4
DEFAULT_BACKEND = "auto"


@dataclass(frozen=True)
class ConversionOptions:
    """Immutable options shared by every public API entry point.

    Attributes
    ----------
    backend:
        Name of a registered backend, or ``"auto"`` to pick the first
        available backend in priority order. Case-sensitive.
    overwrite:
        When ``False`` (default), refuse to overwrite an existing output file.
    workers:
        Maximum number of parallel workers for batch operations. Must be at
        least 1. ``1`` means sequential.
    verbose:
        When ``True``, raise logging verbosity to ``DEBUG``.
    """

    backend: str = DEFAULT_BACKEND
    overwrite: bool = False
    workers: int = DEFAULT_WORKERS
    verbose: bool = False

    def __post_init__(self) -> None:
        if self.workers < 1:
            raise ValueError(f"workers must be >= 1, got {self.workers!r}")
        if not self.backend:
            raise ValueError("backend must be a non-empty string")


@dataclass(frozen=True)
class DiscoveryResult:
    """The list of input files a recursive directory scan produced.

    Carries the relative-to-source paths so callers can reproduce the same
    tree under a destination directory.
    """

    src_dir: str
    files: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    """Each entry is ``(absolute_path, relative_to_src_dir)``."""
