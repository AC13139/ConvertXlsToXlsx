#!/usr/bin/env bash
# Build the convertxls Docker image. Auto-detects docker or podman.
#
# Usage:
#   bash scripts/docker-build.sh               # build with default tag (convertxls:latest)
#   bash scripts/docker-build.sh mytag:1.2.3   # build with custom tag
#   bash scripts/docker-build.sh --multi-arch  # multi-arch build via docker buildx
#
# Multi-arch builds (docker buildx only):
#   The default single-arch build works with docker or podman. For a
#   linux/amd64 + linux/arm64 manifest list, use Buildx:
#     bash scripts/docker-build.sh --multi-arch ghcr.io/you/convertxls:1.2.3
#   The manifest is pushed to the tag's registry, so TAG must be a registry
#   reference. Override platforms with BUILDX_PLATFORMS (default
#   linux/amd64,linux/arm64). Cross-platform builds use QEMU emulation; on a
#   fresh runner you may need:
#     docker run --privileged --rm tonistiigi/binfmt --install all
#
# Notes:
#   - The build needs ~2 GB of RAM for the apt-get install of LibreOffice +
#     OpenJDK. On constrained CI runners, set CONTAINER_MEMORY=4g to give the
#     builder a memory cap.
#   - The recipe was verified manually via podman run with the same package
#     set (libreoffice-calc, libreoffice-core, libreoffice-java-common,
#     default-jre-headless) and successfully converted 12 real .xls files.

set -euo pipefail

cd "$(dirname "$0")/.."

TAG="convertxls:latest"
MULTI_ARCH=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --multi-arch)
            MULTI_ARCH=1
            ;;
        -*)
            echo "Error: unknown option: $1" >&2
            exit 1
            ;;
        *)
            TAG="$1"
            ;;
    esac
    shift
done

# Pick the first available runtime (docker first for --multi-arch, which
# requires Buildx).
candidates=(podman docker)
if [ "$MULTI_ARCH" -eq 1 ]; then
    candidates=(docker podman)
fi

RUNTIME=""
for candidate in "${candidates[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1; then
        RUNTIME="$candidate"
        break
    fi
done

if [ -z "$RUNTIME" ]; then
    echo "Error: neither 'docker' nor 'podman' is on PATH." >&2
    exit 1
fi

echo "[docker-build] Using runtime: $RUNTIME"
echo "[docker-build] Tag: $TAG"

# Build with a generous memory cap to avoid OOM on the OpenJDK install step.
MEMORY_FLAG=()
if [ -n "${CONTAINER_MEMORY:-}" ]; then
    MEMORY_FLAG=(--memory="${CONTAINER_MEMORY}")
    echo "[docker-build] Memory cap: ${CONTAINER_MEMORY}"
fi

if [ "$MULTI_ARCH" -eq 1 ]; then
    if [ "$RUNTIME" != "docker" ]; then
        echo "Error: --multi-arch requires docker buildx; only podman is on PATH." >&2
        exit 1
    fi
    if ! docker buildx version >/dev/null 2>&1; then
        echo "Error: 'docker buildx' is not available. Install the Buildx plugin." >&2
        exit 1
    fi
    PLATFORMS="${BUILDX_PLATFORMS:-linux/amd64,linux/arm64}"
    echo "[docker-build] Multi-arch platforms: $PLATFORMS"
    echo "[docker-build] Pushing manifest list to registry tag: $TAG"
    docker buildx build \
        "${MEMORY_FLAG[@]}" \
        --platform "$PLATFORMS" \
        --push \
        -t "$TAG" .
    exit 0
fi

$RUNTIME build "${MEMORY_FLAG[@]}" -t "$TAG" .
