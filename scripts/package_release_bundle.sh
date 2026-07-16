#!/usr/bin/env bash
# Build offline release tar for GitHub Release (app images only; models separate).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="${BRA_RELEASE_VERSION:?set BRA_RELEASE_VERSION}"
STAGING="${RELEASE_STAGING_DIR:-release-staging}"

export BRA_VERSION="${VERSION}"

rm -rf "$STAGING"
mkdir -p "$STAGING"

chmod +x scripts/export_offline_bundle.sh
./scripts/export_offline_bundle.sh --output-dir "${STAGING}/offline-bundle" --version "${VERSION}"

BUNDLE_DIR="${STAGING}/bra-offline-${VERSION}"
mkdir -p "${BUNDLE_DIR}/scripts"
cp -R "${STAGING}/offline-bundle/." "${BUNDLE_DIR}/"
cp docker-compose.prod.yml import.sh install.sh "${BUNDLE_DIR}/"
cp scripts/import_offline_bundle.sh scripts/import_models_bundle.sh "${BUNDLE_DIR}/scripts/"
cp docs/customer-runbook.md "${BUNDLE_DIR}/" 2>/dev/null || true
{
  echo "BRA_VERSION=${VERSION}"
  grep -v '^BRA_VERSION=' .env.example | grep -v '^#' | grep -v '^$' || true
} > "${BUNDLE_DIR}/.env"

tar -czf "bra-offline-${VERSION}.tar.gz" -C "$STAGING" "bra-offline-${VERSION}"
echo "Created bra-offline-${VERSION}.tar.gz"
