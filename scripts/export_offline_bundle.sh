#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="./offline-bundle"
VERSION="${BRA_VERSION:?set BRA_VERSION}"
BACKEND_IMAGE="ghcr.io/synapticfour/bioresearch-assistant-backend:${VERSION}"
FRONTEND_IMAGE="ghcr.io/synapticfour/bioresearch-assistant-frontend:${VERSION}"
POSTGRES_IMAGE="pgvector/pgvector:pg16"
OLLAMA_IMAGE="ollama/ollama:${OLLAMA_IMAGE_TAG:-0.5.13}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --version) VERSION="$2"; BACKEND_IMAGE="ghcr.io/synapticfour/bioresearch-assistant-backend:${VERSION}"
      FRONTEND_IMAGE="ghcr.io/synapticfour/bioresearch-assistant-frontend:${VERSION}"; shift 2 ;;
    --backend-image) BACKEND_IMAGE="$2"; shift 2 ;;
    --frontend-image) FRONTEND_IMAGE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"

IMAGES_TAR="${OUTPUT_DIR}/images-${VERSION}.tar"
IMAGES_TARGZ="${IMAGES_TAR}.gz"

echo "Pulling images (version ${VERSION})..."
docker pull "${BACKEND_IMAGE}"
docker pull "${FRONTEND_IMAGE}"
docker pull "${POSTGRES_IMAGE}"
docker pull "${OLLAMA_IMAGE}"

echo "Saving images..."
docker save \
  "${BACKEND_IMAGE}" \
  "${FRONTEND_IMAGE}" \
  "${POSTGRES_IMAGE}" \
  "${OLLAMA_IMAGE}" \
  -o "${IMAGES_TAR}"

gzip -f "${IMAGES_TAR}"

cat > "${OUTPUT_DIR}/manifest.txt" <<EOF
bra_version=${VERSION}
backend_image=${BACKEND_IMAGE}
frontend_image=${FRONTEND_IMAGE}
postgres_image=${POSTGRES_IMAGE}
ollama_image=${OLLAMA_IMAGE}
generated_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

(
  cd "${OUTPUT_DIR}"
  shasum -a 256 ./* > checksums.sha256
)

echo "Offline bundle (app only, no LLM weights): ${OUTPUT_DIR}"
echo "Generated: $(basename "${IMAGES_TARGZ}")"
