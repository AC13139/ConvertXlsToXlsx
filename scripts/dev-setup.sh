#!/usr/bin/env bash
# Install the package in editable mode with development extras.
set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"

echo "[dev-setup] Installing package in editable mode with dev extras..."
"$PY" -m pip install -e ".[dev]"

echo "[dev-setup] Done. Run 'bash scripts/verify.sh' to confirm the install."
