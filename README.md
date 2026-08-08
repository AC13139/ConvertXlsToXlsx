# ConvertXlsToXlsx

> Convert legacy Microsoft Excel `.xls` files into the modern `.xlsx` format.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-MVP-yellow.svg)](#status--roadmap)

`ConvertXlsToXlsx` is a small, dependency-free Python utility (plus CLI) for
batch-converting legacy Microsoft Excel spreadsheets (`.xls`) into the modern
Office Open XML format (`.xlsx`). It exists because many downstream tools —
notably AI knowledgebases such as Google NotebookLM and similar products —
accept `.xlsx` (and PDF / HTML) but not legacy `.xls`.

## Why

Large archives of legacy `.xls` files — research, theses, manuals, and
institutional records — are effectively locked out of modern AI ingest
pipelines. This tool bridges that gap with a clean, scriptable interface and a
pluggable converter backend.

## Features

- **Single file** conversion from the command line or Python API.
- **Two batch modes**:
  - Explicit file list (`convert_many`) — different files picked by the user.
  - Recursive directory walk (`convert_directory`) — directory tree mirrored under `dst_dir/<source_folder_name>/` (rsync-style).
- **Pluggable backend registry** with a single built-in engine:
  - `LibreOfficeConverter` — uses `soffice --headless --convert-to xlsx`.
- **Parallel processing** with configurable worker count; per-call soffice
  user-profile isolation keeps concurrent runs from deadlocking.
- **Zero runtime dependencies** — pure Python standard library plus a
  LibreOffice binary on `PATH`.
- **MIT licensed**, ready for public release.

## Installation

You need Python 3.10 or newer and a LibreOffice binary on `PATH`.

### Option 1 — pip install (recommended)

```bash
# 1. Install LibreOffice
#    Linux:   sudo apt install libreoffice
#    macOS:   brew install --cask libreoffice
#    Windows: choco install libreoffice

# 2. Install ConvertXlsToXlsx
pip install convertxls
```

### Option 2 — Docker (no local install needed)

If you want a self-contained environment that doesn't touch your host
system, use the project's `Dockerfile`:

```bash
# Build the image (~280 MB compressed)
docker build -t convertxls .

# Convert a single folder
docker run --rm \
    -v /path/to/legacy:/data \
    -v /path/to/modern:/out \
    convertxls --src-dir /data --dst-dir /out --workers 4

# Or with podman (rootless, no daemon)
podman run --rm \
    -v /path/to/legacy:/data \
    -v /path/to/modern:/out \
    convertxls --src-dir /data --dst-dir /out --workers 4
```

The image bundles Python 3.12, LibreOffice, and `convertxls` — nothing
else to install. Recommended for CI runners and one-off batch jobs.
Multi-arch: the image supports `linux/amd64` and `linux/arm64`, and
`bash scripts/docker-build.sh --multi-arch` builds and pushes a manifest
list for both via Docker Buildx.

Or run the published image with Docker Compose — no build needed:

```bash
cp .env.example .env   # point XLS_SRC_DIR / XLS_OUT_DIR at your folders
docker compose up      # converts ./docs -> ./out with 4 workers
```

For local development from a checkout:

```bash
git clone https://github.com/AC13139/ConvertXlsToXlsx.git
cd ConvertXlsToXlsx
bash scripts/dev-setup.sh
```

## Quickstart

### Command line

```bash
# Single file — writes <stem>.xlsx next to the source
convertxls report.xls

# Single file with explicit output
convertxls report.xls --out report.xlsx

# Batch from an explicit list of files
convertxls file1.xls file2.xls file3.xls --out-dir modern/

# Batch via glob (shell-expanded)
convertxls notes/*.xls --out-dir modern/

# Recursive folder scan — mirrors the tree under modern/legacy/ (rsync-style)
convertxls --src-dir legacy/ --dst-dir modern/

# Parallelism
convertxls --src-dir legacy/ --dst-dir modern/ --workers 8

# Pick a specific backend
convertxls report.xls --backend libreoffice

# See available backends
convertxls --list-backends

# Verbose logging
convertxls report.xls --verbose
```

### Python API

```python
from convertxls import (
    convert_file,
    convert_many,
    convert_directory,
    list_backends,
)

# Single file
convert_file("report.xls", "report.xlsx")

# Explicit batch
results = convert_many(
    ["a.xls", "b.xls", "c.xls"],
    out_dir="modern/",
    backend="auto",
    workers=4,
)
for r in results:
    print(r.dst, "->", r.return_code)

# Recursive directory walk
results = convert_directory(
    src_dir="legacy/",
    dst_dir="modern/",
    backend="auto",
    workers=4,
)
# Output lives at modern/legacy/<original tree>.

# Introspection
print(list_backends())  # -> ["libreoffice"]
print(available_backends())  # backends whose binary is ready to use
```

## Documentation

- [Installation](docs/installation.md) — per-OS setup, plus the Docker recipe.
- [Usage](docs/usage.md) — full CLI reference and Python API examples.
- [Architecture](docs/architecture.md) — the registry pattern, backend contract, and selection logic.
- [API reference](docs/api.md) — generated-style doc of the public Python surface.
- [Examples](examples/) — runnable scripts.

## Project Status & Roadmap

This is **0.1.0** — a working MVP. Backwards-incompatible changes are still
possible before 1.0.

| Version | Status | Notes |
|---------|--------|-------|
| 0.1.x   | MVP    | CLI + Python API, LibreOffice backend, tests, docs, Docker + multi-arch + publish workflow. |
| 0.2.x   | Planned | Real-file integration tests, PyPI publication. |
| 1.0.0   | Future | First stable API guarantee. |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports and feature requests
should use the [issue templates](.github/ISSUE_TEMPLATE/).

## License

[MIT](LICENSE) — Copyright (c) 2026 ConvertXlsToXlsx contributors.
