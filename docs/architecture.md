# Architecture

## Overview

`ConvertXlsToXlsx` is a thin wrapper around one or more external converter
binaries (LibreOffice). The Python package does not parse
documents itself — it dispatches the work to the most appropriate backend.

```
                       ┌──────────────────────┐
                       │     CLI / Python     │
                       │       entry point    │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │  core.convert_*()    │
                       │ (orchestration only) │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │      Registry        │
                       │ (priority-ordered)   │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   LibreOffice        │
                       │   Converter          │
                       │   (priority 10)      │
                       └──────────────────────┘
                                  │
                                  ▼
                            soffice CLI
```

The registry is pluggable — third-party backends (e.g. a COM-based
backend on Windows, or a commercial Aspose adapter) can register
themselves without touching core code. As of 0.1.x, LibreOffice is the
only shipped backend because it is the only open-source engine that
can read legacy `.xls` files in 2026.

## Why pluggable backends?

Adding a new converter should not require editing core code. The package
defines a `Converter` abstract base class with two methods:

- `is_available() -> bool` — does the binary exist and run?
- `convert(src, dst, *, overwrite) -> ConversionResult` — run it.

New backends register themselves with a single `@register_backend`
decorator. The registry exposes:

- `available_backends()` — backends whose binary is on `PATH`.
- `backend_info()` — a snapshot of every registered backend.

When the user requests `backend="auto"`, the registry is scanned in
priority order and the first available backend wins.

## Why is LibreOffice the primary engine?

LibreOffice renders `.xls` files faithfully, especially
when the source uses complex formatting, embedded objects, or legacy
fields. The trade-off is speed: each LibreOffice call pays a
~hundreds-of-milliseconds cold-start cost, because LibreOffice headless is
notoriously unhappy running multiple conversions inside the same user
profile.

`convertxls` keeps parallel calls safe by:

- Using a `ThreadPoolExecutor` for batch dispatch.
- Asking each converter to write to a per-call output directory (so files
  do not race).
- Letting the user cap parallelism with `--workers`.

## Directory mirroring

Recursive scans reproduce the input tree under the destination directory, with the source folder's own name preserved as the top-level directory (rsync-style):

```
legacy/reports/2020/q1.xls  ──►  modern/legacy/reports/2020/q1.xlsx
legacy/reports/2021/q2.xls  ──►  modern/legacy/reports/2021/q2.xlsx
legacy/misc/note.xls        ──►  modern/legacy/misc/note.xlsx
```

`_ensure_within()` checks every produced path against the destination root
to prevent path traversal when the input tree contains oddly named files.

## Discovery rules

- Files matched by suffix `.xls` (case-insensitive).
- Files ending in `.xlsx` are excluded even when they look like `.xls`.
- Symlinks are not followed (reproducibility + safety).
- Results are lex-sorted so output order is stable across runs.

## Failure handling

Every public function returns either a single `ConversionResult` or a
`list[ConversionResult]`. The conversion always runs regardless of prior
failures — callers can iterate the full list and decide what to do.

A failed conversion raises `ConversionFailedError` carrying `backend`,
`src`, `return_code`, and `stderr`. Batch callers may either:

- Let the exception propagate (one failure aborts the batch), or
- Wrap each call in a try/except and accumulate their own results.

The CLI chooses the former: a non-zero exit code reflects at least one
per-file failure.
