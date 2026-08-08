# Installation

`ConvertXlsToXlsx` is pure Python — the package itself ships with no
third-party runtime dependencies. You still need a LibreOffice binary on
`PATH` for the actual `.xls → .xlsx` work.

## 1. Pick a converter backend

LibreOffice is the only supported backend as of 0.1.x. The registry pattern
leaves room for additional backends later, but today LibreOffice is the only
engine that can faithfully read legacy `.xls` files.

| Backend          | Quality | Speed     | License           | Notes |
|------------------|---------|-----------|-------------------|-------|
| LibreOffice      | High    | Slow (~1s/launch) | MPL-2.0     | The only viable open-source engine for `.xls → .xlsx` in 2026. |

If you need to ship ConvertXlsToXlsx to hosts without LibreOffice
installed, use the Docker recipe at the bottom of this page — it
self-installs LibreOffice inside a container.

## 2. Install LibreOffice

=== "Linux (Debian / Ubuntu)"

    ```bash
    sudo apt update
    sudo apt install -y libreoffice
    ```

=== "Linux (Fedora)"

    ```bash
    sudo dnf install -y libreoffice
    ```

=== "macOS"

    ```bash
    brew install --cask libreoffice
    ```

=== "Windows (Chocolatey)"

    ```powershell
    choco install libreoffice
    ```

Verify:

```bash
soffice --version
```

## 3. Install ConvertXlsToXlsx

### From PyPI (when published)

```bash
pip install convertxls
```

### From a local checkout (development)

```bash
git clone https://github.com/AC13139/ConvertXlsToXlsx.git
cd ConvertXlsToXlsx
bash scripts/dev-setup.sh
```

`scripts/dev-setup.sh` runs `pip install -e ".[dev]"`, which installs the
package in editable mode plus the development extras (`pytest`, `ruff`,
`mypy`, `coverage`).

## 4. Sanity-check the install

```bash
convertxls --version
convertxls --list-backends
```

You should see:

```text
libreoffice   priority=10  available
```

If `libreoffice` shows `missing`, install the package as described above
and ensure `soffice` (Linux/macOS) or `soffice.exe` (Windows) is on `PATH`.

## 5. Docker (alternative)

If you want a self-contained environment that doesn't touch the host
system — useful for CI runners, batch jobs, or hosts where you can't
install system packages — the project ships a `Dockerfile`.

### Build

```bash
# Default: build from the local source tree.
docker build -t convertxls .

# Or use the Makefile target.
make docker-build
```

The image is based on `python:3.12-slim` plus `libreoffice-calc`,
`libreoffice-java-common`, and `default-jre-headless`. Final size is
~280 MB compressed, ~700 MB uncompressed.

### Run

```bash
# Recursive directory scan, source tree mirrored under out/<src_name>/.
docker run --rm \
    -v /path/to/legacy:/data \
    -v /path/to/modern:/out \
    convertxls --src-dir /data --dst-dir /out --workers 4

# Single file with explicit output.
docker run --rm \
    -v /path/to/single.xls:/data/in.xls \
    -v /path/to/out:/out \
    convertxls /data/in.xls --out /out/in.xlsx

# In-place conversion (writes .xlsx next to each .xls).
docker run --rm \
    -v /path/to/legacy:/data \
    convertxls --src-dir /data --workers 4

# Use podman instead (rootless, no daemon).
podman run --rm \
    -v /path/to/legacy:/data \
    -v /path/to/modern:/out \
    convertxls --src-dir /data --dst-dir /out --workers 4

# Smoke check the image.
docker run --rm convertxls --version
docker run --rm convertxls --list-backends
```

### Customising the image

If you want to ship a specific version of `convertxls` instead of the
local source, edit the Dockerfile's `pip install` line:

```dockerfile
# Replace `pip install --no-cache-dir .` with:
RUN pip install --no-cache-dir convertxls==0.2.0
```

Or build from a git checkout:

```dockerfile
ARG CONVERTXLS_REF=main
RUN pip install --no-cache-dir \
    "convertxls @ git+https://github.com/AC13139/ConvertXlsToXlsx.git@${CONVERTXLS_REF}"
```

### CI integration

```yaml
# .github/workflows/convert.yml
- name: Convert .xls files
  run: |
    docker run --rm \
      -v ${{ github.workspace }}/legacy:/data \
      -v ${{ github.workspace }}/out:/out \
      convertxls --src-dir /data --dst-dir /out --workers 4
```
