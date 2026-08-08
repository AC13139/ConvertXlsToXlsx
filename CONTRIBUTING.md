# Contributing to ConvertXlsToXlsx

Thanks for your interest in contributing! This document covers how to file
issues, propose changes, and set up a local development environment.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you agree to uphold it.

## Reporting Bugs

Use the [bug report issue template](.github/ISSUE_TEMPLATE/bug_report.md).
Please include:

- Your operating system and Python version (`python --version`).
- The exact command you ran and the full output, including traceback.
- A minimal `.xls` sample if the bug is reproducible (or a description of the
  document type: text-only, tables, images, embedded objects, etc.).

## Requesting Features

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).
Describe the use case first; implementation details can come later.

## Development Setup

This project uses `pyproject.toml` (PEP 621) and an editable install for
development.

```bash
# Clone your fork, then:
cd ConvertXlsToXlsx
bash scripts/dev-setup.sh
```

That installs the package in editable mode plus the dev dependencies declared
in `requirements-dev.txt`.

To run the full verification suite (lint + type-check + tests):

```bash
bash scripts/verify.sh
```

Or step by step:

```bash
make lint
make typecheck
make test
```

## Pull Requests

1. Fork the repo and create a topic branch off `main`.
2. Make focused commits. Use [Conventional Commits](https://www.conventionalcommits.org/)
   for the subject line:

   ```text
   feat: add a second converter backend for hosts without LibreOffice
   fix: preserve subfolder structure on recursive scans
   docs: clarify --overwrite semantics
   refactor: extract registry iteration into helpers
   test: cover convert_many empty-list edge case
   chore: bump ruff to 0.6
   ```

3. Update `CHANGELOG.md` under `## [Unreleased]` if the change is user-visible.
4. Ensure `bash scripts/verify.sh` passes locally.
5. Open a pull request using the
   [pull request template](.github/PULL_REQUEST_TEMPLATE.md).

## Local Git Identity (privacy)

The initial scaffold commit uses a neutral maintainer identity
(`ConvertXlsToXlsx Maintainers`) so that the very first commit author
does not leak a personal email. For your own commits, please set your
personal identity either globally (`git config --global user.email "..."`)
or per-repo (`git config user.email "..."`) before pushing.

## Coding Style

- Python 3.10+; the package declares 3.10 as the minimum.
- 4-space indentation, UTF-8, LF line endings (see `.editorconfig`).
- Formatting and import-order rules are enforced by `ruff`.
- Type hints are required on public functions. The codebase is checked with
  `mypy --strict` (config lives in `pyproject.toml`).
- Prefer small, focused functions and immutable data (`@dataclass(frozen=True)`
  for value objects).
- Tests live in `tests/unit/` and `tests/integration/`. The integration test
  is automatically skipped when `soffice` is not on `PATH`.

## Project Structure

```
src/convertxls/         # public package
  converters/           # pluggable backend registry
tests/                  # pytest suite
docs/                   # user-facing documentation
examples/               # runnable usage examples
scripts/                # developer scripts
```

## Adding a New Backend

1. Create `src/convertxls/converters/<name>.py` with a class that subclasses
   `Converter` (see `converters/base.py`).
2. Use the `@register_backend` decorator to register it.
3. Set a sensible `priority` — lower means preferred when `auto` is selected.
4. Implement `is_available()` cheaply (cache the result) and `convert()`.
5. Add a unit test in `tests/unit/test_converters_registry.py` and, if
   feasible, an integration test in `tests/integration/`.

## License

By contributing, you agree that your contributions will be licensed under the
MIT License (see [LICENSE](LICENSE)).
