# Changelog

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/) und folgt [Semantic Versioning](https://semver.org/lang/de/).

## [1.4.2] - 2026-02-24

### Behoben
- Alembic: Fehlende Migration 011 für Notebooks Tabelle hinzugefügt
- Alembic: Multiple heads Problem behoben
- Git: Ambiguous 'main' Tag entfernt

## [1.4.1] - 2026-02-24

### Behoben
- Notebook Model: JSON Import fehlte in notebook.py → Alembic Migration schlug fehl
- Notebook Model: Vollständige Implementation auf main Branch

## [1.4.0] — 2026-02-24

### Neu
- **Research Notebook (ELN):** Markdown-basiertes elektronisches Laborbuch mit KI-Assistent, Auto-Save (2s Debounce) und Verknüpfungen zu Papers, Phenopackets und DRS-Dateien
- **FAIR Data Export:** Publikationsvorbereitung mit 3-Schritt Wizard, FAIR Compliance Score (F/A/I/R), DataCite + Dublin Core Metadaten, Data Management Plan und ZIP Export
- **Zenodo Integration:** Optionaler direkter Upload zu Zenodo (ZENODO_TOKEN in .env)
- **Multilinguales Embedding Modell:** paraphrase-multilingual-mpnet-base-v2 für bessere DE+EN semantische Suche
- **Semantischer Threshold Slider:** Kontinuierlicher Slider (0.3–1.8) für Suchgenauigkeit in Bibliothek
- **Similarity Score:** Prozentuale Ähnlichkeit pro Paper in semantischer Suche
- **Konfigurierbare Patienten-IDs:** CUSTOM_PATIENT_ID_PATTERNS in .env für institutionsspezifische Formate
- **Konfigurierbare Ollama Modelle:** Modellauswahl im Installer (mistral/phi3/gemma:2b/llama3.2:3b)
- **BLAST Datenbank Setup:** setup-blast-db.sh Script für interaktiven DB Download

### Verbessert
- Semantische Suche: Query Preprocessing extrahiert Keywords aus natürlichsprachigen Anfragen
- KI Zusammenfassungen: Collapsed/Expanded UI mit Sprach-Awareness (DE/EN)
- KI Zusammenfassungen: In DB gecacht — werden nur einmal generiert
- Pseudonymisierung: Deutsche Datumsformate (DD.MM.YYYY), Telefonnummern (0711-123456), Arzt-Nummern (Ärztin 4711)
- Literature Page: Separate Badges für PubMed (Keyword) vs Bibliothek (Semantisch)
- Phenopackets: Literature Search übergibt Phänotypen und Diagnosen als Suchbegriffe
- Installer: Bestehende Secrets werden bei Neuinstallation wiederverwendet
- Frontend API Timeout: 30s → 180s
- LLM Timeout: 30s → 180s

### Sicherheit (OWASP Top 10)
- Security Headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS
- BLAST Sequence Validator: IUPAC Zeichen only
- Workflow Allowlist: Nur erlaubte Pipelines
- CORS: Produktion Warning bei Wildcard
- Dev Mode Auth: Blockiert in Produktion
- Rate Limiting: Neue Endpoints (Notebook, FAIR Export, KI Assistent)
- Zenodo SSRF: URL Allowlist
- Audit Logging: FAIR Export Aktionen
- npm audit fix: Frontend Vulnerabilities

### Behoben
- OLLAMA_URL → OLLAMA_BASE_URL Mapping fix
- Sprache: Globaler React Context statt lokaler useState (Sprachänderung propagiert)
- BLAST Container: tail -f /dev/null idle command
- Nextflow: nf-core/blast → direktes Binary
- Semantischer Threshold: 0.7 → 1.0 default
- Summary Collapse: Inline CSS statt line-clamp
- README Badges: Statisch für privates Repo

## [1.3.0] — 2026-02-23

### Neu
- One-Command Installer (install.py / install.sh / install.bat)
- Vollständiges Docker Compose Setup mit pgvector, Ollama, BLAST, Nextflow
- Drag & Drop Datei-Upload in DRS mit Auto-Registrierung
- Bulk Import für Papers (ZIP/JSON/CSV)
- PubMed Query Validierung auf sensitive Daten
- De-Pseudonymisierung UI mit konfigurierbarem Zugriff
- Automatische Metadaten-Extraktion (DOI via CrossRef, FASTA, VCF Header)
- Geführte Phenopacket-Erstellung mit HPO-Suche
- Dynamische Feature Flags vom Backend
- Konfigurierbares Isolation-System (user/team/open)
- Management Scripts (start/stop/restart/update/backup/status)

### Verbessert
- Test-Isolation: SQLite In-Memory statt PostgreSQL
- JSONB zu JSON mit SQLite-Kompatibilität
- httpx Timeouts in Auth Service
- Rate Limiting via slowapi
- CORS eingeschränkt auf spezifische Methods/Headers
- DB Composite Indexes für Paper-Filter
- Dynamische Version aus APP_VERSION Umgebungsvariable

### Behoben
- Literature Stats Datenleck (Isolation verletzt)
- BLAST Endpunkte ohne Authentifizierung
- year Feldtyp (int statt str) in PubMedArticle
- user_id/team_id fehlten in store_paper()
- Null-Vektor statt NULL bei fehlendem Embedding
- Zirkuläre Imports in literature.py

### Sicherheit
- Rate Limiting auf sensitive Endpunkte
- Path Traversal Schutz in DRS Server-Pfad
- ZIP Bomb Schutz in Bulk Import
- Audit Trail für alle De-Pseudonymisierungen

## [1.2.0] — 2026-02-22

### Neu
- OpenID Connect / OAuth2 mit GA4GH Passport v1.2
- Multi-Provider: Keycloak, ELIXIR AAI, Azure AD, DFN-AAI
- Phenopackets Seite mit vollständigem UI
- Manuelle Paper-Eingabe in Bibliothek
- DRS Datei-Upload über UI
- Semantische Such-Hints (Demo vs. Vollinstallation)
- Heidelberg/UKHD Azure AD Integrations-Beispiel

### Verbessert
- DSGVO Klarstellung (Ollama vs. Anthropic API)
- Alle Deployment-Dokumentationen aktualisiert

### Behoben
- frontend/src/pages/LoginPage.tsx (toter Code entfernt)
- Ruff Linting Fehler behoben

## [1.1.0] — 2026-02-21

### Neu
- Bibliothek-Seite für gespeicherte Papers
- Semantische Suche mit pgvector cosine distance
- GA4GH WES v1.1 Pipeline Integration
- GA4GH DRS v1.2 Datei-Registry
- GAIA-X Self-Description
- Railway Demo Deployment
- Vercel Frontend Deployment
- Multi-Arch Docker Images (AMD64/ARM64)
- Graceful Fallbacks für Railway-Limitierungen

## [1.0.0] — 2026-02-20

### Neu
- Initiales Release
- FastAPI Backend mit PostgreSQL und pgvector
- React Frontend mit TypeScript
- Presidio Pseudonymisierung
- PubMed Literatursuche
- LLM Integration (Anthropic / Ollama)
- GA4GH Standards (WES, DRS, Phenopackets)
- GAIA-X Alignment
- Deutsche und Englische UI
