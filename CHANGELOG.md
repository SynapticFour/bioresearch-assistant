# Changelog
BioResearch Assistant — Synaptic Four
Format: [Keep a Changelog](https://keepachangelog.com)
Versioning: [Semantic Versioning](https://semver.org)

---

## [Unreleased]

## [0.2.2] - 2026-10-03

- **Service registry lookup** — `SERVICE_REGISTRY_URL` resolves DRS (`drsservice`) and WES. A missing `stale` field is fresh. Several fresh rows are an error unless a service id or organization is set. An empty host allowlist does not restrict ordinary hosts and is unsafe for a public deployment. Loopback, link-local, and cloud metadata stay blocked unless that host is listed. The service URL must use the registry URL's scheme. A failed lookup with a static `FERRUM_*_URL` is logged as a static fallback.
- Production Compose starts Ollama only with `--profile ollama`. `LLM_PROVIDER=anthropic` or `openai_compatible` boots without that container. `/api/v1/health` stays `healthy` when the model server is absent.
- OIDC and RAM notes label what the unit tests cover and what was not executed (no live Keycloak or broker login; RAM figures are Compose limits, not a measured RSS).

- Optional module `modules/variant_interpretation/`: juxtaposes a Locus RAG source list with Ferrum DRS/WES technical metadata only when `LOCUS_ENABLED` and both `FERRUM_DRS_URL` and `FERRUM_WES_URL` are set. Otherwise it stays inactive and does not raise. No recommendation, no diagnosis, no new data source.
- Docs: supported versions in [SECURITY.md](SECURITY.md) are **0.2.x** (v1.0.0 remains a published mistake tag). DPA/AVV is on request — there is no `docs/AVV-TEMPLATE.md` in this tree.
- HelixTest patch `0001-default-bearer-for-confidential-drs-wes.patch` regenerated against suite SHA `4a10e12` (`HELIXTEST_DEFAULT_BEARER` on `get_builder` / `post_json`).
- Release workflow writes notes to `release-notes.md` and uses `body_path` (git log bodies can contain `EOF` and broke `GITHUB_OUTPUT`).
- `make verify-release` is the local gate before a tag. Push to `main` and pull requests run the secret scan and dependency review. Product CI, conformance, CodeQL, `build-images.yml`, and deploys are `workflow_dispatch`. A `v*.*.*` tag runs the Release workflow: GHCR backend and frontend images, plus the offline bundle on the GitHub Release. The models bundle stays a manual dispatch.

### Security

- **urllib3 2.8.0** — PYSEC-2026-4175 (HTTPS proxy TLS configuration ignored or overridden), PYSEC-2026-4176 (chunked deflate streaming can loop), PYSEC-2026-4177 (unbounded chunk-size line). `requirements.txt` already allowed `>=2.5.0,<3`. The lock pin moved from 2.7.0.
- **axios 1.20.0 and DOMPurify 3.4.16** — production `npm audit` reported high-severity axios issues through 1.19.0 and a DOMPurify hook issue in 3.4.13–3.4.15. The lock now has the patched releases inside the existing ranges. `react-router` 6.30.6 still has two moderate advisories whose non-breaking fix is not published; the 7.18.4 upgrade is a major and is not in this tag. `npm audit --omit=dev --audit-level=high` is the release gate.
- **Not upgraded in this tag.** `transformers` 4.57.6 still has PYSEC-2026-3929 (`save_pretrained` path traversal, fix 5.10.0) and PYSEC-2026-4174 (custom generation code downloaded before trust consent; pip-audit listed no fix). `sentence-transformers` 2.7.0 still has PYSEC-2026-4164 (local model load bypasses `trust_remote_code`, fix 5.6.0). Those fixes are 5.x majors. `make verify-release` ignores those three ids and the older transformers ids already recorded on this line. spaCy `de-core-news-sm` and `en-core-web-sm` are not on PyPI, so pip-audit skips them.

## [0.2.1] - 2026-08-17

Suite join tag (Ferrum HTTP proxy + visa-verify + HelixTest pin). Git tag `v0.2.1`.

- Optional Ferrum DRS/WES HTTP proxy (`maybe_proxy_ferrum`) when `FERRUM_*` URLs are set. Tag **v0.2.0** does not include this.
- Commercial path: [COMMERCIAL.md](docs/COMMERCIAL.md). BRA stays a separate license; no combo SKU.
- HelixTest pin **v0.1.3** (`1832c04`).
- BUSL Change Date: four years from each version (no longer `2030-03-01`).
- README badges: GAIA-X / DSGVO are **not certified**.
- Nested GA4GH visa JWTs (`ga4gh_passport_v1`) are signature-verified (broker JWKS, then visa `iss`). Failed visas are dropped. Dataset bytes stay Ferrum’s job when `FERRUM_*` URLs are set.
- JupyterLite-class compute notebooks (nbformat v4 / Pyodide in the SPA). Optional JupyterHub sidecar without `DATABASE_URL`. No JupyterHub in Ferrum, no Colab.
- Institute IdP profiles (`OIDC_PROFILE`: Keycloak, Entra, LS Login, broker): groups isolation, RP-initiated logout, Entra without Passport scope. BRA does not issue Passports.

## [0.2.0] - 2026-08-15

Pre-1.0 release. The March 2026 initial tag was published as v1.0.0 by mistake.

### Added

- **`make prove`** — backend pytest without Docker and without the coverage gate (that remains CI).

### Security (Uniklinik-Bar)

- Production start refuses unauthenticated local auth, `ISOLATION_MODE=open`, CORS `*`, missing OIDC, and default DB password `bioresearch`.
- OIDC callback sets an httpOnly session cookie and redirects to the SPA (`/auth/callback`); tokens are not returned as JSON.
- WES/BLAST/PhenoFlow/DRS/notebook queries are tenant-scoped; owner-less workflow runs are rejected outside `open`.
- BLAST databases and local `.nf` paths are allowlisted; HelixTest TRS stubs require `WES_HELIXTEST_STUBS=1`.
- Markdown preview is sanitized (DOMPurify). Docker socket removed from default compose (optional DiD overlay only).
- Nextflow install pinned to a GitHub release tag (no `curl | bash`).
- Operator checklist: [docs/deployment/UNIKLINIK.md](docs/deployment/UNIKLINIK.md).

- Locus (curated on-prem RAG): `locus_chunks` table, `LOCUS_ENABLED`, `GET/POST /api/v1/locus/*`, demo seed script — see [docs/LOCUS-MODULE.md](docs/LOCUS-MODULE.md).

### Security (supply chain, 2026-08-15)

- JWT verification uses PyJWT + cryptography (no python-jose / python-ecdsa).
- `cryptography` ≥50 (Presidio anonymizer pinned at 2.2.362 so 2.2.364 cannot cap below 50).
- `pytest` ≥9.0.3 with `pytest-asyncio` ≥1.3.
- GitHub Actions checkout/setup-python/setup-node v7, cache v6.
- Dependabot disabled again (unreviewed majors). Operator patching: `pip-audit` / `npm audit` in CI. Residual transformer 4.x advisories documented in [docs/SBOM.md](docs/SBOM.md).

## [0.1.0] - 2026-03-01

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
