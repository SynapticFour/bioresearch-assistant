#!/bin/bash
# ─────────────────────────────────────────────────────
# reset_db.sh — Reset database to match current .env
#
# Use when: DB password mismatch after new install
# Effect:   Drops DB volume, recreates DB, runs
#           migrations, optionally seeds demo data
#
# Usage:
#   cd ~/bioresearch
#   bash /path/to/reset_db.sh
#   bash /path/to/reset_db.sh --seed
# ─────────────────────────────────────────────────────

set -e
SEED=false
for arg in "$@"; do
  [[ "$arg" == "--seed" ]] && SEED=true
done

COMPOSE="docker compose -f docker-compose.full.yml"
ENV_FILE=".env"

echo "🔄 BioResearch Assistant — DB Reset"
echo ""

# Prüfe ob .env existiert
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env nicht gefunden!"
  echo "   Bitte zuerst python install.py ausführen."
  exit 1
fi

# Lese Passwort aus .env
DB_PASS=$(grep POSTGRES_PASSWORD "$ENV_FILE" \
  | cut -d= -f2)
if [ -z "$DB_PASS" ]; then
  echo "❌ POSTGRES_PASSWORD nicht in .env gefunden!"
  exit 1
fi
echo "✓ Passwort aus .env gelesen"

# Warnung
echo ""
echo "⚠️  WARNUNG: Alle Datenbankdaten gehen verloren!"
echo "   Passwort: ${DB_PASS:0:8}..."
echo ""
read -p "Fortfahren? [j/N]: " confirm
[[ "$confirm" != "j" ]] && echo "Abgebrochen." && exit 0

# DB Container stoppen
echo ""
echo "⏹  Stoppe DB Container..."
$COMPOSE stop db 2>/dev/null || true
$COMPOSE rm -f db 2>/dev/null || true

# DB Volume löschen
echo "🗑  Lösche DB Volume..."
docker volume rm bioresearch_postgres_data \
  2>/dev/null || true
echo "✓ Volume gelöscht"

# DB neu starten
echo "▶  Starte DB neu..."
$COMPOSE up -d db
echo -n "   Warte auf DB"
for i in $(seq 1 30); do
  if $COMPOSE exec -T db pg_isready \
    -U bioresearch > /dev/null 2>&1; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 2
done

# pgvector aktivieren
echo "🔧 Aktiviere pgvector..."
$COMPOSE exec -T db psql -U bioresearch \
  -c "CREATE EXTENSION IF NOT EXISTS vector;" \
  > /dev/null 2>&1
echo "✓ pgvector aktiviert"

# Backend neu starten
echo "▶  Starte Backend..."
$COMPOSE up -d backend
echo -n "   Warte auf Backend"
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/api/v1/health \
    > /dev/null 2>&1; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 3
done

# Migrationen ausführen
echo "🔧 Führe Migrationen aus..."
$COMPOSE exec -T backend alembic upgrade head
echo "✓ Migrationen abgeschlossen"

# Demo Daten
if [ "$SEED" = true ]; then
  echo "🌱 Lade Demo-Daten..."
  $COMPOSE exec -T backend \
    python scripts/seed_demo_data.py
  echo "✓ Demo-Daten geladen"
fi

echo ""
echo "✅ DB Reset abgeschlossen!"
echo ""
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo ""
echo "Tipp: Embeddings neu generieren:"
echo "  curl -X POST http://localhost:8000/api/v1/library/reembed-all"
