# BioResearch Assistant — Synaptic Four

[![CI](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/ci.yml)
[![Version](https://img.shields.io/github/v/tag/SynapticFour/bioresearch-assistant?label=version)](https://github.com/SynapticFour/bioresearch-assistant/tags)
![Coverage](docs/coverage-badge.svg)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
[![GA4GH](https://img.shields.io/badge/GA4GH-WES%20%7C%20DRS%20%7C%20Phenopackets%20%7C%20Passports-green)](https://www.ga4gh.org/)
[![DSGVO](https://img.shields.io/badge/DSGVO-konform-blue)](https://dsgvo-gesetz.de/)
![GAIA-X Ready](https://img.shields.io/badge/GAIA--X-Ready%20by%20Design-0066CC?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMiAxNWwtNS01IDEuNDEtMS40MUwxMCAxNC4xN2w3LjU5LTcuNTlMMTkgOGwtOSA5eiIvPjwvc3ZnPg==)
[![Deploy DFN](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-dfn.yml/badge.svg)](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-dfn.yml)
[![Deploy OTC](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-otc.yml/badge.svg)](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-otc.yml)
[![Deploy Azure](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-azure.yml/badge.svg)](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-azure.yml)
![License](https://img.shields.io/badge/License-BUSL%201.1-blue)

## Was ist das?

BioResearch Assistant ist ein **on-premise KI-System** für Forschungsinstitute und Unikliniken. Es kombiniert Literature Mining (PubMed + KI-Zusammenfassung), Bioinformatik-Pipelines (BLAST, RNA-Seq, Variant Calling) und **DSGVO-konforme Pseudonymisierung**. GA4GH-Standards (WES, DRS, Phenopackets) werden unterstützt.

## Features

- 📚 **Literature Mining** — PubMed-Suche mit KI-Zusammenfassung (DE/EN)
- 🔒 **DSGVO-konforme Pseudonymisierung** — Presidio-basiert (DE + EN)
- ↩️ **De-Pseudonymisierung** — Mit Audit Trail und konfigurierbarer Zugriffskontrolle (DEPSEUDO_ACCESS)
- 📋 **Automatische Metadaten-Extraktion** — DOI (CrossRef), PMID (PubMed), FASTA/VCF-Header
- 🧬 **Geführte Phenopacket-Erstellung** — HPO-Suche und Extraktion aus Freitext
- 🧬 **BLAST Sequenzsuche** — Anbindung an Nextflow-Pipelines
- ⚙️ **GA4GH WES** — Pipeline-Ausführung (Nextflow)
- 📁 **GA4GH DRS** — Datei-Management für genomische Daten
- 🏥 **Phenopackets v2** — Unterstützung für phänotypische Daten
- 🔍 **Vollständiges Audit Logging** — Für Pseudonymisierungen
- 👤 **Konfigurierbare Datenisolation** — User-, Team- oder Open-Modus ([docs/ISOLATION-MODES.md](docs/ISOLATION-MODES.md))

## Tech Stack

| Bereich      | Technologien |
|-------------|--------------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, pgvector, Alembic |
| **Frontend**| React 18, TypeScript, Vite, TanStack Query, Tailwind CSS |
| **GA4GH**   | WES v1.1, DRS v1.3, Phenopackets v2, Passports v1.2 |
| **Sicherheit** | Presidio, AES-256 für Mappings, Audit-Log (kein Rohtext) |

## Schnellstart (5 Minuten)

1. **Repository klonen und .env anlegen**
   ```bash
   git clone https://github.com/SynapticFour/bioresearch-assistant.git
   cd bioresearch-assistant
   cp .env.example .env
   ```
   In `.env` mindestens: `DATABASE_URL`, `PSEUDONYMIZATION_ENCRYPTION_KEY` (64 Hex: `openssl rand -hex 32`).

2. **PostgreSQL starten**
   ```bash
   docker-compose up -d postgres
   ```

3. **Backend**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r backend/requirements.txt
   cd backend && alembic upgrade head && uvicorn app.main:app --reload --port 8000
   ```

4. **Frontend**
   ```bash
   cd frontend && npm install && npm run dev
   ```
   In `frontend/.env`: `VITE_API_URL=http://localhost:8000`

5. **Öffnen:** http://localhost:5173 (oder http://localhost:3000 je nach Vite-Port)

Ausführliche Schritte und Voraussetzungen: **[INSTALLATION.md](INSTALLATION.md)**.

## Architektur

- **Backend (FastAPI):** REST-API unter `/api/v1`, GA4GH-Endpunkte unter `/ga4gh/wes/v1` und `/ga4gh/drs/v1`. Datenbank: PostgreSQL mit pgvector für Embeddings.
- **Frontend (React):** SPA mit Dashboard, Literature, Pseudonymize, BLAST, Pipelines/Workflows, DRS, Audit Log.
- **Pipelines:** Nextflow-Workflows; Ausführung über WES; Ergebnisse optional über DRS abrufbar.

## GA4GH Kompatibilität

| Standard       | Version | Status        |
|----------------|--------|---------------|
| WES            | 1.1    | ✅ Implementiert |
| DRS            | 1.3    | ✅ Implementiert |
| Phenopackets   | v2     | ✅ Implementiert |
| GA4GH Passports | v1.2  | ✅ Implementiert |
| OpenID Connect | —      | ✅ Föderierte Identität |

## ☁️ Cloud Deployment

| Plattform | Status | Anleitung |
|-----------|--------|-----------|
| DFN-Cloud | ✅ Unterstützt | [docs/deployment/DFN-CLOUD.md](docs/deployment/DFN-CLOUD.md) |
| Open Telekom Cloud | ✅ Unterstützt (GAIA-X) | [docs/deployment/OPEN-TELEKOM-CLOUD.md](docs/deployment/OPEN-TELEKOM-CLOUD.md) |
| Azure | ✅ Unterstützt | [docs/deployment/AZURE.md](docs/deployment/AZURE.md) |
| StackIT | 🔄 Geplant | — |
| AWS | 🔄 Geplant | — |
| On-Premise | ✅ Empfohlen | [INSTALLATION.md](INSTALLATION.md) |

## 🇪🇺 GAIA-X Ready by Design

Der BioResearch Assistant ist nach GAIA-X Prinzipien designed:

| Prinzip | Implementierung |
|--------|-----------------|
| **Datensouveränität** | On-Premise (Ollama) oder Cloud-LLM (Anthropic) — siehe Abschnitt unten |
| **DSGVO** | Presidio Pseudonymisierung + vollständiges Audit Logging |
| **Offene Standards** | GA4GH DRS, WES, Phenopackets — keine Vendor Lock-ins |
| **Transparenz** | Open Source, Self-Description API unter `/api/v1/gaia-x/self-description` |
| **Portabilität** | Docker-basiert, läuft auf jeder EU-Infrastruktur |

> **Hinweis:** "GAIA-X Ready by Design" beschreibt die architektonische
> Ausrichtung nach GAIA-X Prinzipien. Eine formale Zertifizierung durch
> die GAIA-X Association ist in der Roadmap.

## Datensouveränität

BioResearch Assistant unterstützt zwei Modi:

### On-Premise Modus (vollständige Datensouveränität)
Mit Ollama als lokalem LLM:
- ✅ Alle Daten bleiben im System
- ✅ Keine externen API-Aufrufe
- ✅ DSGVO-konform für Patientendaten
- ✅ Empfohlen für produktiven Klinikbetrieb

Konfiguration: Kein `ANTHROPIC_API_KEY` gesetzt; `OLLAMA_URL=http://localhost:11434`

### Cloud-LLM Modus (Anthropic API)
Mit Anthropic Claude API:
- ⚠️ Suchanfragen und Texte werden an Anthropic (USA) übertragen
- ⚠️ Nicht für unpseudonymisierte Patientendaten geeignet
- ✅ Für Recherche mit öffentlichen Daten verwendbar
- ✅ Für pseudonymisierte Texte vertretbar

Konfiguration: `ANTHROPIC_API_KEY=sk-ant-...`

### Empfehlung für Unikliniken
Für den produktiven Einsatz mit Patientendaten: Ollama mit lokalem Modell (z.B. Mistral, Llama3). Anthropic API nur für Recherche mit öffentlichen/pseudonymisierten Daten.

## Für Kunden / Institutionen

Pseudonymisierungen sind audit-logged und für Berechtigte reversibel. Volle Kontrolle über Speicherort und Zugriff bei On-Premise-Betrieb. Ideal für Unikliniken und Forschungseinrichtungen mit hohen DSGVO-Anforderungen.

## 📄 Lizenz

BioResearch Assistant ist unter der [Business Source License 1.1](LICENSE.md) lizenziert.

- ✅ Kostenlos für akademische Forschung und Evaluation
- ✅ Code ist vollständig einsehbar
- 💼 Kommerzielle Nutzung: Kontakt unter kontakt@synapticfour.com
- 🔓 Wird automatisch Open Source (Apache 2.0) nach 4 Jahren

---

<p align="center">
  <sub>
    Proudly developed by individuals on the autism spectrum
    in Germany 🇩🇪<br>
    <a href="https://synapticfour.de">Synaptic Four</a> —
    Stuttgart
  </sub>
</p>
