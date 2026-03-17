# Installation — BioResearch Assistant

## Voraussetzungen

| Voraussetzung   | Minimum   | Empfohlen   |
|-----------------|-----------|-------------|
| Docker Desktop  | 24.x      | aktuell     |
| Python          | 3.9       | 3.11+       |
| RAM             | 8 GB      | 16 GB (für Ollama) |
| Speicher        | 10 GB     | 30 GB       |
| Betriebssystem  | Windows 10, macOS 12, Ubuntu 20.04 | — |

## Schnellstart

### macOS / Linux

```bash
git clone https://github.com/SynapticFour/bioresearch-assistant.git
cd bioresearch-assistant
./install.sh
```

### Windows

```bat
git clone https://github.com/SynapticFour/bioresearch-assistant.git
cd bioresearch-assistant
install.bat
```

### Unattended (für IT-Abteilungen / automatisiert)

```bash
./install.sh --unattended --install-dir /opt/bioresearch
```

## Was wird installiert?

| Komponente        | Docker Image           | Beschreibung                |
|-------------------|------------------------|-----------------------------|
| PostgreSQL + pgvector | pgvector/pgvector:pg16 | Datenbank mit Vektor-Support |
| Backend           | lokal gebaut           | FastAPI + Python 3.11       |
| Frontend          | lokal gebaut           | React + nginx                |
| Ollama            | ollama/ollama          | Lokales LLM (DSGVO-konform) |
| BLAST             | ncbi/blast             | Sequenzsuche                 |
| Nextflow          | nextflow/nextflow       | Pipeline Engine              |

## Management nach Installation

```bash
./start.sh        # System starten
./stop.sh         # System stoppen
./restart.sh      # System neustarten
./update.sh       # Update auf neue Version
./logs.sh         # Alle Logs anzeigen
./logs.sh backend # Nur Backend Logs
./backup.sh       # Datenbank-Backup
./status.sh       # System-Status
```

## Konfiguration

Alle Einstellungen werden in `.env` gespeichert (automatisch generiert, niemals committen!).

Wichtige Variablen:

```bash
# Datenisolation
ISOLATION_MODE=user    # user / team / open

# De-Pseudonymisierung Zugriff
DEPSEUDO_ACCESS=owner  # owner / team / admin

# LLM Provider
LLM_PROVIDER=ollama    # ollama / anthropic
OLLAMA_MODEL=mistral   # mistral / llama3 / gemma2

# Version
APP_VERSION=1.3.0
```

## DSGVO Hinweis

| Modus        | Datensouveränität |
|--------------|--------------------|
| Ollama (Standard) | Datenverarbeitung lokal im eigenen Setup |
| Anthropic API     | ⚠️ Texte werden an Anthropic übertragen |

Für klinische Produktionsbetriebe wird in der Regel ein Betrieb mit
lokalem LLM (Ollama) ohne externe KI‑APIs empfohlen. Ob dies ausreicht,
um rechtliche Anforderungen (z. B. DSGVO, §393 SGB V) zu erfüllen,
muss durch die verantwortlichen Stellen geprüft werden.

## Ollama GPU Support

Für schnellere Inferenz mit NVIDIA GPU: In `docker-compose.full.yml` unter `ollama:` die auskommentierten GPU-Zeilen einkommentieren:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## Große Dateien (DRS)

Für genomische Dateien > 500MB: Datei direkt auf Server kopieren, dann Server-Pfad in der DRS-UI angeben.

```bash
scp /local/genome.bam server:/data/drs/
# Dann in UI: DRS → Pfad: /data/drs/genome.bam
```

## Troubleshooting

### Docker startet nicht

Docker Desktop öffnen und warten, bis es vollständig läuft.

### Port bereits belegt

Installer erneut starten und anderen Port wählen, oder bestehenden Prozess beenden:

```bash
sudo lsof -i :3000  # Wer nutzt Port 3000?
```

### Ollama Modell Download unterbrochen

```bash
./start.sh
docker compose -f docker-compose.full.yml exec ollama ollama pull mistral
```

### Logs anzeigen

```bash
./logs.sh            # Alle Services
./logs.sh backend    # Nur Backend
./logs.sh db         # Nur Datenbank
./logs.sh ollama     # Nur Ollama
```

### Komplette Neuinstallation

```bash
./stop.sh
docker compose -f docker-compose.full.yml down -v
python install.py
```
