"""Convert a single .xls file into .xlsx.

Usage:
    python examples/single_file.py INPUT.xls [OUTPUT.xlsx]
"""

from __future__ import annotations

import sys
from pathlib import Path

from convertxls import convert_file


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: single_file.py INPUT.xls [OUTPUT.xlsx]", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    result = convert_file(src, dst)
    print(f"Converted with {result.backend!r} in {result.duration_ms}ms")
    print(f"  src: {result.src}")
    print(f"  dst: {result.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
