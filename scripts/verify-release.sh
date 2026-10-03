#!/usr/bin/env bash
# Local gate before a v* tag.
# Runs the pre-commit CI mirror, frontend unit tests, and supply-chain audits
# when those tools are installed. FHIR/GA4GH conformance stays workflow_dispatch
# (see docs/CI.md).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

"$ROOT/scripts/hooks/ci-check.sh"

echo "verify-release: frontend unit tests"
(cd frontend && npm test)

if [[ -x "$ROOT/backend/.venv/bin/pip-audit" ]]; then
  PIP_AUDIT="$ROOT/backend/.venv/bin/pip-audit"
elif command -v pip-audit >/dev/null 2>&1; then
  PIP_AUDIT="$(command -v pip-audit)"
else
  PIP_AUDIT=""
fi
if [[ -n "$PIP_AUDIT" ]]; then
  echo "verify-release: pip-audit"
  # urllib3 is pinned at 2.8.0 (PYSEC-2026-4175/4176/4177).
  # The Hugging Face pins stay on the 4.x / 2.x lines. Their published fixes
  # are 5.x majors, so this gate records them instead of taking that bump:
  #   PYSEC-2026-3929 transformers save_pretrained path traversal, fix 5.10.0
  #   PYSEC-2026-4174 transformers custom generation code before trust consent,
  #                   no fixed version listed
  #   PYSEC-2026-4164 sentence-transformers trust_remote_code bypass, fix 5.6.0
  # spaCy model wheels are not on PyPI; pip-audit skips them.
  "$PIP_AUDIT" --extra-index-url https://download.pytorch.org/whl/cpu \
    -r backend/requirements.lock \
    --ignore-vuln PYSEC-2025-217 \
    --ignore-vuln PYSEC-2026-2288 \
    --ignore-vuln PYSEC-2026-2289 \
    --ignore-vuln PYSEC-2026-2290 \
    --ignore-vuln CVE-2026-9856 \
    --ignore-vuln PYSEC-2026-3929 \
    --ignore-vuln PYSEC-2026-4174 \
    --ignore-vuln PYSEC-2026-4164
else
  echo "verify-release: pip-audit not installed; skipped (pip install pip-audit)"
fi

if command -v npm >/dev/null 2>&1; then
  echo "verify-release: npm audit (production, high)"
  (cd frontend && npm audit --omit=dev --audit-level=high)
else
  echo "verify-release: npm not installed; skipped"
fi

echo "verify-release: OK"
