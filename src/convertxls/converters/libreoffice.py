"""LibreOffice headless backend — primary engine for ``.xls`` -> ``.xlsx``."""

from __future__ import annotations

import os
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

    Robustness note
    ---------------
    LibreOffice can abort with a SIGABRT (e.g. ``WrappedTargetRuntimeException``)
    on a transient basis — most often when the host is under memory pressure
    and a parallel soffice/JRE process gets starved. ``soffice`` writing
    ``exit code 128+N`` (or a negative code through the launcher wrapper) is
    the tell. We run with a hardened, fully-headless invocation and retry once
    on a crash with a fresh profile, which clears the vast majority of
    transient aborts.
    """

    name = "libreoffice"
    priority = 10  # preferred when auto-selecting

    # Attempts per file. A crashed first attempt is retried once with a fresh
    # profile; deterministic failures still raise immediately.
    MAX_ATTEMPTS = 2

    def __init__(self) -> None:
        self._binary: str | None = _resolve_binary()
        self._available_cache: bool | None = None

    @staticmethod
    def _is_crash(return_code: int) -> bool:
        """True when ``soffice`` aborted rather than reported an error.

        A signal death surfaces as a negative code in ``subprocess`` (e.g.
        ``-6`` for SIGABRT) or as ``128 + signal`` when the ``soffice``
        launcher wrapper masks the signal. Codes in ``128..255`` are the
        shell-convention signal deaths.
        """
        return return_code < 0 or return_code >= 128

    @staticmethod
    def _soffice_env() -> dict[str, str]:
        """Environment for a fully-headless, memory-conservative soffice.

        ``SAL_USE_VCLPLUGIN=svp`` pins the headless VCL plugin (no GUI/Gtk
        dependencies to crash on). ``JAVA_TOOL_OPTIONS`` caps the JRE heap that
        LibreOffice spawns for documents needing Java, which prevents a
        memory-starved JVM from aborting the parent process. Both are
        ``setdefault`` so a caller-provided value always wins.
        """
        env = dict(os.environ)
        env.setdefault("SAL_USE_VCLPLUGIN", "svp")
        env.setdefault("JAVA_TOOL_OPTIONS", "-Xmx512m")
        return env

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

        # soffice writes <src-stem>.xlsx inside --outdir; we will rename
        # if the user requested a non-default destination filename.
        produced = out_dir / f"{src.stem}.xlsx"

        # Retry once on a transient abort: a crashed (or empty) first attempt
        # usually succeeds on a fresh profile. Each attempt uses its own user
        # profile directory — without that, parallel calls (--workers > 1)
        # deadlock on a shared profile lock and silently return exit code 1.
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            # Clear any stale output left by a previous crashed attempt so a
            # retry starts from a clean slate.
            produced.unlink(missing_ok=True)
            with tempfile.TemporaryDirectory(prefix="lo-profile-") as profile_dir:
                user_install = f"-env:UserInstallation=file://{profile_dir}"
                proc_start = time.monotonic()
                try:
                    proc = subprocess.run(
                        [
                            binary,
                            user_install,
                            "--headless",
                            "--norestore",
                            "--nolockcheck",
                            "--nologo",
                            "--nofirststartwizard",
                            "--nodefault",
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
                        env=self._soffice_env(),
                    )
                except subprocess.TimeoutExpired as exc:
                    raise ConversionFailedError(
                        backend=self.name,
                        src=str(src),
                        return_code=-1,
                        stderr=f"timeout after {exc.timeout}s",
                    ) from exc

            if proc.returncode == 0 and produced.exists():
                break
            crashed = self._is_crash(proc.returncode)
            if attempt < self.MAX_ATTEMPTS and (crashed or proc.returncode == 0):
                continue
            if proc.returncode != 0:
                raise ConversionFailedError(
                    backend=self.name,
                    src=str(src),
                    return_code=proc.returncode,
                    stderr=proc.stderr,
                )
            raise ConversionFailedError(
                backend=self.name,
                src=str(src),
                return_code=proc.returncode,
                stderr=f"expected output not found: {produced!s}",
            )
        duration_ms = int((time.monotonic() - proc_start) * 1000)

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
