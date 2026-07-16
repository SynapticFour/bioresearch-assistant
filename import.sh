#!/usr/bin/env bash
# Air-gap import: app images + optional Ollama models bundle.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "${ROOT}/scripts/import_offline_bundle.sh" "$@"
