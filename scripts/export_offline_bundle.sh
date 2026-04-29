#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="./offline-bundle"
BACKEND_IMAGE="ghcr.io/synapticfour/bioresearch-assistant-backend:latest"
FRONTEND_IMAGE="ghcr.io/synapticfour/bioresearch-assistant-frontend:latest"
POSTGRES_IMAGE="pgvector/pgvector:pg16"
OLLAMA_IMAGE="ollama/ollama:latest"
OLLAMA_MODELS=""
OLLAMA_VOLUME="ollama_data"
EXPORT_OLLAMA_VOLUME="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --backend-image) BACKEND_IMAGE="$2"; shift 2 ;;
    --frontend-image) FRONTEND_IMAGE="$2"; shift 2 ;;
    --ollama-models) OLLAMA_MODELS="$2"; shift 2 ;;
    --ollama-volume) OLLAMA_VOLUME="$2"; shift 2 ;;
    --export-ollama-volume) EXPORT_OLLAMA_VOLUME="true"; shift 1 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"

IMAGES_TAR="${OUTPUT_DIR}/images-$(date +%Y%m%d-%H%M%S).tar"
IMAGES_TARGZ="${IMAGES_TAR}.gz"

echo "Pulling images..."
docker pull "${BACKEND_IMAGE}"
docker pull "${FRONTEND_IMAGE}"
docker pull "${POSTGRES_IMAGE}"
docker pull "${OLLAMA_IMAGE}"

echo "Saving images to tar..."
docker save \
  "${BACKEND_IMAGE}" \
  "${FRONTEND_IMAGE}" \
  "${POSTGRES_IMAGE}" \
  "${OLLAMA_IMAGE}" \
  -o "${IMAGES_TAR}"

gzip -f "${IMAGES_TAR}"

if [[ -n "${OLLAMA_MODELS}" ]]; then
  echo "${OLLAMA_MODELS}" | tr ',' '\n' > "${OUTPUT_DIR}/ollama-models.txt"
  echo "Requested Ollama models listed in ${OUTPUT_DIR}/ollama-models.txt."
  echo "Pulling requested Ollama models into local Ollama volume..."
  while IFS= read -r model; do
    if [[ -n "${model}" ]]; then
      echo "  - ollama pull ${model}"
      docker run --rm \
        -v "${OLLAMA_VOLUME}:/root/.ollama" \
        "${OLLAMA_IMAGE}" \
        ollama pull "${model}"
    fi
  done < "${OUTPUT_DIR}/ollama-models.txt"
fi

if [[ "${EXPORT_OLLAMA_VOLUME}" == "true" ]]; then
  OLLAMA_ARCHIVE="${OUTPUT_DIR}/ollama-volume-$(date +%Y%m%d-%H%M%S).tar.gz"
  echo "Exporting Ollama model volume (${OLLAMA_VOLUME})..."
  docker run --rm \
    -v "${OLLAMA_VOLUME}:/source:ro" \
    -v "${OUTPUT_DIR}:/backup" \
    alpine:3.20 \
    sh -c "tar -C /source -czf /backup/$(basename "${OLLAMA_ARCHIVE}") ."
  echo "Generated: $(basename "${OLLAMA_ARCHIVE}")"
fi

(
  cd "${OUTPUT_DIR}"
  shasum -a 256 ./* > checksums.sha256
)

echo "Offline bundle ready at: ${OUTPUT_DIR}"
echo "Generated: $(basename "${IMAGES_TARGZ}")"

