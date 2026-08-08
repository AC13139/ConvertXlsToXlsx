"""Unit tests for the converter registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from convertxls.converters import (
    REGISTRY,
    Converter,
    available_backends,
    backend_info,
    get_converter,
    register_backend,
)
from convertxls.converters.base import BackendInfo, ConversionResult
from convertxls.exceptions import ConverterNotFoundError


@pytest.fixture(autouse=True)
def _snapshot_registry() -> None:
    """Save and restore the registry around each test so registrations do not leak."""
    saved = list(REGISTRY._items.items())  # type: ignore[attr-defined]
    yield
    REGISTRY._items.clear()  # type: ignore[attr-defined]
    REGISTRY._items.update(saved)  # type: ignore[attr-defined]


def test_registry_lookup_and_ordering() -> None:
    names = REGISTRY.names()
    assert "libreoffice" in names
    assert len(names) >= 1
    # LibreOffice is the only built-in backend and must come first.
    assert names[0] == "libreoffice"


def test_get_converter_returns_expected_backend() -> None:
    backend = get_converter("libreoffice")
    assert backend.name == "libreoffice"


def test_get_converter_raises_for_unknown() -> None:
    with pytest.raises(ConverterNotFoundError):
        get_converter("does-not-exist")


def test_available_backends_returns_list() -> None:
    backends = available_backends()
    assert isinstance(backends, list)
    # In CI without LibreOffice this may be empty — we just assert
    # that the call returns a list and contains *registered* entries.
    names = {b.name for b in backends}
    assert names.issubset(set(REGISTRY.names()))


def test_backend_info_snapshot() -> None:
    infos = backend_info()
    by_name = {i.name: i for i in infos}
    assert "libreoffice" in by_name
    assert all(isinstance(i, BackendInfo) for i in infos)


def test_register_backend_decorator() -> None:
    @register_backend
    class DemoConverter(Converter):
        name = "demo-test"
        priority = 999

        def is_available(self) -> bool:
            return True

        def convert(self, src: Path, dst: Path, *, overwrite: bool) -> ConversionResult:
            return ConversionResult(
                src=src,
                dst=dst,
                backend=self.name,
                duration_ms=0,
                return_code=0,
            )

    try:
        assert "demo-test" in REGISTRY
        assert REGISTRY.get("demo-test").name == "demo-test"
    finally:
        REGISTRY._items.pop("demo-test", None)  # type: ignore[attr-defined]


def test_register_rejects_missing_name() -> None:
    with pytest.raises(ValueError):

        @register_backend
        class _Anonymous(Converter):  # type: ignore[abstract]
            name = ""

            def is_available(self) -> bool:
                return True

            def convert(self, src: Path, dst: Path, *, overwrite: bool) -> ConversionResult:
                return ConversionResult(
                    src=src,
                    dst=dst,
                    backend="",
                    duration_ms=0,
                    return_code=0,
                )
