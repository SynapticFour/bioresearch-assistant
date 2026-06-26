#!/usr/bin/env bash
# Export Ollama model weights for air-gap (optional, separate from app bundle).
set -euo pipefail

OUTPUT_DIR="."
VERSION="${BRA_VERSION:?set BRA_VERSION}"
OLLAMA_IMAGE="ollama/ollama:${OLLAMA_IMAGE_TAG:-0.5.13}"
OLLAMA_MODELS="${OLLAMA_MODELS:-mistral}"
OLLAMA_VOLUME="bra_models_export_$$"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    --ollama-models) OLLAMA_MODELS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"
ARCHIVE="${OUTPUT_DIR}/models-bundle-${VERSION}.tar.gz"

docker volume create "${OLLAMA_VOLUME}" >/dev/null
trap 'docker volume rm -f "${OLLAMA_VOLUME}" >/dev/null 2>&1 || true' EXIT

echo "Pulling models into export volume (may take 10–30 min): ${OLLAMA_MODELS}"
while IFS= read -r model; do
  [[ -z "${model}" ]] && continue
  echo "  ollama pull ${model}"
  docker run --rm \
    -v "${OLLAMA_VOLUME}:/root/.ollama" \
    "${OLLAMA_IMAGE}" \
    ollama pull "${model}"
done < <(echo "${OLLAMA_MODELS}" | tr ',' '\n')

echo "${OLLAMA_MODELS}" | tr ',' '\n' > "${OUTPUT_DIR}/ollama-models.txt"

docker run --rm \
  -v "${OLLAMA_VOLUME}:/source:ro" \
  -v "${OUTPUT_DIR}:/backup" \
  alpine:3.20 \
  sh -c "tar -C /source -czf /backup/$(basename "${ARCHIVE}") ."

(
  cd "${OUTPUT_DIR}"
  shasum -a 256 "$(basename "${ARCHIVE}")" ollama-models.txt > "models-bundle-${VERSION}.sha256"
)

echo "Models bundle ready: ${ARCHIVE}"
