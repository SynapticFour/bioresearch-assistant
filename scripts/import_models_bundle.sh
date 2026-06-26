#!/usr/bin/env bash
# Import optional Ollama models bundle (models-bundle-*.tar.gz).
set -euo pipefail

BUNDLE="${1:-}"
OLLAMA_VOLUME="${OLLAMA_VOLUME:-ollama_data}"

if [[ -z "${BUNDLE}" ]]; then
  BUNDLE="$(ls ./models-bundle-*.tar.gz 2>/dev/null | head -n 1 || true)"
fi

if [[ -z "${BUNDLE}" || ! -f "${BUNDLE}" ]]; then
  echo "No models bundle found (models-bundle-*.tar.gz). Skipping."
  exit 0
fi

if [[ -f "${BUNDLE%.tar.gz}.sha256" ]] || [[ -f "$(dirname "$BUNDLE")/models-bundle-$(basename "$BUNDLE" | sed 's/models-bundle-//;s/.tar.gz//').sha256" ]]; then
  SHA_FILE="$(ls "$(dirname "$BUNDLE")"/models-bundle-*.sha256 2>/dev/null | head -n 1 || true)"
  if [[ -n "${SHA_FILE}" ]]; then
    echo "Verifying models bundle checksum..."
    (cd "$(dirname "$BUNDLE")" && shasum -a 256 -c "$(basename "$SHA_FILE")")
  fi
fi

echo "Importing Ollama models from ${BUNDLE} into volume ${OLLAMA_VOLUME}..."
docker volume create "${OLLAMA_VOLUME}" >/dev/null
docker run --rm \
  -v "${OLLAMA_VOLUME}:/target" \
  -v "$(cd "$(dirname "$BUNDLE")" && pwd):/backup:ro" \
  alpine:3.20 \
  sh -c "rm -rf /target/* && tar -C /target -xzf /backup/$(basename "$BUNDLE")"

echo "Models import complete."
