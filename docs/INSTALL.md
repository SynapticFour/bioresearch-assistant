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

> Deployment-Uebersicht fuer alle Wege (online/offline/cloud/k8s):  
> `docs/deployment/README.md`

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

Standardports im Installer:
- Frontend: `3000`
- Backend/API: `8000`

Hinweis fuer lokale Frontend-Entwicklung mit Vite: meist `5173`.

## Was wird installiert?

| Komponente        | Docker Image           | Beschreibung                |
|-------------------|------------------------|-----------------------------|
| PostgreSQL + pgvector | pgvector/pgvector:pg16 | Datenbank mit Vektor-Support |
| Backend           | lokal gebaut           | FastAPI + Python 3.11       |
| Frontend          | lokal gebaut           | React + nginx                |
| Ollama            | ollama/ollama          | Lokales LLM (DSGVO-orientierter Betrieb möglich) |
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
OLLAMA_MODEL=mistral   # z.B. mistral, llama3.2:3b, gemma3:4b, qwen2.5:7b, deepseek-r1:8b, gpt-oss:20b

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

## Beliebte LLMs: lokal installierbar?

Die folgende Übersicht trennt zwischen **Cloud-only Modellen** und
**offiziell lokal verfügbaren Open-Weight Varianten**:

- **OpenAI / ChatGPT**: klassische ChatGPT-Modelle sind Cloud-only, aber `gpt-oss` ist lokal installierbar.
- **Google Gemini**: Gemini ist Cloud-only, aber `Gemma` (open models) ist lokal installierbar.
- **Anthropic Claude**: Cloud/API-only.
- **DeepSeek**: DeepSeek-R1 ist lokal installierbar.
- **Meta Llama**: lokal installierbar.
- **Mistral**: mehrere Open-Modelle lokal installierbar.
- **Qwen (Alibaba)**: lokal installierbar.
- **Cohere**: einzelne Open-Weight Research-Releases sind lokal nutzbar, oft mit restriktiverer Lizenz.
- **xAI Grok**: Grok-1 wurde als Open-Weights veröffentlicht (sehr hardware-intensiv).

Für den Installer sind deshalb praxisnahe Ollama-Modelle als Direktauswahl hinterlegt:
`mistral`, `llama3.2:3b`, `gemma3:4b`, `qwen2.5:7b`, `deepseek-r1:8b`, `gpt-oss:20b`, `phi3`.

## Hardware-Profile im Installer

Der Installer fragt zusätzlich ein Hardware-Profil ab und zeigt passende Empfehlungen:

- **Laptop / klein (8-16 GB RAM)**: `llama3.2:3b`, `gemma3:4b`, `phi3`
- **Workstation (24-64 GB RAM)**: `mistral`, `qwen2.5:7b`, `deepseek-r1:8b`, `gpt-oss:20b`
- **Institut-Server (>=100 GB RAM, z. B. NVIDIA A100)**:
  `gpt-oss:120b`, `deepseek-r1:70b`, `qwen2.5:32b`, `qwen2.5:72b`

Hinweis: Große Modelle benötigen deutlich mehr VRAM/RAM und sind primär
für dedizierte GPU-Server gedacht.

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
