"""Abstract ``Converter`` contract shared by every backend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConversionResult:
    """Immutable record of a single conversion attempt.

    Created regardless of success so callers can iterate over batch results
    uniformly. On failure, ``dst`` may not exist on disk and ``return_code``
    will be non-zero.
    """

    src: Path
    dst: Path
    backend: str
    duration_ms: int
    return_code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        """``True`` when the underlying converter exited successfully."""
        return self.return_code == 0


@dataclass(frozen=True)
class BackendInfo:
    """Lightweight description of a registered backend."""

    name: str
    priority: int
    available: bool


class Converter(ABC):
    """Abstract base class for every converter backend.

    Subclasses MUST set ``name`` (a stable, lowercase identifier) and
    ``priority`` (lower = preferred when ``auto`` is requested). They MUST
    implement :meth:`is_available` and :meth:`convert`.

    Lifecycle
    ---------
    Backends are typically instantiated once at import time and registered
    with the package registry (see :mod:`convertxls.converters`).
    """

    name: str = ""
    priority: int = 100

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` iff the underlying binary is installed and runnable.

        Implementations should cache the result — this method may be called
        many times in a single process.
        """

    @abstractmethod
    def convert(self, src: Path, dst: Path, *, overwrite: bool) -> ConversionResult:
        """Convert ``src`` into ``dst``.

        Parameters
        ----------
        src:
            The input ``.xls`` file. Must exist.
        dst:
            The output ``.xlsx`` path. Parent directories are created when
            missing.
        overwrite:
            When ``False`` and ``dst`` already exists, the backend must raise
            :class:`~convertxls.exceptions.ConvertXlsError` rather than
            silently replacing the file.

        Returns
        -------
        A :class:`ConversionResult`. Implementations are expected to populate
        ``duration_ms``, ``return_code``, and (when relevant) ``stdout`` /
        ``stderr``.
        """

    def info(self) -> BackendInfo:
        """Return a :class:`BackendInfo` snapshot for introspection."""
        return BackendInfo(name=self.name, priority=self.priority, available=self.is_available())


__all__ = ["BackendInfo", "ConversionResult", "Converter"]


# Backend implementations should raise ``ConversionFailedError`` /
# ``InvalidPathError`` from :mod:`convertxls.exceptions`. They import those
# directly — there is no cycle: ``base`` is leaf, ``exceptions`` is leaf.
