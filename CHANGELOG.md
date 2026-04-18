# Changelog
BioResearch Assistant — Synaptic Four
Format: [Keep a Changelog](https://keepachangelog.com)
Versioning: [Semantic Versioning](https://semver.org)

---

## [Unreleased]

- Locus (curated on-prem RAG): `locus_chunks` table, `LOCUS_ENABLED`, `GET/POST /api/v1/locus/*`, demo seed script — see [docs/LOCUS-MODULE.md](docs/LOCUS-MODULE.md).

## [1.0.0] - 2026-03-01

Initiales Release von BioResearch Assistant.
Vollständige KI-gestützte Forschungsplattform
für biomedizinische Forschung — DSGVO-konform,
on-premise, Open Standards.

### Features

#### Literaturrecherche
- PubMed Integration mit Keyword-Suche
- PII-Erkennung vor Suchanfragen
- Paper-Speicherung in lokaler Bibliothek
- KI-Zusammenfassungen (DE/EN, gecacht)
- Bulk Import (CSV/JSON/ZIP)

#### Semantische Bibliothekssuche
- Multilinguales Embedding-Modell
  (paraphrase-multilingual-mpnet-base-v2, 768-dim)
- Vektorbasierte Ähnlichkeitssuche via pgvector
- Konfigurierbarer Threshold-Slider (0.3–1.8)
- Similarity Score pro Ergebnis (0–100%)
- Query Preprocessing (Stopwort-Extraktion)

#### RAG — Frag deine Bibliothek
- Natürlichsprachige Fragen an gespeicherte Papers
- LLM-generierte Prosa-Antworten mit Quellenangaben
- Kontext-Truncation (8000 Zeichen, Ollama-sicher)
- Vollständig lokal (Ollama) oder Anthropic API
- Prompt-Injection Schutz

#### Pseudonymisierung (DSGVO)
- Presidio-basierte PII-Erkennung
- Deutsche Sondermuster: LANR, Patienten-IDs,
  Datumsformate (DD.MM.YYYY), Telefonnummern
- Konfigurierbare Patienten-ID Patterns (.env)
- AES-256 verschlüsselte Mapping-Speicherung
- Vollständiges Audit Log
- De-Pseudonymisierung mit API-Key

#### Phenopackets v2
- GA4GH Phenopackets v2.0 Standard
- HPO Ontologie Integration (EBI API)
- Validierung, Export, Verknüpfung mit Literatur
- Direkte Literatursuche aus Phenopacket

#### DRS — Dateiverwaltung
- GA4GH DRS v1.4 Standard
- Upload bis 500MB (Drag & Drop)
- Große Dateien (>500MB) via Server-Pfad
- VCF Metadaten-Extraktion (Header-Parsing)
- FASTA, VCF, FASTQ, BAM, CRAM, BED, GFF

#### BLAST Sequenzsuche
- Direkte Binary-Ausführung (kein shell=True)
- IUPAC Sequenz-Validierung
- DB-Status Check vor Suche
- Setup Script (setup-blast-db.sh)
- Unterstützte DBs: 16S, nt, nr

#### Pipelines & Workflows (GA4GH WES)
- GA4GH WES v1.1 Standard
- Nextflow Pipeline Integration
- Async Subprocess Execution
- Status, Logs, Cancel

#### Research Notebook (ELN)
- Markdown-basiertes Laborbuch
- Auto-Save (2s Debounce)
- KI-Assistent (Zusammenfassung + Nächste Schritte)
- KI liest verknüpfte Papers als Kontext
- Verknüpfung: Papers, DRS, Phenopackets
- Export als Markdown

#### FAIR Data Export
- 3-Schritt Wizard
- FAIR Compliance Score (F/A/I/R)
- DataCite + Dublin Core Metadaten
- Data Management Plan Template
- ZIP Download
- Optionaler Zenodo Upload (DOI)

#### Sicherheit (OWASP Top 10)
- Security Headers (X-Content-Type-Options,
  X-Frame-Options, Referrer-Policy, HSTS)
- BLAST Sequenz-Validator (IUPAC only)
- Workflow Allowlist
- CORS Production Warning
- Dev Mode Auth blockiert in Produktion
- Rate Limiting (slowapi) auf allen Endpoints
- Zenodo SSRF URL Allowlist
- Prompt-Injection Schutz (RAG)
- Vollständiges Audit Logging

#### Standards & Compliance
- DSGVO / GDPR konform
- §393 SGB V (On-premise)
- GDNG 2025
- GAIA-X Standard Compliance
- GA4GH WES v1.1, DRS v1.4, Phenopackets v2.0
- FAIR Prinzipien
- OWASP Top 10
- HIPAA (technisch)
- ICH GCP E6(R3)
- EHDS-ready (Pflichten ab 2029)
- NIS2 Supply Chain ready

#### Infrastruktur
- FastAPI + PostgreSQL 16 + pgvector
- React + TypeScript + Tailwind CSS
- Ollama (lokal) oder Anthropic API
- Docker Compose (One-Command Install)
- Alembic Datenbankmigrationen
- Railway / Vercel Deployment Support

---

## Roadmap

### [1.1.0] — Hybrid Search & Collaboration
Geplant: 2026 Q2

- Hybrid Search (Vektor + Keyword kombiniert)
- Team Collaboration im ELN
  (Notebooks teilen, kommentieren)
- VCF → Literatursuche Button
  (Gen-Extraktion aus VCF-Header)
- Notebook Templates

### [1.2.0] — Platform & Compliance
Geplant: 2026 Q3

- Version History im ELN
- GAIA-X Level 1 Verifiable Credential
- BSI C5 Self-Assessment
- Data Use Ontology (DUO) in Phenopackets
- Notebook Export als PDF

### [2.0.0] — Enterprise & Genomic Privacy
Geplant: 2027 Q1

- Crypt4GH: Verschlüsselung genomischer Daten
  nach GA4GH Standard (hg-Crypt4GH)
- ISO 27001 Zertifizierung
- EHDS Secondary Use Compliance (2029 vorbereiten)
- Multi-Tenant Architektur
- SSO Enterprise Integration

---
