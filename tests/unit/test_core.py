"""Unit tests for ``convertxls.core`` orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from convertxls import convert_directory, convert_file, convert_many
from convertxls.converters.base import ConversionResult
from convertxls.core import discover_xls_files
from convertxls.exceptions import InvalidPathError, NoConverterAvailableError


class _FakeConverter:
    name = "fake"
    priority = 1
    available = True

    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path, bool]] = []

    def is_available(self) -> bool:
        return self.available

    def convert(self, src: Path, dst: Path, *, overwrite: bool) -> ConversionResult:
        self.calls.append((src, dst, overwrite))
        if dst.exists() and not overwrite:
            from convertxls.exceptions import InvalidPathError

            raise InvalidPathError(f"destination already exists: {dst!s}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"fake-xlsx")
        return ConversionResult(
            src=src,
            dst=dst,
            backend=self.name,
            duration_ms=1,
            return_code=0,
        )


def _patched_converters(monkeypatch: pytest.MonkeyPatch) -> _FakeConverter:
    """Replace the registry's auto-selection with a single fake backend."""
    fake = _FakeConverter()

    def _fake_resolve(name=None):
        if not fake.available:
            raise NoConverterAvailableError()
        return fake

    monkeypatch.setattr("convertxls.core.resolve_backend", _fake_resolve)
    return fake


def test_convert_file_writes_alongside_source_when_no_dst(
    monkeypatch: pytest.MonkeyPatch,
    tmp_xls: Path,
) -> None:
    fake = _patched_converters(monkeypatch)

    result = convert_file(tmp_xls)
    assert result.dst == tmp_xls.with_suffix(".xlsx")
    assert result.dst.exists()
    assert fake.calls == [(tmp_xls, tmp_xls.with_suffix(".xlsx"), False)]


def test_convert_file_respects_overwrite_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_xls: Path,
    tmp_path: Path,
) -> None:
    _patched_converters(monkeypatch)
    out = tmp_path / "out.xlsx"
    out.write_bytes(b"existing")
    with pytest.raises(InvalidPathError):
        convert_file(tmp_xls, dst=out, overwrite=False)
    result = convert_file(tmp_xls, dst=out, overwrite=True)
    assert result.dst == out


def test_convert_file_rejects_non_xls_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patched_converters(monkeypatch)
    fake = tmp_path / "fake.txt"
    fake.write_text("hello")
    with pytest.raises(InvalidPathError):
        convert_file(fake)


def test_convert_file_raises_when_backend_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_xls: Path,
) -> None:
    def _resolve(name=None):
        raise NoConverterAvailableError()

    monkeypatch.setattr("convertxls.core.resolve_backend", _resolve)
    with pytest.raises(NoConverterAvailableError):
        convert_file(tmp_xls)


def test_convert_many_preserves_stems_and_uses_out_dir(
    monkeypatch: pytest.MonkeyPatch,
    xls_dir: Path,
    tmp_path: Path,
) -> None:
    _patched_converters(monkeypatch)
    files = sorted(xls_dir.rglob("*.xls"))
    out_dir = tmp_path / "modern"

    results = convert_many([str(p) for p in files], out_dir=out_dir, workers=2)

    produced_stems = sorted(r.dst.stem for r in results)
    assert produced_stems == ["a", "b", "c"]
    for stem in produced_stems:
        assert (out_dir / f"{stem}.xlsx").exists()


def test_convert_many_handles_empty_list(tmp_path: Path) -> None:
    _patched_converters(None) if False else None
    out_dir = tmp_path / "modern"
    # No fake converter needed; should not even attempt backend resolution.
    results = convert_many([], out_dir=out_dir)
    assert results == []


def test_convert_many_rejects_collision_without_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    xls_dir: Path,
    tmp_path: Path,
) -> None:
    _patched_converters(monkeypatch)
    a = xls_dir / "a.xls"
    out_dir = tmp_path / "modern"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "a.xlsx").write_bytes(b"pre-existing")

    with pytest.raises(InvalidPathError):
        convert_many([str(a)], out_dir=out_dir)


def test_convert_directory_mirrors_tree_and_preserves_root_name(
    monkeypatch: pytest.MonkeyPatch,
    xls_dir: Path,
    tmp_path: Path,
) -> None:
    """rsync-style: convert_directory(legacy/, modern/) -> modern/legacy/<files>."""
    _patched_converters(monkeypatch)
    dst = tmp_path / "modern"

    results = convert_directory(xls_dir, dst, workers=1)

    # Files end up at modern/legacy/<files> — the source folder name is preserved.
    assert sorted(r.dst.name for r in results) == ["a.xlsx", "b.xlsx", "c.xlsx"]
    assert (dst / xls_dir.name / "a.xlsx").exists()
    assert (dst / xls_dir.name / "b.xlsx").exists()
    assert (dst / xls_dir.name / "sub" / "c.xlsx").exists()
    # But not at the dst root itself.
    assert not (dst / "a.xlsx").exists()


def test_convert_directory_in_place_when_no_dst(
    monkeypatch: pytest.MonkeyPatch,
    xls_dir: Path,
) -> None:
    _patched_converters(monkeypatch)
    results = convert_directory(xls_dir, None)
    # In-place mode writes next to each source — no folder preservation needed.
    assert all(r.dst.parent == xls_dir for r in results)


def test_discover_xls_files_skips_symlinks_and_sorts(
    monkeypatch: pytest.MonkeyPatch,
    xls_dir: Path,
    tmp_path: Path,
) -> None:
    target = xls_dir / "a.xls"
    link = xls_dir / "link.xls"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this filesystem")

    discovered = discover_xls_files(xls_dir)
    rels = [rel for _abs, rel in discovered.files]
    # Symlink should be skipped.
    assert "link.xls" not in rels
    assert rels == sorted(rels)


def test_discover_xls_files_raises_on_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(InvalidPathError):
        discover_xls_files(tmp_path / "does-not-exist")


@patch("convertxls.core.REGISTRY")
def test_resolve_backend_auto_picks_first_available(
    mock_registry: object,
) -> None:
    from convertxls.core import resolve_backend

    fake_lo = type("C", (), {"name": "lo", "priority": 10, "is_available": lambda self: True})()
    fake_pd = type("C", (), {"name": "pd", "priority": 20, "is_available": lambda self: True})()
    mock_registry.available.return_value = [fake_lo, fake_pd]  # type: ignore[attr-defined]
    backend = resolve_backend()
    assert backend is fake_lo


def test_resolve_backend_raises_when_nothing_available(monkeypatch: pytest.MonkeyPatch) -> None:
    from convertxls.core import resolve_backend

    monkeypatch.setattr("convertxls.core.REGISTRY.available", lambda: [])
    with pytest.raises(NoConverterAvailableError):
        resolve_backend()
