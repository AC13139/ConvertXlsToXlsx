# Dockerfile for ConvertXlsToXlsx.
#
# Self-contained image with:
#   - Python 3.12 (slim Debian base)
#   - LibreOffice headless + Java (the .xls -> .xlsx engine)
#   - convertxls (installed from the local source tree)
#
# Supported platforms: linux/amd64, linux/arm64
#   (available for python:3.12-slim and the Debian LibreOffice packages;
#   build both with scripts/docker-build.sh --multi-arch)
#
# Build:  docker build -t convertxls .
# Or:     make docker-build
# Or:     bash scripts/docker-build.sh --multi-arch  (Buildx manifest list)
#
# Resulting image: ~280 MB compressed, ~700 MB uncompressed.
# Use:     docker run --rm -v /path/to/docs:/data -v /path/to/out:/out \
#             convertxls --src-dir /data --dst-dir /out --workers 4

FROM python:3.12-slim

# System dependencies: libreoffice-calc (the engine), libreoffice-java-common
# (some .xls files with embedded objects need Java), default-jre-headless (the
# JRE), and locales (for non-ASCII filenames like CMYK / Chinese filenames).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-calc \
        libreoffice-core \
        libreoffice-java-common \
        default-jre-headless \
        locales \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Generate a UTF-8 locale so the engine can read filenames with non-ASCII
# characters (CJK, accented, etc.). en_US.UTF-8 is the standard locale.
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Install convertxls from the local source. ``pip install .`` reads the
# project layout from /src and installs the package + all entrypoints.
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

# Clear out the build context we don't need at runtime.
RUN rm -rf /src

# Default work directory — callers mount their data here.
WORKDIR /work

# Smoke check at build time so a broken image never ships.
RUN convertxls --version && convertxls --list-backends

LABEL org.opencontainers.image.title="convertxls"
LABEL org.opencontainers.image.description="Convert legacy Microsoft Excel .xls files into modern .xlsx files via LibreOffice."
LABEL org.opencontainers.image.source="https://github.com/AC13139/ConvertXlsToXlsx"
LABEL org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["convertxls"]
CMD ["--help"]
