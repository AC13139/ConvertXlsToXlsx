"""Unit tests for ``convertxls.converters.libreoffice``."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from convertxls.converters.libreoffice import LibreOfficeConverter


def _completed_process(
    returncode: int = 0, stderr: str = "", stdout: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_is_available_when_binary_present() -> None:
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"  # type: ignore[attr-defined]
    converter._available_cache = None  # type: ignore[attr-defined]

    with patch(
        "convertxls.converters.libreoffice.subprocess.run", return_value=_completed_process()
    ):
        assert converter.is_available() is True
        assert converter.is_available() is True  # cached


def test_is_available_when_binary_missing() -> None:
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = None  # type: ignore[attr-defined]
    converter._available_cache = None  # type: ignore[attr-defined]

    with patch("convertxls.converters.libreoffice.shutil.which", return_value=None):
        assert converter.is_available() is False


def test_convert_raises_when_binary_missing(tmp_path: Path) -> None:
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = None  # type: ignore[attr-defined]
    converter._available_cache = False  # type: ignore[attr-defined]

    src = tmp_path / "in.xls"
    src.write_bytes(b"x")
    dst = tmp_path / "out.xlsx"

    with patch("convertxls.converters.libreoffice.shutil.which", return_value=None):
        from convertxls.exceptions import ConversionFailedError

        with pytest.raises(ConversionFailedError):
            converter.convert(src, dst, overwrite=False)


def test_convert_renames_produced_file(tmp_path: Path) -> None:
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"  # type: ignore[attr-defined]
    converter._available_cache = True  # type: ignore[attr-defined]

    src = tmp_path / "in.xls"
    src.write_bytes(b"x")
    dst = tmp_path / "renamed.xlsx"

    def fake_run(argv, *args, **kwargs):
        # Pretend soffice wrote <src.stem>.xlsx into --outdir.
        out_dir = Path(argv[argv.index("--outdir") + 1])
        (out_dir / "in.xlsx").write_bytes(b"produced")
        return _completed_process()

    with patch("convertxls.converters.libreoffice.subprocess.run", side_effect=fake_run):
        result = converter.convert(src, dst, overwrite=False)

    assert result.dst == dst
    assert dst.exists()
    assert dst.read_bytes() == b"produced"


def test_convert_passes_per_call_user_installation(tmp_path: Path) -> None:
    """Regression: parallel soffice calls must use isolated profile dirs.

    Without ``-env:UserInstallation=file://<unique>`` the second parallel
    call would deadlock on the shared default profile and silently return
    exit code 1. Every ``convert()`` invocation must pass its own profile.
    """
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"  # type: ignore[attr-defined]
    converter._available_cache = True  # type: ignore[attr-defined]

    captured_argv: list[list[str]] = []

    def fake_run(argv, *args, **kwargs):
        captured_argv.append(list(argv))
        out_dir = Path(argv[argv.index("--outdir") + 1])
        (out_dir / "in.xlsx").write_bytes(b"x")
        return _completed_process()

    src = tmp_path / "in.xls"
    src.write_bytes(b"x")
    dst = tmp_path / "out.xlsx"

    with patch("convertxls.converters.libreoffice.subprocess.run", side_effect=fake_run):
        converter.convert(src, dst, overwrite=False)
        converter.convert(src, dst, overwrite=True)

    assert len(captured_argv) == 2
    for argv in captured_argv:
        user_install = next((a for a in argv if a.startswith("-env:UserInstallation=")), None)
        assert user_install is not None, f"missing -env:UserInstallation in {argv!r}"
        # Profile dir must point to a real path inside the per-call temp dir.
        assert user_install.startswith("-env:UserInstallation=file://")
    # And the two profile dirs must be different.
    profiles = [a for argv in captured_argv for a in argv if a.startswith("-env:UserInstallation=")]
    assert profiles[0] != profiles[1]
