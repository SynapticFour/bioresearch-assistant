# BioResearch Assistant — Synaptic Four

[![CI](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/ci.yml)
![Coverage](docs/coverage-badge.svg)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
[![GA4GH](https://img.shields.io/badge/GA4GH-WES%20%7C%20DRS%20%7C%20Phenopackets-green)](https://www.ga4gh.org/)
[![DSGVO](https://img.shields.io/badge/DSGVO-konform-blue)](https://dsgvo-gesetz.de/)
![GAIA-X Ready](https://img.shields.io/badge/GAIA--X-Ready%20by%20Design-0066CC?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMiAxNWwtNS01IDEuNDEtMS40MUwxMCAxNC4xN2w3LjU5LTcuNTlMMTkgOGwtOSA5eiIvPjwvc3ZnPg==)
[![Deploy DFN](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-dfn.yml/badge.svg)](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-dfn.yml)
[![Deploy OTC](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-otc.yml/badge.svg)](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-otc.yml)
[![Deploy Azure](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-azure.yml/badge.svg)](https://github.com/SynapticFour/bioresearch-assistant/actions/workflows/deploy-azure.yml)

## Was ist das?

BioResearch Assistant ist ein **on-premise KI-System** für Forschungsinstitute und Unikliniken. Es kombiniert Literature Mining (PubMed + KI-Zusammenfassung), Bioinformatik-Pipelines (BLAST, RNA-Seq, Variant Calling) und **DSGVO-konforme Pseudonymisierung**. Alle sensiblen Daten bleiben in Ihrer Infrastruktur; es werden GA4GH-Standards (WES, DRS, Phenopackets) unterstützt.

## Features

- 📚 **Literature Mining** — PubMed-Suche mit KI-Zusammenfassung (DE/EN)
- 🔒 **DSGVO-konforme Pseudonymisierung** — Presidio-basiert (DE + EN)
- 🧬 **BLAST Sequenzsuche** — Anbindung an Nextflow-Pipelines
- ⚙️ **GA4GH WES** — Pipeline-Ausführung (Nextflow)
- 📁 **GA4GH DRS** — Datei-Management für genomische Daten
- 🏥 **Phenopackets v2** — Unterstützung für phänotypische Daten
- 🔍 **Vollständiges Audit Logging** — Für Pseudonymisierungen

## Tech Stack

| Bereich      | Technologien |
|-------------|--------------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, pgvector, Alembic |
| **Frontend**| React 18, TypeScript, Vite, TanStack Query, Tailwind CSS |
| **GA4GH**   | WES v1.1, DRS v1.3, Phenopackets v2 |
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
| **Datensouveränität** | Vollständig on-premise — keine Cloud-Abhängigkeit |
| **DSGVO** | Presidio Pseudonymisierung + vollständiges Audit Logging |
| **Offene Standards** | GA4GH DRS, WES, Phenopackets — keine Vendor Lock-ins |
| **Transparenz** | Open Source, Self-Description API unter `/api/v1/gaia-x/self-description` |
| **Portabilität** | Docker-basiert, läuft auf jeder EU-Infrastruktur |

> **Hinweis:** "GAIA-X Ready by Design" beschreibt die architektonische
> Ausrichtung nach GAIA-X Prinzipien. Eine formale Zertifizierung durch
> die GAIA-X Association ist in der Roadmap.

## Für Kunden / Institutionen

On-premise bedeutet: **Ihre Daten verlassen nicht Ihre Infrastruktur.** Keine Weitergabe an Dritte, volle Kontrolle über Speicherort und Zugriff. Pseudonymisierungen sind audit-logged und für Berechtigte reversibel. Ideal für Unikliniken und Forschungseinrichtungen mit hohen DSGVO-Anforderungen.

## Lizenz & Kontakt

**Synaptic Four**

Projekt- und Lizenzdetails siehe Repository.
