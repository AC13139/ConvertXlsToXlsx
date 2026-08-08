"""Unit tests for ``convertxls.converters.libreoffice``."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from convertxls.converters.libreoffice import LibreOfficeConverter
from convertxls.exceptions import ConversionFailedError


def _completed_process(
    returncode: int = 0, stderr: str = "", stdout: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_is_available_when_binary_present() -> None:
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"
    converter._available_cache = None

    with patch(
        "convertxls.converters.libreoffice.subprocess.run", return_value=_completed_process()
    ):
        assert converter.is_available() is True
        assert converter.is_available() is True  # cached


def test_is_available_when_binary_missing() -> None:
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = None
    converter._available_cache = None

    with patch("convertxls.converters.libreoffice.shutil.which", return_value=None):
        assert converter.is_available() is False


def test_convert_raises_when_binary_missing(tmp_path: Path) -> None:
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = None
    converter._available_cache = False

    src = tmp_path / "in.xls"
    src.write_bytes(b"x")
    dst = tmp_path / "out.xlsx"

    with (
        patch("convertxls.converters.libreoffice.shutil.which", return_value=None),
        pytest.raises(ConversionFailedError),
    ):
        converter.convert(src, dst, overwrite=False)


def test_convert_renames_produced_file(tmp_path: Path) -> None:
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"
    converter._available_cache = True

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
    converter._binary = "/fake/soffice"
    converter._available_cache = True

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


def test_convert_hardened_flags_and_env(tmp_path: Path) -> None:
    """Regression: every invocation passes the hardened headless flags and env.

    ``SAL_USE_VCLPLUGIN=svp`` pins the headless VCL plugin and
    ``JAVA_TOOL_OPTIONS`` caps the JRE heap, both of which prevent a
    memory-starved soffice from aborting the parent process mid-conversion.
    """
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"
    converter._available_cache = True

    captured: dict[str, object] = {}

    def fake_run(argv, *args, **kwargs):
        captured["argv"] = list(argv)
        captured["env"] = kwargs.get("env")
        out_dir = Path(argv[argv.index("--outdir") + 1])
        (out_dir / "in.xlsx").write_bytes(b"produced")
        return _completed_process()

    src = tmp_path / "in.xls"
    src.write_bytes(b"x")
    dst = tmp_path / "out.xlsx"

    with patch("convertxls.converters.libreoffice.subprocess.run", side_effect=fake_run):
        converter.convert(src, dst, overwrite=False)

    argv = captured["argv"]
    assert isinstance(argv, list)
    for flag in ("--headless", "--norestore", "--nolockcheck", "--nologo", "--nofirststartwizard"):
        assert flag in argv, f"missing hardened flag {flag} in {argv!r}"
    assert "--nodefault" in argv
    env = captured["env"]
    assert isinstance(env, dict)
    assert env.get("SAL_USE_VCLPLUGIN") == "svp"
    assert env.get("JAVA_TOOL_OPTIONS") == "-Xmx512m"


def test_convert_retries_once_after_crash(tmp_path: Path) -> None:
    """Regression: a transient soffice SIGABRT (rc 134) must not kill the batch.

    A memory-starved soffice aborts with ``WrappedTargetRuntimeException`` /
    ``return_code=134``. A crashed first attempt is retried once with a fresh
    profile, which clears the vast majority of transient aborts.
    """
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"
    converter._available_cache = True

    calls = {"n": 0}

    def fake_run(argv, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _completed_process(returncode=134, stderr="Unspecified Application Error\n")
        out_dir = Path(argv[argv.index("--outdir") + 1])
        (out_dir / "in.xlsx").write_bytes(b"produced")
        return _completed_process()

    src = tmp_path / "in.xls"
    src.write_bytes(b"x")
    dst = tmp_path / "out.xlsx"

    with patch("convertxls.converters.libreoffice.subprocess.run", side_effect=fake_run):
        result = converter.convert(src, dst, overwrite=False)

    assert calls["n"] == 2  # exactly one retry
    assert result.return_code == 0
    assert dst.read_bytes() == b"produced"


def test_convert_raises_when_crash_persists(tmp_path: Path) -> None:
    """Two consecutive crashes still surface as a conversion failure."""
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"
    converter._available_cache = True

    calls = {"n": 0}

    def fake_run(argv, *args, **kwargs):
        calls["n"] += 1
        return _completed_process(returncode=134, stderr="Unspecified Application Error\n")

    src = tmp_path / "in.xls"
    src.write_bytes(b"x")
    dst = tmp_path / "out.xlsx"

    with (
        patch("convertxls.converters.libreoffice.subprocess.run", side_effect=fake_run),
        pytest.raises(ConversionFailedError) as exc_info,
    ):
        converter.convert(src, dst, overwrite=False)

    assert calls["n"] == 2  # both attempts crashed
    assert exc_info.value.return_code == 134


def test_convert_does_not_retry_deterministic_error(tmp_path: Path) -> None:
    """A normal nonzero exit (soffice reported an error) must fail fast."""
    converter = LibreOfficeConverter.__new__(LibreOfficeConverter)
    converter._binary = "/fake/soffice"
    converter._available_cache = True

    calls = {"n": 0}

    def fake_run(argv, *args, **kwargs):
        calls["n"] += 1
        return _completed_process(returncode=1, stderr="soffice said no\n")

    src = tmp_path / "in.xls"
    src.write_bytes(b"x")
    dst = tmp_path / "out.xlsx"

    with (
        patch("convertxls.converters.libreoffice.subprocess.run", side_effect=fake_run),
        pytest.raises(ConversionFailedError) as exc_info,
    ):
        converter.convert(src, dst, overwrite=False)

    assert calls["n"] == 1  # deterministic failure is not retried
    assert exc_info.value.return_code == 1
