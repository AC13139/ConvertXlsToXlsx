"""Unit tests for ``convertxls.config``."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from convertxls.config import ConversionOptions


def test_defaults() -> None:
    opts = ConversionOptions()
    assert opts.backend == "auto"
    assert opts.overwrite is False
    assert opts.workers == 4
    assert opts.verbose is False


def test_immutability() -> None:
    opts = ConversionOptions()
    with pytest.raises(FrozenInstanceError):
        opts.backend = "libreoffice"  # type: ignore[misc]


def test_workers_must_be_positive() -> None:
    with pytest.raises(ValueError):
        ConversionOptions(workers=0)
    with pytest.raises(ValueError):
        ConversionOptions(workers=-1)


def test_backend_must_be_non_empty() -> None:
    with pytest.raises(ValueError):
        ConversionOptions(backend="")
