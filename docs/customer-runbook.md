# BioResearch Assistant — Installations- und Betriebshandbuch

Kurzanleitung für IT-Betrieb und Forschungs-IT. Technische Details: [GitHub Releases](https://github.com/SynapticFour/bioresearch-assistant/releases).

---

## Voraussetzungen

- Linux-Server mit **Docker** und **Docker Compose v2**
- Freie Ports: **8000** (API), **3000** (Weboberfläche), **11434** (Ollama, intern)
- Ca. **24 GB RAM** empfohlen (Ollama + Backend)
- `.env` mit **`BRA_VERSION`** (Release-Tag, z. B. `v1.3.0`) — **Pflicht**; `./install.sh --prod` bricht ohne diese Variable ab (kein `:latest`).

---

## 1. Standard-Installation (Online)

1. Release von GitHub laden oder Repository klonen.
2. `cp .env.example .env` — Passwörter setzen und **`BRA_VERSION=vX.Y.Z`** eintragen.
3. `./install.sh --prod` ausführen.

Der Installer:

- lädt die Docker-Images der gewählten Version,
- führt **Datenbank-Migrationen** aus (`alembic upgrade head`),
- startet den Stack,
- lädt **Ollama-Modelle** beim ersten Start (Internet nötig, typisch **5–20 Minuten** pro Modell; Standard: `mistral`, konfigurierbar über `OLLAMA_MODEL` / `OLLAMA_MODELS` in `.env`).

**Prüfen:** `curl http://localhost:8000/api/v1/health` → OK. Weboberfläche: `http://localhost:3000`.

**Entwickler-/Lab-Setup (interaktiv):** `./install.sh` ohne `--prod` startet weiterhin `install.py` (voller Stack-Generator).

---

## 2. Air-Gap-Installation (zwei Bundles)

Für isolierte Netze gibt es **zwei getrennte Downloads**:

| Bundle | Inhalt | Größe |
|--------|--------|-------|
| **`bra-offline-<version>.tar.gz`** | App-Images (Backend, Frontend, Postgres, Ollama-Server) | mittel |
| **`models-bundle-<version>.tar.gz`** (optional) | LLM-Gewichte für Ollama | groß ( mehrere GB) |

### Schritte

1. Beide Artefakte (falls LLM offline nötig) laden und mit **`SHA256SUMS.txt`** prüfen.
2. App-Bundle entpacken, `./import.sh` ausführen (lädt Images; erkennt automatisch `models-bundle-*.tar.gz` im gleichen Ordner).
3. `.env` prüfen (`BRA_VERSION` ist im Bundle vorausgefüllt), Passwörter anpassen.
4. `./install.sh --offline` ausführen.

**Ohne Models-Bundle:** Nach dem Start sind **keine** LLM-Antworten verfügbar, bis Modelle geladen wurden — entweder `./install.sh --prod` mit Internet oder separates Models-Bundle importieren.

Models-Bundle manuell erzeugen (Betreiber): `./scripts/export_models_bundle.sh --version vX.Y.Z`

---

## Update & Rollback

**Update:** `BRA_VERSION` in `.env` ändern → `./install.sh --prod`.

**Rollback:** Vorherige `BRA_VERSION` setzen → `./install.sh --prod` (oder `./install.sh --offline` mit altem Bundle).

Details: `docs/deployment/UPDATE-SOP.md`.

---

**Support:** contact@synapticfour.com
