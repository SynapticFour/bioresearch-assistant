#!/usr/bin/env bash
set -euo pipefail

BUNDLE_DIR="./offline-bundle"
OLLAMA_VOLUME="ollama_data"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-dir) BUNDLE_DIR="$2"; shift 2 ;;
    --ollama-volume) OLLAMA_VOLUME="$2"; shift 2 ;;
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

# Optional separate models bundle (same directory or parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT="$(cd "${BUNDLE_DIR}/.." && pwd)"
for search in "${BUNDLE_DIR}" "${PARENT}" "."; do
  MODELS="$(ls "${search}"/models-bundle-*.tar.gz 2>/dev/null | head -n 1 || true)"
  if [[ -n "${MODELS}" ]]; then
    echo "Found optional models bundle: ${MODELS}"
    OLLAMA_VOLUME="${OLLAMA_VOLUME}" bash "${SCRIPT_DIR}/import_models_bundle.sh" "${MODELS}"
    break
  fi
done

echo "Import finished."
echo "Next: cp .env.example .env, set BRA_VERSION, then ./install.sh --offline"
