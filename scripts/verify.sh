#!/usr/bin/env bash
# Run the full verification suite: lint + type-check + unit tests.
set -euo pipefail

cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"

echo "[verify] ruff check..."
"$PY" -m ruff check src tests

echo "[verify] ruff format --check..."
"$PY" -m ruff format --check src tests

echo "[verify] mypy..."
"$PY" -m mypy src/convertxls

echo "[verify] pytest (unit)..."
"$PY" -m pytest tests/unit -v

echo "[verify] OK"
