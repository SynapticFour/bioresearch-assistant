#!/usr/bin/env bash
set -euo pipefail

BUNDLE_DIR="./offline-bundle"
OLLAMA_VOLUME="ollama_data"
IMPORT_OLLAMA_VOLUME="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-dir) BUNDLE_DIR="$2"; shift 2 ;;
    --ollama-volume) OLLAMA_VOLUME="$2"; shift 2 ;;
    --import-ollama-volume) IMPORT_OLLAMA_VOLUME="true"; shift 1 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ ! -d "${BUNDLE_DIR}" ]]; then
  echo "Bundle directory not found: ${BUNDLE_DIR}"
  exit 1
fi

echo "Verifying checksums..."
(
  cd "${BUNDLE_DIR}"
  shasum -a 256 -c checksums.sha256
)

ARCHIVE="$(ls "${BUNDLE_DIR}"/images-*.tar.gz 2>/dev/null | head -n 1 || true)"
if [[ -z "${ARCHIVE}" ]]; then
  echo "No images archive found in ${BUNDLE_DIR}"
  exit 1
fi

echo "Loading docker images from: ${ARCHIVE}"
gunzip -c "${ARCHIVE}" | docker load

if [[ "${IMPORT_OLLAMA_VOLUME}" == "true" ]]; then
  OLLAMA_ARCHIVE="$(ls "${BUNDLE_DIR}"/ollama-volume-*.tar.gz 2>/dev/null | head -n 1 || true)"
  if [[ -z "${OLLAMA_ARCHIVE}" ]]; then
    echo "No Ollama volume archive found. Skipping Ollama volume import."
  else
    echo "Importing Ollama model volume into '${OLLAMA_VOLUME}' from: ${OLLAMA_ARCHIVE}"
    docker volume create "${OLLAMA_VOLUME}" >/dev/null
    docker run --rm \
      -v "${OLLAMA_VOLUME}:/target" \
      -v "${BUNDLE_DIR}:/backup:ro" \
      alpine:3.20 \
      sh -c "rm -rf /target/* && tar -C /target -xzf /backup/$(basename "${OLLAMA_ARCHIVE}")"
  fi
fi

echo "Import finished."
echo "Next: configure .env and run docker compose -f docker-compose.prod.yml up -d"

