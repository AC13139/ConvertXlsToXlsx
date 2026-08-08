# Usage

## Command-line interface

```text
convertxls [OPTIONS] [FILE ...]
```

### Modes

| Mode | Invocation | Output |
|------|-----------|--------|
| Single file | `convertxls FILE` | `<stem>.xlsx` next to source, or `--out OUT` |
| Single file with explicit output | `convertxls FILE --out OUT` | `OUT` |
| Batch (explicit list) | `convertxls FILE [FILE ...] --out-dir DIR` | `<stem>.xlsx` under `DIR` |
| Batch (glob) | `convertxls notes/*.xls --out-dir modern/` | same as above |
| Recursive scan | `convertxls --src-dir DIR [--dst-dir DIR]` | source tree mirrored under `DIR/<src_folder_name>/` (rsync-style), or alongside source |
| Introspection | `convertxls --list-backends` | one line per backend |
| Version | `convertxls --version` | package version |

### Common flags

- `--backend NAME` — pick a backend explicitly (default: `auto`).
- `--overwrite` — overwrite existing destination files (default: refuse).
- `--workers N` — parallel workers for batch operations (default: 4).
- `--verbose` — debug logging to stderr.

### Examples

```bash
# Convert a single file, writing beside the source.
convertxls report.xls

# Convert a single file to a specific path.
convertxls report.xls --out modern/report.xlsx

# Convert several files picked by the user.
convertxls chapter1.xls chapter2.xls chapter3.xls --out-dir modern/

# Recursive scan — mirrors the directory tree.
convertxls --src-dir legacy/ --dst-dir modern/ --workers 8

# Pick the LibreOffice backend explicitly.
convertxls report.xls --backend libreoffice
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0    | All conversions succeeded. |
| 1    | One or more conversions failed (per-file conversion error). |
| 2    | Invalid CLI usage (conflicting flags, missing input, ...). |

### Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `CONVERTXLS_LOG_LEVEL` | Set logging level (`DEBUG`, `INFO`, `WARNING`). | `INFO` (`--verbose` overrides to `DEBUG`). |

(No environment variable is required — the tool makes no network calls and
stores no global state.)

## Python API

```python
from convertxls import (
    convert_file,
    convert_many,
    convert_directory,
    list_backends,
    available_backends,
)
```

### Single file

```python
from convertxls import convert_file

convert_file("report.xls", "report.xlsx")
```

### Explicit batch

```python
from convertxls import convert_many

results = convert_many(
    ["a.xls", "b.xls", "c.xls"],
    out_dir="modern/",
    backend="auto",
    workers=4,
)
for r in results:
    print(r.dst, "ok" if r.ok else "FAILED")
```

### Recursive directory scan

```python
from convertxls import convert_directory

results = convert_directory(
    src_dir="legacy/",
    dst_dir="modern/",
    backend="auto",
    workers=4,
)
```

### Introspection

```python
print(list_backends())       # ["libreoffice"]
print(available_backends())  # backends whose binary is ready to use
```

### Backend selection

LibreOffice is the only supported backend as of 0.1.x. The CLI flag
`--backend NAME` is accepted for forward compatibility but in practice
must be `libreoffice` (or omitted, which is equivalent to `auto`).

### Error handling

All public functions raise a subclass of `convertxls.ConvertXlsError`:

- `convertxls.ConverterNotFoundError` — backend name is not registered.
- `convertxls.NoConverterAvailableError` — no backend is installed.
- `convertxls.ConversionFailedError` — a backend ran but the conversion failed.
- `convertxls.InvalidPathError` — a path passed in by the caller was invalid.

Catch `ConvertXlsError` to handle every error uniformly.
