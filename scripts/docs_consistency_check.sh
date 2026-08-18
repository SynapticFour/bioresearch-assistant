#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILED=1; }

check_absent() {
  local pattern="$1"
  local scope="$2"
  local label="$3"
  if python3 - "$pattern" "$scope" <<'PY'
import pathlib, re, sys
pat = re.compile(sys.argv[1])
scope = pathlib.Path(sys.argv[2])
files = [scope] if scope.is_file() else [p for p in scope.rglob("*") if p.is_file()]
for f in files:
    try:
        text = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if pat.search(text):
        print(f)
        sys.exit(0)
sys.exit(1)
PY
  then
    echo "----"
    echo "Found forbidden pattern (${label}): ${pattern}"
    python3 - "$pattern" "$scope" <<'PY'
import pathlib, re, sys
pat = re.compile(sys.argv[1])
scope = pathlib.Path(sys.argv[2])
files = [scope] if scope.is_file() else [p for p in scope.rglob("*") if p.is_file()]
for f in files:
    try:
        lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        continue
    for i, line in enumerate(lines, 1):
        if pat.search(line):
            print(f"{f}:{i}:{line}")
PY
    echo "----"
    fail "${label}"
  else
    pass "${label}"
  fi
}

check_present() {
  local pattern="$1"
  local scope="$2"
  local label="$3"
  if python3 - "$pattern" "$scope" <<'PY'
import pathlib, re, sys
pat = re.compile(sys.argv[1])
scope = pathlib.Path(sys.argv[2])
files = [scope] if scope.is_file() else [p for p in scope.rglob("*") if p.is_file()]
for f in files:
    try:
        text = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if pat.search(text):
        sys.exit(0)
sys.exit(1)
PY
  then
    pass "${label}"
  else
    fail "${label}"
  fi
}

echo "Running docs consistency checks in: ${ROOT_DIR}"

# Canonical pointers should exist.
check_present "docs/deployment/README\\.md" "${ROOT_DIR}/README.md" "README links deployment matrix"
check_present "docs/INSTALL\\.md" "${ROOT_DIR}/INSTALLATION.md" "INSTALLATION points to canonical install doc"

# OIDC callback URI consistency in docs.
check_absent "http://localhost:8000/auth/callback" "${ROOT_DIR}/docs" "No legacy OIDC callback URI in docs"
check_present "api/v1/auth/callback" "${ROOT_DIR}/docs" "Canonical OIDC callback URI used in docs"

# Deployment variable naming consistency.
check_absent "GITHUB_REPO=" "${ROOT_DIR}/docs/deployment" "No legacy GITHUB_REPO deployment instruction"
check_present "BACKEND_IMAGE|FRONTEND_IMAGE" "${ROOT_DIR}/docs/deployment" "Deployment docs mention image override variables"

# Tooling wording consistency for backend deps in docs.
check_absent "poetry install" "${ROOT_DIR}/docs" "No conflicting poetry install instructions in docs"
check_present "pip install --require-hashes --no-deps --extra-index-url https://download.pytorch.org/whl/cpu -r backend/requirements.lock" "${ROOT_DIR}/docs" "pip hashed-lock install instruction present"

if [[ "${FAILED}" -eq 1 ]]; then
  echo "Docs consistency checks failed."
  exit 1
fi

echo "Docs consistency checks passed."
