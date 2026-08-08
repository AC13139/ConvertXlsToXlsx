"""Pluggable converter registry.

A module-level :data:`REGISTRY` holds the set of :class:`~.base.Converter`
subclasses that have been registered via the :func:`@register_backend
<register_backend>` decorator. Importing :mod:`convertxls` registers the
built-in backends; user code may register additional backends the same way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..exceptions import ConverterNotFoundError, NoConverterAvailableError
from .base import BackendInfo, ConversionResult, Converter

if TYPE_CHECKING:
    from collections.abc import Iterator


class _Registry:
    """An ordered, name-keyed collection of :class:`Converter` instances.

    Backends are stored in the order they were registered; the public
    iteration order is *priority ascending* (lower number = preferred).
    """

    def __init__(self) -> None:
        self._items: dict[str, Converter] = {}

    def register(self, backend: Converter) -> None:
        if not backend.name:
            raise ValueError("Converter.name must be set before registration")
        if backend.name in self._items:
            # Allow re-registration but warn via ordering — keep the original.
            return
        self._items[backend.name] = backend

    def get(self, name: str) -> Converter:
        try:
            return self._items[name]
        except KeyError as exc:
            raise ConverterNotFoundError(
                f"No converter registered under name {name!r}. Available: {sorted(self._items)!r}"
            ) from exc

    def all(self) -> list[Converter]:
        """Return all registered backends sorted by priority (ascending)."""
        return sorted(self._items.values(), key=lambda c: (c.priority, c.name))

    def available(self) -> list[Converter]:
        """Return registered backends whose :meth:`is_available` is ``True``,
        sorted by priority (ascending)."""
        return [c for c in self.all() if c.is_available()]

    def names(self) -> list[str]:
        """Return the names of all registered backends in priority order."""
        return [c.name for c in self.all()]

    def info(self) -> list[BackendInfo]:
        """Return a snapshot of every registered backend (name, priority, availability)."""
        return [c.info() for c in self.all()]

    def __iter__(self) -> Iterator[Converter]:
        return iter(self.all())

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._items

    def __len__(self) -> int:
        return len(self._items)


REGISTRY: _Registry = _Registry()


def register_backend(cls: type[Converter]) -> type[Converter]:
    """Class decorator that registers a :class:`Converter` subclass.

    Example
    -------
    >>> @register_backend
    ... class MyBackend(Converter):
    ...     name = "my"
    ...     priority = 50
    ...     def is_available(self) -> bool: ...
    ...     def convert(self, src, dst, *, overwrite): ...
    """
    instance = cls()
    REGISTRY.register(instance)
    return cls


# Re-export the public registry helpers at package level.
get_converter = REGISTRY.get
available_backends = REGISTRY.available
backend_info = REGISTRY.info

__all__ = [
    "REGISTRY",
    "BackendInfo",
    "ConversionResult",
    "Converter",
    "NoConverterAvailableError",
    "available_backends",
    "get_converter",
    "register_backend",
]


def _register_builtins() -> None:
    # Importing the modules triggers their top-level registration decorators.
    from . import libreoffice as _lo  # noqa: F401


_register_builtins()
