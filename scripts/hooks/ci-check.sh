#!/usr/bin/env bash
# Mirror .github/workflows/ci.yml (backend ruff/pytest + frontend tsc/build).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/backend/.venv/bin/ruff" ]]; then
  RUFF="$ROOT/backend/.venv/bin/ruff"
  PYTEST="$ROOT/backend/.venv/bin/pytest"
elif command -v ruff >/dev/null 2>&1; then
  RUFF=ruff
  PYTEST=pytest
else
  echo "ci-check: ruff not found — install backend deps (uv/pip) first" >&2
  exit 1
fi

echo "ci-check: ruff check (backend)"
(cd backend && "$RUFF" check app/ tests/)

echo "ci-check: ruff format --check (backend)"
(cd backend && "$RUFF" format --check app/ tests/)

echo "ci-check: pytest (backend)"
(cd backend && "$PYTEST" tests/ -q --cov-fail-under=0)

echo "ci-check: tsc --noEmit (frontend)"
(cd frontend && npx tsc --noEmit)

echo "ci-check: npm run build (frontend)"
(cd frontend && npm run build)

echo "ci-check: OK (matches bioresearch-assistant CI)"
