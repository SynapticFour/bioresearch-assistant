#!/bin/bash
set -e

echo "BioResearch Assistant — Installer v1.3.0"
echo "Synaptic Four"
echo ""

# Python prüfen
if ! command -v python3 &>/dev/null; then
    echo "✗ Python 3 nicht gefunden."
    echo "  Bitte installieren: https://python.org"
    exit 1
fi

# psutil optional installieren
python3 -m pip install psutil --quiet 2>/dev/null || true

# Installer starten
python3 install.py "$@"
