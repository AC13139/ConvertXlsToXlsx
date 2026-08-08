"""Recursively convert every .xls file under a source directory.

Usage:
    python examples/batch_directory.py SRC_DIR [DST_DIR]
"""

from __future__ import annotations

import sys
from pathlib import Path

from convertxls import convert_directory


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: batch_directory.py SRC_DIR [DST_DIR]", file=sys.stderr)
        return 2

    src_dir = Path(sys.argv[1])
    dst_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    results = convert_directory(src_dir, dst_dir, workers=4)
    failures = sum(1 for r in results if not r.ok)

    for r in results:
        marker = "OK " if r.ok else "ERR"
        print(f"[{marker}] {r.backend}: {r.src} -> {r.dst} ({r.duration_ms}ms)")

    print(f"\n{len(results)} file(s) processed, {failures} failure(s).")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
