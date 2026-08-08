"""Public orchestration API: ``convert_file``, ``convert_many``,
``convert_directory`` and the helper ``resolve_backend``.

The CLI is a thin wrapper over this module — every behaviour the CLI
exposes should be expressible as a single call into :mod:`convertxls.core`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .config import (
    DEFAULT_BACKEND,
    DEFAULT_WORKERS,
    DiscoveryResult,
)
from .converters import REGISTRY, ConversionResult, Converter
from .exceptions import (
    InvalidPathError,
    NoConverterAvailableError,
)
from .logging_setup import get_logger

_LOGGER = get_logger()

XLS_SUFFIXES: tuple[str, ...] = (".xls",)


def _coerce_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def _ensure_xls(path: Path) -> None:
    if path.suffix.lower() not in XLS_SUFFIXES:
        raise InvalidPathError(f"expected a .xls input file, got suffix {path.suffix!r}: {path!s}")


def _ensure_within(parent: Path, candidate: Path) -> None:
    """Raise if ``candidate`` resolves outside ``parent`` after symlink resolution."""
    try:
        candidate.relative_to(parent)
    except ValueError as exc:
        raise InvalidPathError(
            f"destination {candidate!s} escapes the dst_dir root {parent!s}"
        ) from exc


def resolve_backend(name: str | None = None) -> Converter:
    """Return the backend to use for a request.

    ``name`` may be:

    - ``None`` or ``"auto"`` — pick the first *available* backend in
      priority order.
    - any other string — look up the registered backend by that name. A
      backend is selected even when its binary is missing; the caller is
      responsible for handling :meth:`Converter.is_available` failures.

    Raises
    ------
    NoConverterAvailableError
        When ``name`` is ``"auto"`` and no backend is available.
    """
    if name is None or name == "auto":
        available = REGISTRY.available()
        if not available:
            raise NoConverterAvailableError()
        return available[0]
    return REGISTRY.get(name)


# ---------------------------------------------------------------------------
# Single file
# ---------------------------------------------------------------------------


def convert_file(
    src: str | Path,
    dst: str | Path | None = None,
    *,
    backend: str = DEFAULT_BACKEND,
    overwrite: bool = False,
    verbose: bool = False,
) -> ConversionResult:
    """Convert a single ``.xls`` file into ``.xlsx``.

    Parameters
    ----------
    src:
        Path to the input ``.xls`` file.
    dst:
        Destination path. When ``None``, the result is written next to the
        source as ``<stem>.xlsx``.
    backend:
        Backend name (e.g. ``"libreoffice"``) or ``"auto"``.
    overwrite:
        If ``False`` (default) and ``dst`` already exists, raise
        :class:`InvalidPathError`.
    verbose:
        Enable debug logging.
    """
    if verbose:
        _LOGGER.debug("convert_file: src=%s dst=%s backend=%s", src, dst, backend)

    src_path = _coerce_path(src)
    _ensure_xls(src_path)
    if not src_path.exists():
        raise InvalidPathError(f"source does not exist: {src_path!s}")

    dst_path = _coerce_path(dst) if dst is not None else src_path.with_suffix(".xlsx")
    if dst_path.suffix.lower() != ".xlsx":
        # LibreOffice produces .xlsx — assert it.
        dst_path = dst_path.with_suffix(".xlsx")

    converter = resolve_backend(backend)
    if not converter.is_available():
        raise NoConverterAvailableError(
            f"Requested backend {converter.name!r} is not available on this host."
        )
    return converter.convert(src_path, dst_path, overwrite=overwrite)


# ---------------------------------------------------------------------------
# Batch — explicit list
# ---------------------------------------------------------------------------


def convert_many(
    files: Sequence[str | Path],
    *,
    out_dir: str | Path,
    backend: str = DEFAULT_BACKEND,
    overwrite: bool = False,
    workers: int = DEFAULT_WORKERS,
    verbose: bool = False,
) -> list[ConversionResult]:
    """Convert an explicit list of ``.xls`` files into ``out_dir``.

    All output files keep their original stem and land in the same flat
    ``out_dir``. Filename collisions raise :class:`InvalidPathError` unless
    ``overwrite`` is ``True``.

    Parameters mirror :func:`convert_file`; ``workers`` controls parallelism
    (set to 1 for sequential execution).
    """
    if not files:
        return []

    out_dir_path = _coerce_path(out_dir).resolve()
    out_dir_path.mkdir(parents=True, exist_ok=True)

    src_paths: list[Path] = []
    for raw in files:
        p = _coerce_path(raw)
        _ensure_xls(p)
        if not p.exists():
            raise InvalidPathError(f"source does not exist: {p!s}")
        src_paths.append(p)

    converter = resolve_backend(backend)
    if not converter.is_available():
        raise NoConverterAvailableError(
            f"Requested backend {converter.name!r} is not available on this host."
        )

    def _resolve_destination(src: Path) -> Path:
        target = out_dir_path / f"{src.stem}.xlsx"
        if target.exists() and not overwrite:
            raise InvalidPathError(f"destination already exists and overwrite=False: {target!s}")
        return target

    if workers <= 1:
        results: list[ConversionResult] = []
        for src in src_paths:
            dst = _resolve_destination(src)
            results.append(converter.convert(src, dst, overwrite=overwrite))
        return results

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_src = {
            pool.submit(converter.convert, src, _resolve_destination(src), overwrite=overwrite): src
            for src in src_paths
        }
        for fut in as_completed(future_to_src):
            results.append(fut.result())
    return results


# ---------------------------------------------------------------------------
# Batch — recursive directory walk
# ---------------------------------------------------------------------------


def discover_xls_files(src_dir: str | Path) -> DiscoveryResult:
    """Walk ``src_dir`` and return every ``.xls`` file (case-insensitive).

    Symlinks are *not* followed, and the result is lex-sorted for
    reproducibility. ``.xlsx`` files are excluded even when named with a
    ``.xls`` suffix.
    """
    root = _coerce_path(src_dir).resolve()
    if not root.exists() or not root.is_dir():
        raise InvalidPathError(f"src_dir is not an existing directory: {root!s}")

    found: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() != ".xls":
            continue
        # Defence in depth — never pick up .xlsx via a weird suffix
        if path.name.lower().endswith(".xlsx"):
            continue
        rel = path.relative_to(root).as_posix()
        found.append((str(path), rel))
    return DiscoveryResult(src_dir=str(root), files=tuple(found))


def convert_directory(
    src_dir: str | Path,
    dst_dir: str | Path | None = None,
    *,
    backend: str = DEFAULT_BACKEND,
    overwrite: bool = False,
    workers: int = DEFAULT_WORKERS,
    verbose: bool = False,
) -> list[ConversionResult]:
    """Recursively convert every ``.xls`` file under ``src_dir``.

    The directory tree is mirrored under ``dst_dir`` with the source
    folder's own name preserved — matching the ``rsync src dst/`` convention:

    ``legacy/reports/2020/q1.xls`` -> ``modern/legacy/reports/2020/q1.xlsx``

    When ``dst_dir`` is ``None`` each output is written next to its source
    (no folder-name preservation, since the source folder is the destination).
    """
    if verbose:
        _LOGGER.debug("convert_directory: src=%s dst=%s", src_dir, dst_dir)

    src_root = _coerce_path(src_dir).resolve()
    if not src_root.exists() or not src_root.is_dir():
        raise InvalidPathError(f"src_dir is not an existing directory: {src_root!s}")

    discovered = discover_xls_files(src_root)
    if not discovered.files:
        return []

    if dst_dir is None:
        return convert_many(
            [Path(abs_path) for abs_path, _ in discovered.files],
            out_dir=src_root,
            backend=backend,
            overwrite=overwrite,
            workers=workers,
            verbose=verbose,
        )

    # Mirror the source tree under ``dst_dir`` with the source folder's
    # basename preserved as the top-level directory — same as ``rsync src dst/``.
    dst_root = (_coerce_path(dst_dir) / src_root.name).resolve()
    dst_root.mkdir(parents=True, exist_ok=True)

    converter = resolve_backend(backend)
    if not converter.is_available():
        raise NoConverterAvailableError(
            f"Requested backend {converter.name!r} is not available on this host."
        )

    def _convert_one(abs_path: str, rel_path: str) -> ConversionResult:
        src = Path(abs_path)
        target_dir = (dst_root / Path(rel_path).parent).resolve()
        _ensure_within(dst_root, target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        dst = target_dir / f"{src.stem}.xlsx"
        if dst.exists() and not overwrite:
            raise InvalidPathError(f"destination already exists and overwrite=False: {dst!s}")
        return converter.convert(src, dst, overwrite=overwrite)

    if workers <= 1:
        return [_convert_one(abs_path, rel_path) for abs_path, rel_path in discovered.files]

    results: list[ConversionResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_src = {
            pool.submit(_convert_one, abs_path, rel_path): abs_path
            for abs_path, rel_path in discovered.files
        }
        for fut in as_completed(future_to_src):
            results.append(fut.result())
    return results


__all__ = [
    "convert_directory",
    "convert_file",
    "convert_many",
    "discover_xls_files",
    "resolve_backend",
]


def _check_types() -> None:  # pragma: no cover - defensive
    """Lightweight runtime check used by the test suite to detect import cycles."""
    _: Iterable[ConversionResult] = []
