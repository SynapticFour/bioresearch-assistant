# BioResearch Assistant

**KI-gestützte Forschungsplattform für
biomedizinische Forschung**
DSGVO-konform · On-premise · Open Standards

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL%201.1-blue.svg)](LICENSE)
[![GA4GH Compliant](https://img.shields.io/badge/GA4GH-Compliant-green.svg)](https://ga4gh.org)
[![GAIA-X Ready](https://img.shields.io/badge/GAIA--X-Ready-blue.svg)](https://gaia-x.eu)
[![DSGVO](https://img.shields.io/badge/DSGVO-Konform-green.svg)](docs/COMPLIANCE.md)

---

## Was ist BioResearch Assistant?

BioResearch Assistant verbindet Literaturrecherche,
Pseudonymisierung, Phenotypisierung, Genomanalyse
und KI in einer einzigen, DSGVO-konformen Plattform —
vollständig on-premise betreibbar.

Entwickelt von [Synaptic Four](https://synapticfour.de)
für Unikliniken, Forschungsgruppen und Biotech-Startups
im DACH-Raum.

---

## Features

| Feature | Standard | Status |
|---------|----------|--------|
| 📚 Literaturrecherche | PubMed API | ✅ |
| 🧠 RAG — Frag deine Bibliothek | Ollama / Claude | ✅ |
| 🔒 DSGVO Pseudonymisierung | Presidio + AES-256 | ✅ |
| 👤 Phenopackets | GA4GH v2.0 | ✅ |
| 🗄️ Dateiverwaltung | GA4GH DRS v1.4 | ✅ |
| 🧬 BLAST Sequenzsuche | NCBI BLAST+ | ✅ |
| ⚙️ Pipelines | GA4GH WES v1.1 | ✅ |
| 📓 Research Notebook (ELN) | Markdown + KI | ✅ |
| 📦 FAIR Data Export | DataCite + Zenodo | ✅ |
| 🌐 GAIA-X Self-Description | Gaia-X Standard | ✅ |

---

## Compliance

| Standard | Status |
|----------|--------|
| 🇪🇺 DSGVO / GDPR | ✅ |
| 🇩🇪 BDSG + §393 SGB V | ✅ On-premise |
| 🇩🇪 GDNG 2025 | ✅ |
| 🌐 GAIA-X Standard | ✅ |
| 🧬 GA4GH WES / DRS / Phenopackets | ✅ |
| 📊 FAIR Prinzipien | ✅ |
| 🔒 OWASP Top 10 | ✅ |
| 🏥 HIPAA (technisch) | ✅ |
| 📋 ICH GCP E6(R3) | ✅ |
| 🏥 EHDS-ready | ✅ (Pflichten ab 2029) |

Vollständige Dokumentation: [docs/COMPLIANCE.md](docs/COMPLIANCE.md)

---

## Schnellstart

### Voraussetzungen
- Docker Desktop
- Python 3.11+
- 8 GB RAM (16 GB empfohlen)
- 10 GB freier Speicher

### Installation

```bash
git clone https://github.com/SynapticFour/bioresearch-assistant
cd bioresearch-assistant
python install.py
```

Der Installer führt dich durch:
- Konfiguration (Modell, Auth, Ports)
- Docker Compose Setup
- Ollama Modell Download
- Datenbankmigrationen

Danach erreichbar unter:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Dokumentation

| Dokument | Beschreibung |
|----------|-------------|
| [USER-GUIDE.md](docs/USER-GUIDE.md) | Benutzerhandbuch (UI) |
| [DEVELOPER-GUIDE.md](docs/DEVELOPER-GUIDE.md) | API Referenz + curl Beispiele |
| [COMPLIANCE.md](docs/COMPLIANCE.md) | DSGVO, GAIA-X, GA4GH, NIS2, EHDS |
| [TOOLS-SETUP.md](docs/TOOLS-SETUP.md) | BLAST, Nextflow Setup |
| [AUDIT-REPORT.md](docs/AUDIT-REPORT.md) | Security Audit |
| [SBOM.md](docs/SBOM.md) | Software Bill of Materials |

---

## Architektur

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│   React     │────▶│    FastAPI      │────▶│ PostgreSQL   │
│ TypeScript  │     │   Python 3.11   │     │ + pgvector   │
│ Tailwind    │     │   SQLAlchemy    │     │ (768-dim)    │
└─────────────┘     └────────┬────────┘     └──────────────┘
                             │
                    ┌────────▼────────┐
                    │   Ollama (lokal)│
                    │   Presidio NLP  │
                    │   Sentence-     │
                    │   Transformers  │
                    └─────────────────┘
```

---

## Lizenz

BUSL 1.1 — Business Source License
Kostenlos für Forschung und Evaluation.
Kommerzielle Nutzung: contact@synapticfour.de

© 2026 Synaptic Four · synapticfour.de

---
