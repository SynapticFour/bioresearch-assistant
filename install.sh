#!/usr/bin/env bash
# BioResearch Assistant — Install wrapper (Compose prod path + install.py).
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"

load_env() {
  if [ -f .env ]; then set -a && . ./.env && set +a; fi
}

require_bra_version() {
  if [ -z "${BRA_VERSION:-}" ]; then
    echo "ERROR: BRA_VERSION ist nicht gesetzt. Bitte .env konfigurieren."
    echo "       Beispiel: cp .env.example .env  und  BRA_VERSION=v0.2.1 setzen"
    exit 1
  fi
}

# ollama is a Compose profile. auto and ollama start it. anthropic and
# openai_compatible boot the API without that container.
compose_cmd() {
  local provider
  provider="$(printf '%s' "${LLM_PROVIDER:-ollama}" | tr '[:upper:]' '[:lower:]')"
  if [ "$provider" = "anthropic" ] || [ "$provider" = "openai_compatible" ]; then
    docker compose -f "$COMPOSE_FILE" "$@"
  else
    docker compose -f "$COMPOSE_FILE" --profile ollama "$@"
  fi
}

prod_compose() {
  local offline="${1:-0}"
  load_env
  require_bra_version
  command -v docker >/dev/null || { echo "ERROR: Docker nicht gefunden."; exit 1; }
  local provider
  provider="$(printf '%s' "${LLM_PROVIDER:-ollama}" | tr '[:upper:]' '[:lower:]')"

  if [ "$offline" = "1" ]; then
    compose_cmd up -d postgres
    compose_cmd run --rm backend alembic upgrade head
    compose_cmd up -d --pull never
  else
    compose_cmd pull
    compose_cmd run --rm backend alembic upgrade head
    compose_cmd up -d
  fi

  if [ "$provider" = "anthropic" ] || [ "$provider" = "openai_compatible" ]; then
    echo "[bra] LLM_PROVIDER=${provider}: Ollama container not started."
  else
    models="${OLLAMA_MODELS:-${OLLAMA_MODEL:-mistral}}"
    echo "[bra] Ollama-Modelle laden (Internet nötig, ca. 5–20 Min. je Modell): ${models}"
    for m in $(echo "$models" | tr ',' ' '); do
      if compose_cmd exec -T ollama ollama list 2>/dev/null | grep -q "${m%%:*}"; then
        echo "[bra] Modell bereits vorhanden: $m"
        continue
      fi
      [ -n "$m" ] && compose_cmd exec -T ollama ollama pull "$m" || true
    done
  fi

  for i in $(seq 1 24); do
    curl -sf "http://localhost:8000/api/v1/health" >/dev/null && break
    [ "$i" -eq 24 ] && { echo "ERROR: Health-Check fehlgeschlagen."; exit 1; }
    sleep 5
  done
  echo "[bra] Bereit: http://localhost:3000  (API: http://localhost:8000/api/v1/health)"
}

case "${1:-}" in
  --prod) prod_compose 0 ;;
  --offline) prod_compose 1 ;;
  start|stop|destroy)
    command -v python3 >/dev/null || { echo "ERROR: Python 3 fehlt."; exit 1; }
    exec python3 install.py "$@"
    ;;
  *)
    command -v python3 >/dev/null || { echo "ERROR: Python 3 fehlt."; exit 1; }
    python3 -m pip install psutil --quiet 2>/dev/null || true
    exec python3 install.py "$@"
    ;;
esac
