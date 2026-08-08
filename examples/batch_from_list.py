"""Convert an explicit list of .xls files into a single output directory.

Usage:
    python examples/batch_from_list.py OUT_DIR FILE1.xls FILE2.xls [FILE3.xls ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

from convertxls import convert_many


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Usage: batch_from_list.py OUT_DIR FILE [FILE ...]",
            file=sys.stderr,
        )
        return 2

    out_dir = Path(sys.argv[1])
    files = [Path(p) for p in sys.argv[2:]]
    results = convert_many(files, out_dir=out_dir, workers=4)

    failures = 0
    for r in results:
        marker = "OK " if r.ok else "ERR"
        if not r.ok:
            failures += 1
        print(f"[{marker}] {r.backend}: {r.src} -> {r.dst} ({r.duration_ms}ms)")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
