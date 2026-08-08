"""Command-line entry point for ``convertxls``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .config import DEFAULT_BACKEND, DEFAULT_WORKERS
from .converters import REGISTRY
from .core import (
    convert_directory,
    convert_file,
    convert_many,
)
from .exceptions import ConvertXlsError
from .logging_setup import configure_logging

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_CONVERSION = 1


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Exposed for tests so they can introspect the parser without running
    ``main()``.
    """
    parser = argparse.ArgumentParser(
        prog="convertxls",
        description=(
            "Convert legacy Microsoft Excel .xls files into the modern "
            ".xlsx format. Supports single files, explicit batch lists, and "
            "recursive directory scans."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="One or more .xls files. Combined with --out-dir this becomes "
        "an explicit batch; with a single positional it is single-file mode.",
    )
    parser.add_argument(
        "--out",
        help="Output path for single-file mode. Default: <stem>.xlsx next to source.",
    )
    parser.add_argument(
        "--out-dir",
        help="Output directory for batch mode (explicit list). Default: directory of first file.",
    )
    parser.add_argument(
        "--src-dir",
        help="Source directory for recursive scan mode.",
    )
    parser.add_argument(
        "--dst-dir",
        help="Destination directory for recursive scan mode. Default: next to each source.",
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        help=f"Backend name or 'auto' (default: {DEFAULT_BACKEND}).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Parallel workers for batch mode (default: {DEFAULT_WORKERS}).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing destination files (default: refuse).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="Print registered backends and exit.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> str | None:
    """Validate the parsed arguments and return an error message, or ``None``.

    Returns the error string on failure (the caller prints it and exits with
    :data:`EXIT_USAGE`); returns ``None`` when the args look fine.
    """
    has_positional = bool(args.files)
    has_src_dir = bool(args.src_dir)
    if has_positional and has_src_dir:
        return "Cannot combine positional FILE arguments with --src-dir."
    if has_src_dir and args.dst_dir is not None and args.out_dir is not None:
        return "--dst-dir and --out-dir cannot be combined; --out-dir is for batch-from-list mode."
    if args.workers < 1:
        return f"--workers must be >= 1, got {args.workers}"
    if not has_positional and not has_src_dir and not (args.list_backends or args.version):
        return "No input provided. Pass FILE arguments or --src-dir, or use --list-backends / --version."
    return None


def _print_list_backends() -> None:
    infos = REGISTRY.info()
    if not infos:
        print("No converter backends are registered.")
        return
    for info in infos:
        marker = "available" if info.available else "missing"
        print(f"{info.name}\tpriority={info.priority}\t{marker}")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"convertxls {__version__}")
        return EXIT_OK

    if args.list_backends:
        _print_list_backends()
        return EXIT_OK

    error = _validate_args(args)
    if error is not None:
        parser.error(error)  # exits with code 2
        return EXIT_USAGE  # unreachable, kept for type-checkers

    configure_logging(verbose=args.verbose)

    try:
        # Recursive directory scan mode
        if args.src_dir:
            results = convert_directory(
                args.src_dir,
                args.dst_dir,
                backend=args.backend,
                overwrite=args.overwrite,
                workers=args.workers,
                verbose=args.verbose,
            )
            failures = [r for r in results if not r.ok]
            for r in results:
                print(f"{r.backend}\t{r.src}\t->\t{r.dst}\t{r.duration_ms}ms")
            return EXIT_OK if not failures else EXIT_CONVERSION

        # Single-file mode (one positional, no --out-dir)
        if len(args.files) == 1 and args.out_dir is None:
            result = convert_file(
                args.files[0],
                args.out,
                backend=args.backend,
                overwrite=args.overwrite,
                verbose=args.verbose,
            )
            print(f"{result.backend}\t{result.src}\t->\t{result.dst}\t{result.duration_ms}ms")
            return EXIT_OK

        # Batch-from-list mode (one or more positionals + --out-dir)
        out_dir = args.out_dir
        if out_dir is None:
            # Fall back to the directory of the first input.
            out_dir = str(Path(args.files[0]).resolve().parent)

        results = convert_many(
            args.files,
            out_dir=out_dir,
            backend=args.backend,
            overwrite=args.overwrite,
            workers=args.workers,
            verbose=args.verbose,
        )
        failures = [r for r in results if not r.ok]
        for r in results:
            print(f"{r.backend}\t{r.src}\t->\t{r.dst}\t{r.duration_ms}ms")
        return EXIT_OK if not failures else EXIT_CONVERSION

    except ConvertXlsError as exc:
        print(f"convertxls: {exc}", file=sys.stderr)
        return EXIT_CONVERSION


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
