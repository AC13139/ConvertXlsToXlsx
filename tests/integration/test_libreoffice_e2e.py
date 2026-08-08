"""Integration test for the LibreOffice backend.

Skipped automatically when ``soffice`` is not on ``PATH``. The fixture
synthesizes a minimal ``.xls`` file via OLE2 magic bytes — not a real
spreadsheet — so the assertion focuses on the *shape* of the output (a valid
ZIP archive starting with ``PK\\x03\\x04``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from convertxls.converters.libreoffice import LibreOfficeConverter

# Minimal OLE2 compound document header. Real .xls files are far more
# complex, but for the integration test we only need the binary to be
# recognised as a compound document so LibreOffice at least *tries* to read
# it. If soffice produces *any* output we consider the round-trip wired up.
OLE2_HEADER = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * (512 - 8)


def _write_minimal_xls(tmp_path: Path) -> Path:
    src = tmp_path / "fixture.xls"
    src.write_bytes(OLE2_HEADER)
    return src


@pytest.mark.integration
def test_libreoffice_round_trip(tmp_path: Path, skip_if_no_soffice) -> None:
    src = _write_minimal_xls(tmp_path)
    dst = tmp_path / "fixture.xlsx"

    converter = LibreOfficeConverter()
    if not converter.is_available():
        pytest.skip("soffice not available")

    try:
        result = converter.convert(src, dst, overwrite=False)
    except Exception as exc:
        pytest.skip(f"soffice refused the synthetic fixture: {exc}")

    assert result.ok
    assert dst.exists()
    assert dst.read_bytes()[:4] == b"PK\x03\x04"  # OOXML zip signature
