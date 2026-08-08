"""LibreOffice headless backend — primary engine for ``.xls`` -> ``.xlsx``."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from ..exceptions import ConversionFailedError, InvalidPathError
from . import register_backend
from .base import ConversionResult, Converter


def _resolve_binary() -> str | None:
    """Locate the ``soffice`` binary, or return ``None`` if missing."""
    return shutil.which("soffice")


@register_backend
class LibreOfficeConverter(Converter):
    """Drive ``soffice --headless --convert-to xlsx`` to convert a ``.xls`` file.

    The actual filename of the output is chosen by LibreOffice — we pass an
    output *directory* and locate the produced file by stem afterwards.

    Performance note
    ----------------
    Each ``convert()`` call spawns a fresh ``soffice`` process. That is
    expensive (hundreds of ms of startup), but it is the simplest correct
    behaviour: LibreOffice headless is famously unhappy when more than one
    conversion runs concurrently *inside* the same user profile. We rely on
    a per-call profile directory (``-env:UserInstallation``) to keep parallel
    callers out of each other's way.
    """

    name = "libreoffice"
    priority = 10  # preferred when auto-selecting

    def __init__(self) -> None:
        self._binary: str | None = _resolve_binary()
        self._available_cache: bool | None = None

    def is_available(self) -> bool:
        if self._available_cache is not None:
            return self._available_cache
        binary = self._binary if self._binary is not None else _resolve_binary()
        self._binary = binary
        if binary is None:
            self._available_cache = False
            return False
        # ``soffice --version`` exits 0 even when no display is available.
        try:
            proc = subprocess.run(
                [binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            self._available_cache = False
            return False
        self._available_cache = proc.returncode == 0
        return self._available_cache

    def convert(self, src: Path, dst: Path, *, overwrite: bool) -> ConversionResult:
        if not isinstance(src, Path):
            src = Path(src)
        if not isinstance(dst, Path):
            dst = Path(dst)

        if not src.exists() or not src.is_file():
            raise InvalidPathError(f"source does not exist or is not a file: {src!s}")
        if dst.exists() and not overwrite:
            raise InvalidPathError(f"destination already exists and overwrite=False: {dst!s}")

        binary = self._binary or _resolve_binary()
        if binary is None:
            raise ConversionFailedError(
                backend=self.name,
                src=str(src),
                return_code=-1,
                stderr="soffice binary not found on PATH",
            )

        dst.parent.mkdir(parents=True, exist_ok=True)
        out_dir = dst.parent

        # Each soffice invocation gets its own user profile directory.
        # Without this, parallel calls (--workers > 1) deadlock on a shared
        # profile lock and silently return exit code 1.
        with tempfile.TemporaryDirectory(prefix="lo-profile-") as profile_dir:
            user_install = f"-env:UserInstallation=file://{profile_dir}"

            # soffice writes <src-stem>.xlsx inside --outdir; we will rename
            # if the user requested a non-default destination filename.
            proc_start = time.monotonic()
            try:
                proc = subprocess.run(
                    [
                        binary,
                        user_install,
                        "--headless",
                        "--norestore",
                        "--nolockcheck",
                        "--convert-to",
                        "xlsx",
                        "--outdir",
                        str(out_dir),
                        str(src),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ConversionFailedError(
                    backend=self.name,
                    src=str(src),
                    return_code=-1,
                    stderr=f"timeout after {exc.timeout}s",
                ) from exc
        duration_ms = int((time.monotonic() - proc_start) * 1000)

        if proc.returncode != 0:
            raise ConversionFailedError(
                backend=self.name,
                src=str(src),
                return_code=proc.returncode,
                stderr=proc.stderr,
            )

        produced = out_dir / f"{src.stem}.xlsx"
        if not produced.exists():
            raise ConversionFailedError(
                backend=self.name,
                src=str(src),
                return_code=proc.returncode,
                stderr=f"expected output not found: {produced!s}",
            )

        if produced.resolve() != dst.resolve():
            # Move the produced file to the requested destination.
            if dst.exists() and not overwrite:
                raise InvalidPathError(f"destination already exists and overwrite=False: {dst!s}")
            produced.replace(dst)

        return ConversionResult(
            src=src,
            dst=dst,
            backend=self.name,
            duration_ms=duration_ms,
            return_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )


__all__ = ["LibreOfficeConverter"]
