#!/usr/bin/env bash
# Validate a FHIR JSON file: first FHIR R4 structure, then with MII Kerndatensatz Meta IG.
# Usage: ./scripts/validate_fhir_bundle.sh [path/to/bundle.json]
# Env:
#   VALIDATOR_JAR  — path to validator_cli.jar (default: .cache/fhir/validator_cli-<release>.jar)
#   SKIP_MII_IG=1  — only run R4 structural validation (no -ig package)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${REPO_ROOT}/backend/app/interoperability/mii/ig_manifest.json"
DEFAULT_BUNDLE="${REPO_ROOT}/backend/tests/fixtures/mii/sample-bundle.json"
BUNDLE_PATH="${1:-$DEFAULT_BUNDLE}"

if [[ ! -f "$MANIFEST" ]]; then
  echo "Missing manifest: $MANIFEST" >&2
  exit 1
fi
if [[ ! -f "$BUNDLE_PATH" ]]; then
  echo "Bundle not found: $BUNDLE_PATH" >&2
  exit 1
fi

eval "$(MANIFEST="$MANIFEST" python3 <<'PY'
import json, os
m = json.load(open(os.environ["MANIFEST"], encoding="utf-8"))
ig = m["implementation_guide"]
v = m["validator_cli"]
print(f'export FHIR_VERSION={m["fhir_version"]!r}')
print(f'export IG_ID={ig["package_id"]!r}')
print(f'export IG_VER={ig["package_version"]!r}')
print(f'export VAL_REL={v["org_hl7_fhir_core_release"]!r}')
print(f'export VAL_URL={v["download_url"]!r}')
print(f'export VAL_SHA={v["sha256"]!r}')
PY
)"

CACHE_DIR="${REPO_ROOT}/.cache/fhir"
VALIDATOR_JAR="${VALIDATOR_JAR:-${CACHE_DIR}/validator_cli-${VAL_REL}.jar}"

mkdir -p "$CACHE_DIR"

if [[ ! -f "$VALIDATOR_JAR" ]]; then
  echo "Downloading validator_cli ${VAL_REL}..."
  curl -fsSL -o "$VALIDATOR_JAR" "$VAL_URL"
fi

if command -v shasum >/dev/null 2>&1; then
  echo "$VAL_SHA  $VALIDATOR_JAR" | shasum -a 256 -c - || {
    echo "SHA256 mismatch — remove jar and re-download" >&2
    exit 1
  }
fi

echo "=== FHIR R4 structural validation (${FHIR_VERSION}) ==="
java -jar "$VALIDATOR_JAR" "$BUNDLE_PATH" -version "${FHIR_VERSION}" -tx n/a

if [[ "${SKIP_MII_IG:-}" == "1" ]]; then
  echo "SKIP_MII_IG=1 — skipping MII Kerndatensatz Meta IG."
  exit 0
fi

IG_SPEC="${IG_ID}#${IG_VER}"
echo "=== MII IG validation (-ig ${IG_SPEC}) ==="
java -jar "$VALIDATOR_JAR" "$BUNDLE_PATH" -version "${FHIR_VERSION}" -ig "$IG_SPEC" -tx n/a

echo "OK: R4 + MII Meta IG"
