"""ConvertXlsToXlsx — convert legacy .xls files into modern .xlsx files.

Public API
----------

>>> from convertxls import convert_file, convert_many, convert_directory
>>> from convertxls import list_backends
"""

from __future__ import annotations

from .converters import REGISTRY, available_backends, get_converter
from .core import convert_directory, convert_file, convert_many
from .exceptions import ConvertXlsError

__version__ = "0.1.0"

__all__ = [
    "ConvertXlsError",
    "__version__",
    "available_backends",
    "convert_directory",
    "convert_file",
    "convert_many",
    "get_converter",
    "list_backends",
]


def list_backends() -> list[str]:
    """Return the names of converter backends currently registered.

    This is purely introspection — it does not check whether a given backend's
    binary is on the host ``PATH``. Use ``available_backends()`` for that.
    """
    return REGISTRY.names()
