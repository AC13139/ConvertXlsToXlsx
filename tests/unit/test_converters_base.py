"""Unit tests for ``convertxls.converters.base``."""

from __future__ import annotations

from pathlib import Path

import pytest

from convertxls.converters.base import ConversionResult, Converter


def test_conversion_result_ok_property() -> None:
    r = ConversionResult(
        src=Path("a.xls"),
        dst=Path("a.xlsx"),
        backend="libreoffice",
        duration_ms=10,
        return_code=0,
    )
    assert r.ok is True


def test_conversion_result_failure_is_not_ok() -> None:
    r = ConversionResult(
        src=Path("a.xls"),
        dst=Path("a.xlsx"),
        backend="libreoffice",
        duration_ms=10,
        return_code=2,
        stderr="boom",
    )
    assert r.ok is False


def test_converter_is_abstract() -> None:
    with pytest.raises(TypeError):
        Converter()  # type: ignore[abstract]


def test_converter_subclass_must_implement_both() -> None:
    class Half(Converter):
        name = "half"
        priority = 50

        def is_available(self) -> bool:
            return True

        # convert() missing on purpose

    with pytest.raises(TypeError):
        Half()  # type: ignore[abstract]


def test_subclass_with_both_methods_is_concrete() -> None:
    class Full(Converter):
        name = "full"
        priority = 50

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

    c = Full()
    assert c.info().available is True
