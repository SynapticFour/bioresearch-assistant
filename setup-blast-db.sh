#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔═══════════════════════════════════════════════╗"
echo "║   BLAST Datenbank Setup — Synaptic Four      ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""
echo -e "${YELLOW}⚠️  WARNUNG: Download ist sehr gross!${NC}"
echo ""
echo "Verfügbare Datenbanken:"
echo "  1) 16S_ribosomal_RNA  (~1 GB)   Für Tests empfohlen"
echo "  2) nt                 (~100 GB) Standard Nukleotid"
echo "  3) nr                 (~300 GB) Protein"
echo ""
read -rp "Wahl [1]: " choice
choice=${choice:-1}

case $choice in
  1) DB="16S_ribosomal_RNA" SIZE="~1 GB" ;;
  2) DB="nt" SIZE="~100 GB" ;;
  3) DB="nr" SIZE="~300 GB" ;;
  *) echo -e "${RED}Ungültige Wahl${NC}"; exit 1 ;;
esac

echo ""
echo -e "${YELLOW}▶ Lade $DB ($SIZE) herunter...${NC}"
echo "  Dies kann mehrere Stunden dauern."
echo ""

docker compose -f docker-compose.full.yml \
  exec backend bash -c "
    mkdir -p /blast/db &&
    cd /blast/db &&
    update_blastdb.pl --decompress $DB &&
    echo 'Fertig!'
  "

echo ""
echo -e "${GREEN}✓ BLAST Datenbank bereit!${NC}"
echo "  Datenbank: $DB"
echo ""
echo "Test mit:"
echo "  docker compose -f docker-compose.full.yml \\"
echo "    exec backend bash -c \\"
echo "    \"echo '>test\nATGCATGC' > /tmp/t.fa && \\"
echo "     blastn -db /blast/db/$DB \\"
echo "     -query /tmp/t.fa -outfmt 6\""
