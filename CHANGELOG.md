# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-07

### Added

- Initial public release.
- Command-line interface (`convertxls`) with three modes:
  - Single file: `convertxls FILE [--out OUT]`
  - Batch from explicit list: `convertxls FILE [FILE ...] --out-dir DIR [--workers N]`
  - Recursive directory scan: `convertxls --src-dir DIR [--dst-dir DIR] [--workers N]`
- Python API: `convert_file`, `convert_many`, `convert_directory`, `discover_xls_files`, `list_backends`.
- Pluggable converter registry with a built-in `LibreOfficeConverter`
  (priority 10; primary engine; runs `soffice --headless --convert-to xlsx`).
- Auto backend selection iterates the registry in priority order and uses the first available backend.
- `convert_directory` mirrors the source tree under `--dst-dir` preserving the
  source folder's basename (rsync `src dst/` convention).
- Parallel batch conversion via `--workers`, safe under concurrent soffice
  invocations thanks to a per-call `-env:UserInstallation` profile directory.
- Structured logging controlled by `--verbose`.
- `Dockerfile` and `.dockerignore` — a self-contained image bundling Python
  3.12 + LibreOffice Calc headless + Java + `convertxls`.
- `scripts/docker-build.sh` auto-detects `podman` or `docker`, applies a
  configurable memory cap via `CONTAINER_MEMORY`, and accepts a custom tag as
  its first argument. `--multi-arch` builds and pushes a Docker Buildx
  manifest list for `linux/amd64` and `linux/arm64`.
- `compose.yaml` runs the published multi-arch image (`ac13139/xls2xlsx:latest`)
  with `docker compose up`; source/output folders and worker count are
  configurable via `.env` (`XLS_SRC_DIR`, `XLS_OUT_DIR`, `WORKERS`).
- `make docker-build` and `make docker-run` Makefile targets.
- Initial documentation set: `README.md`, `docs/installation.md`,
  `docs/usage.md`, `docs/architecture.md`, `docs/api.md`.
- Example scripts under `examples/`.
- Unit tests covering CLI parsing, config, core orchestration, and registry;
  integration test for LibreOffice gated on `soffice` presence.

[Unreleased]: https://github.com/AC13139/ConvertXlsToXlsx/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AC13139/ConvertXlsToXlsx/releases/tag/v0.1.0
