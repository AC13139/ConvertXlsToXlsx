"""Exception hierarchy for ConvertXlsToXlsx."""

from __future__ import annotations


class ConvertXlsError(Exception):
    """Base class for every error raised by this package.

    Catching this should be enough for most user code that wants to react to
    any conversion failure (missing backend, invalid paths, subprocess error,
    ...).
    """


class ConverterNotFoundError(ConvertXlsError):
    """A named backend was requested but no such backend is registered.

    Distinct from :class:`NoConverterAvailableError`, which fires when no
    installed backend can service the request at all.
    """


class NoConverterAvailableError(ConvertXlsError):
    """No backend is registered *and* installed on the host."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or (
                "No converter backend is available. Install LibreOffice "
                "and make sure its binary is on PATH. See docs/installation.md."
            )
        )


class ConversionFailedError(ConvertXlsError):
    """A backend executed but the conversion did not succeed.

    Carries the underlying backend name and return code so callers can render
    helpful error messages.
    """

    def __init__(self, backend: str, src: str, return_code: int, stderr: str = "") -> None:
        self.backend = backend
        self.src = src
        self.return_code = return_code
        self.stderr = stderr
        detail = f"backend={backend!r} src={src!r} return_code={return_code}"
        if stderr:
            detail = f"{detail} stderr={stderr!r}"
        super().__init__(f"Conversion failed: {detail}")


class InvalidPathError(ConvertXlsError):
    """A path passed in by the caller did not validate (missing, wrong type, ...)."""
