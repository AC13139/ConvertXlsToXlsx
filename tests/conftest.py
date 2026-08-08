"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_xls(tmp_path: Path) -> Path:
    """Create a tiny but valid-looking ``.xls`` file under ``tmp_path``.

    We do not need a parseable spreadsheet for unit tests — most of the
    tests mock out the converter binary. We just need a non-empty file
    with the ``.xls`` suffix so the path validation helpers are happy.
    """
    path = tmp_path / "sample.xls"
    path.write_bytes(b"\xd0\xcf\x11\xe0placeholder .xls bytes for tests")
    return path


@pytest.fixture()
def xls_dir(tmp_path: Path) -> Path:
    """Create a small directory tree with three ``.xls`` files in two folders.

    Layout::

        tmp_path/
            a.xls
            b.xls
            sub/
                c.xls
                not_a_xls.txt
    """
    root = tmp_path / "legacy"
    root.mkdir()
    (root / "a.xls").write_bytes(b"a")
    (root / "b.xls").write_bytes(b"b")
    sub = root / "sub"
    sub.mkdir()
    (sub / "c.xls").write_bytes(b"c")
    (sub / "not_a_xls.txt").write_text("ignore me")
    return root


@pytest.fixture()
def skip_if_no_soffice() -> Iterator[None]:
    """Skip the calling test when ``soffice`` is not on PATH."""
    if not _have_soffice():
        pytest.skip("soffice not installed; integration test skipped")
    yield


def _have_soffice() -> bool:
    from shutil import which

    return which("soffice") is not None


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip any inherited CONVERTXLS_* variables so tests start clean."""
    for key in list(os.environ):
        if key.startswith("CONVERTXLS_"):
            monkeypatch.delenv(key, raising=False)
    yield
