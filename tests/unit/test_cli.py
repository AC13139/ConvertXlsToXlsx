"""Unit tests for ``convertxls.cli``."""

from __future__ import annotations

from pathlib import Path

import pytest

from convertxls import __version__
from convertxls.cli import EXIT_OK, build_parser, main


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    build_parser()  # smoke check — exposed for introspection
    rc = main(["--version"])
    captured = capsys.readouterr()
    assert rc == EXIT_OK
    assert captured.out.strip() == f"convertxls {__version__}"


def test_list_backends(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--list-backends"])
    captured = capsys.readouterr()
    assert rc == EXIT_OK
    # Built-in backend should be listed.
    assert "libreoffice" in captured.out


def test_conflict_between_positional_and_src_dir(tmp_xls: Path) -> None:
    with pytest.raises(SystemExit):
        main([str(tmp_xls), "--src-dir", "legacy"])


def test_no_input_is_usage_error() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_single_file_mode_invokes_convert_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_xls: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    called = {}

    def fake_convert_file(src, dst=None, *, backend="auto", overwrite=False, verbose=False):
        called["src"] = src
        called["dst"] = dst
        called["backend"] = backend
        called["overwrite"] = overwrite
        captured_src = Path(src)
        captured_dst = Path(dst) if dst else captured_src.with_suffix(".xlsx")

        class _Result:
            backend = "libreoffice"
            src = captured_src
            dst = captured_dst
            duration_ms = 12

        return _Result()

    monkeypatch.setattr("convertxls.cli.convert_file", fake_convert_file)

    rc = main([str(tmp_xls)])
    assert rc == EXIT_OK
    assert called["src"] == str(tmp_xls)
    assert called["dst"] is None
    captured = capsys.readouterr()
    assert str(tmp_xls) in captured.out


def test_batch_mode_requires_out_dir_or_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    a = tmp_path / "a.xls"
    a.write_bytes(b"a")
    captured_kwargs: dict[str, object] = {}

    def fake_convert_many(
        files, *, out_dir, backend="auto", overwrite=False, workers=4, verbose=False
    ):
        captured_kwargs["files"] = list(files)
        captured_kwargs["out_dir"] = out_dir

        class _Result:
            backend = "libreoffice"
            src = Path(files[0])
            dst = Path(out_dir) / (Path(files[0]).stem + ".xlsx")
            duration_ms = 5
            ok = True
            return_code = 0

        return [_Result()]

    monkeypatch.setattr("convertxls.cli.convert_many", fake_convert_many)

    out_dir = tmp_path / "modern"
    rc = main([str(a), "--out-dir", str(out_dir)])
    assert rc == EXIT_OK
    assert captured_kwargs["out_dir"] == str(out_dir)


def test_directory_mode_invokes_convert_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}

    def fake_convert_directory(src_dir, dst_dir=None, **kwargs):
        captured_kwargs["src_dir"] = src_dir
        captured_kwargs["dst_dir"] = dst_dir
        return []

    monkeypatch.setattr("convertxls.cli.convert_directory", fake_convert_directory)

    src = tmp_path / "legacy"
    src.mkdir()
    rc = main(["--src-dir", str(src)])
    assert rc == EXIT_OK
    assert captured_kwargs["src_dir"] == str(src)
    assert captured_kwargs["dst_dir"] is None


def test_help_exits_clean(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "usage:" in captured.err.lower()
