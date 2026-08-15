# BioResearch Assistant

**KI-gestützte Forschungsplattform für
biomedizinische Forschung**
Für datenschutzfreundliche Nutzung konzipiert (technisch, kein Rechtsrat) · On-premise · Open Standards

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL%201.1-blue.svg)](LICENSE)
[![GA4GH Standards](https://img.shields.io/badge/GA4GH-Standards-blue.svg)](https://ga4gh.org)
[![GAIA-X design alignment](https://img.shields.io/badge/GAIA--X-design%20alignment-blue.svg)](docs/GAIA-X-ALIGNMENT.md)
[![Datenschutz](https://img.shields.io/badge/Datenschutz-DSGVO%20orientiert-green.svg)](docs/COMPLIANCE.md)

**Security reviewers:** [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) · **Who this is for:** [docs/IDENTITY.md](docs/IDENTITY.md)

---

## Was ist BioResearch Assistant?

BioResearch Assistant verbindet Literaturrecherche,
Pseudonymisierung, Phenotypisierung, Genomanalyse
und KI in einer Plattform, die technische Maßnahmen
zur datenschutzfreundlichen Nutzung bereitstellt —
vollständig on-premise betreibbar.

Konzipiert für Unikliniken, Forschungsgruppen und Biotech-Startups
im DACH-Raum.

---

## Features

| Feature | Standard | Status |
|---------|----------|--------|
| 📚 Literaturrecherche | PubMed API | ✅ |
| 🧠 **Locus** — On-Premise RAG (Retrieval-Augmented Generation) | Ollama (lokal); optional kuratierte Indizes | ✅ siehe [docs/LOCUS-MODULE.md](docs/LOCUS-MODULE.md) |
| 🔒 DSGVO Pseudonymisierung | Presidio + AES-256 | ✅ |
| 👤 Phenopackets | GA4GH v2.0 | ✅ |
| 🗄️ Dateiverwaltung | GA4GH DRS | ✅ |
| 🧬 BLAST Sequenzsuche | NCBI BLAST+ | ✅ |
| ⚙️ Pipelines | GA4GH WES v1.1 | ✅ |
| 🏥 MII-KDS Export + Broad Consent Tracker | FHIR R4 / MII-KDS-orientiert | ✅ (operational, partial profile mapping) |
| 🔁 Search-to-Execution (PhenoFlow) | Phenopackets + DRS + WES | ✅ v0.1 |
| 📓 Research Notebook (ELN) | Markdown + KI | ✅ |
| 🌐 GAIA-X Self-Description | Gaia-X Standard | ⚠️ Design alignment only, **not certified** |
| 📦 FAIR Data Export | DataCite + Zenodo | ⚠️ Heuristic FAIR check, not a certification |

---

## Datensouveränität

- Lokale Verarbeitung ist mit Ollama (ohne externe LLM-API) möglich.
- Bei Nutzung externer APIs (z. B. Anthropic) werden Inhalte an den jeweiligen Anbieter übertragen.
- Die rechtliche Bewertung erfolgt durch die verantwortliche Institution.

Details: `docs/COMPLIANCE.md` und `docs/deployment/README.md`.

---

## Compliance (Überblick, keine Rechtsberatung)

Die Software wurde technisch so gestaltet, dass sie gängige
Standards und gesetzliche Rahmenbedingungen **unterstützen kann**.
Ob ein konkreter Einsatz „konform“ ist, hängt immer von
Konfiguration, Betriebsumgebung und den Verantwortlichen vor Ort ab.

| Bereich / Rahmen | Technische Ausrichtung (kein Zertifikat) |
|------------------|-------------------------------------------|
| 🇪🇺 DSGVO / GDPR | Pseudonymisierung, Audit-Logs, Isolation, Verschlüsselung (Details in `COMPLIANCE.md`) |
| 🇩🇪 BDSG / §393 SGB V | Fokus auf On-Premise-Betrieb; Cloud-Einsatz erfordert separate Bewertung |
| 🇩🇪 GDNG 2025 | Unterstützt pseudonymisierte Forschungs-Workflows, Audit-Trails |
| 🌐 GAIA-X | Architektur an GAIA-X-Prinzipien ausgerichtet; **keine formale Zertifizierung**; API meldet `gaia_x_ready: false` |
| 🧬 GA4GH WES / DRS / Phenopackets | Implementierung orientiert sich an den jeweiligen GA4GH-Spezifikationen |
| 📊 FAIR Prinzipien | FAIR-Export, Metadaten & Compliance-Check als Hilfsmittel |
| 🔒 OWASP Top 10 | Sicherheitsmaßnahmen an OWASP-Empfehlungen ausgerichtet |
| 🏥 HIPAA / ICH GCP / EHDS | Ausgewählte technische Kontrollen vorhanden; rechtliche Bewertung bleibt Kund:in vorbehalten |

Details und technische Einordnung: [docs/COMPLIANCE.md](docs/COMPLIANCE.md)
Dieses Dokument ersetzt **keine** individuelle Rechtsberatung.

---

## MII-KDS Export (technischer Scope)

BioResearch Assistant enthält einen MII-KDS-orientierten Exportpfad:

- Pseudonymisierte Forschungsdaten können als FHIR `Bundle` für MII-nahe Module exportiert werden
- Broad-Consent-Informationen können pro Pseudonym erfasst und als FHIR `Consent` ausgegeben werden
- Terminologie-Overrides sind für kuratierte Mapping-Korrekturen verfügbar
- Exporte können synchron oder als asynchroner Job mit Status/Artefakt erfolgen

Wichtig zur Einordnung:

- Die Implementierung ist **MII-KDS-orientiert**, aber kein Ersatz für eine formale standortbezogene Konformitätsprüfung.
- Profile/Bindings sind in Teilen implementiert; einzelne Mappings sind weiterhin als `partial` dokumentiert.
- Der produktive Einsatz in FDPG-/DIZ-Prozessen erfordert in der Regel zusätzliche organisatorische und fachliche Qualitätssicherungen durch die verantwortliche Institution.

---

## Schnellstart

### Voraussetzungen
- Docker Desktop
- Python 3.11+ (3.12 empfohlen)
- 8 GB RAM (16 GB empfohlen)
- 10 GB freier Speicher

Für vollständige Installationsvarianten (lokal, unattended, troubleshooting):
`docs/INSTALL.md`.

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

Hinweis Dev-Frontend: bei lokalem Vite-Start typischerweise `http://localhost:5173`.

Ein-Klick-Alternative (nach Klonen):

```bash
make up          # unattended install oder start
make down        # stoppen, Daten behalten
make destroy     # stoppen + Volumes entfernen
```

Details: `docs/INSTALL.md`.

### Stoppen / entfernen

| Ziel | Befehl |
|------|--------|
| Stoppen, **Daten behalten** | `make down`, `./stop.sh`, oder `python install.py stop` |
| Volumes entfernen (Neustart) | `make destroy`, `./destroy.sh`, oder `python install.py destroy` |

---

## Dokumentation

| Dokument | Beschreibung |
|----------|-------------|
| [USER-GUIDE.md](docs/USER-GUIDE.md) | Benutzerhandbuch (UI) |
| [DEVELOPER-GUIDE.md](docs/DEVELOPER-GUIDE.md) | API Referenz + curl Beispiele |
| [PHENOFLOW.md](docs/PHENOFLOW.md) | PhenoFlow v0.1 (Search-to-Execution) |
| [COMPLIANCE.md](docs/COMPLIANCE.md) | DSGVO, GAIA-X, GA4GH, NIS2, EHDS |
| [CONFORMANCE.md](docs/CONFORMANCE.md) | Conformance / QA (GA4GH & verwandte Endpunkte) |
| [MII-EXPORT.md](docs/MII-EXPORT.md) | MII-Export, Consent, Async-Jobs, Terminologie-Overrides |
| [TOOLS-SETUP.md](docs/TOOLS-SETUP.md) | BLAST, Nextflow Setup |
| [deployment/UNIKLINIK.md](docs/deployment/UNIKLINIK.md) | Uniklinik-Produktionscheckliste (OIDC, Isolation, Secrets) |
| [deployment/README.md](docs/deployment/README.md) | Deployment-Matrix (online, offline, bare metal, cloud, k8s) |
| [deployment/OFFLINE-AIRGAP.md](docs/deployment/OFFLINE-AIRGAP.md) | Air-gapped / Offline Install |
| [deployment/UPDATE-SOP.md](docs/deployment/UPDATE-SOP.md) | SOP-Vorlage für Updates, Bugfixes, Rollback |
| [deployment/RELEASE-CHECKLIST.md](docs/deployment/RELEASE-CHECKLIST.md) | 10 Pflichtchecks vor Release/Hotfix |
| `scripts/deployment_preflight.sh` | Szenario-basierte Deployment-Checks vor Rollout |
| `scripts/docs_consistency_check.sh` | Konsistenzcheck für Dokumentation (Konstanten/Begriffe) |
| [AUDIT-REPORT.md](docs/AUDIT-REPORT.md) | Security Audit (internal technical assessment) |
| [customer/SECURITY.md](docs/customer/SECURITY.md) | Customer security one-pager (DRS, US-LLM, clinical pilots) |
| [SOLUM-SUBJECT-BRIDGE.md](docs/SOLUM-SUBJECT-BRIDGE.md) | Phenopacket → Solum `solum_subject_id` (ADR-0003) |
| [SBOM.md](docs/SBOM.md) | Software Bill of Materials |
| [BUSINESS-MODEL.md](docs/BUSINESS-MODEL.md) | Open-core Lizenz- und Nutzungsmodell (BUSL) |
| [LOCUS-MODULE.md](docs/LOCUS-MODULE.md) | **Locus**: On-Premise-RAG-Modul (Domäne klinische Bioinformatik, Indizes, BUSL) |

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
Kommerzielle Nutzung: contact@synapticfour.com

Kontakt: [contact@synapticfour.com](mailto:contact@synapticfour.com)

---
