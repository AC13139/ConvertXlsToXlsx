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


class _FailingConverter(_FakeConverter):
    """Fake backend that fails for a chosen source file and succeeds elsewhere."""

    def __init__(self, failing_name: str) -> None:
        super().__init__()
        self.failing_name = failing_name

    def convert(self, src: Path, dst: Path, *, overwrite: bool) -> ConversionResult:
        self.calls.append((src, dst, overwrite))
        if src.name == self.failing_name:
            from convertxls.exceptions import ConversionFailedError

            raise ConversionFailedError(
                backend=self.name, src=str(src), return_code=1, stderr="boom"
            )
        return super().convert(src, dst, overwrite=overwrite)


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


def test_discover_xls_files_skips_lock_and_temp_files(
    tmp_path: Path,
) -> None:
    """Excel owner files (``~$``) and LibreOffice lock files are not spreadsheets."""
    for name in (
        "~$book.xls",
        "~$化学知识点归纳汇总.xls",
        ".~lock.real.xls#",
        "real.xls",
    ):
        (tmp_path / name).write_bytes(b"x")

    discovered = discover_xls_files(tmp_path)
    rels = [rel for _abs, rel in discovered.files]
    assert rels == ["real.xls"]


def test_convert_directory_resumes_by_skipping_existing_outputs(
    monkeypatch: pytest.MonkeyPatch,
    xls_dir: Path,
    tmp_path: Path,
) -> None:
    """Re-running a directory scan must not fail on already-converted outputs."""
    fake = _patched_converters(monkeypatch)
    dst = tmp_path / "modern"

    # First run converts everything.
    first = convert_directory(xls_dir, dst, workers=2)
    assert len(first) == 3
    assert all(r.ok and not r.skipped for r in first)
    assert len(fake.calls) == 3

    # Second run: all outputs already exist -> everything is skipped.
    second = convert_directory(xls_dir, dst, workers=2)
    assert len(second) == 3
    assert all(r.skipped for r in second)
    assert len(fake.calls) == 3  # no new conversion attempts

    # With overwrite=True the files are re-converted instead.
    third = convert_directory(xls_dir, dst, workers=2, overwrite=True)
    assert all(r.ok and not r.skipped for r in third)
    assert len(fake.calls) == 6


def test_convert_directory_continues_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    xls_dir: Path,
    tmp_path: Path,
) -> None:
    """A failing file must not stop the rest of the batch."""
    failing = _FailingConverter("b.xls")
    monkeypatch.setattr("convertxls.core.resolve_backend", lambda name=None: failing)
    dst = tmp_path / "modern"

    results = convert_directory(xls_dir, dst, workers=2)

    by_name = {r.src.name: r for r in results}
    assert by_name["a.xls"].ok
    assert by_name["c.xls"].ok
    assert not by_name["b.xls"].ok
    assert by_name["b.xls"].return_code == 1
    assert "boom" in by_name["b.xls"].stderr
    # The other two outputs still got written.
    assert by_name["a.xls"].dst.exists()
    assert by_name["c.xls"].dst.exists()


def test_convert_many_continues_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    xls_dir: Path,
    tmp_path: Path,
) -> None:
    """convert_many also records a per-file failure instead of aborting."""
    failing = _FailingConverter("b.xls")
    monkeypatch.setattr("convertxls.core.resolve_backend", lambda name=None: failing)
    files = [str(p) for p in sorted(xls_dir.rglob("*.xls"))]
    out_dir = tmp_path / "modern"

    results = convert_many(files, out_dir=out_dir, workers=2)

    by_name = {r.src.name: r for r in results}
    assert len(results) == 3
    assert by_name["a.xls"].ok
    assert by_name["c.xls"].ok
    assert not by_name["b.xls"].ok


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
