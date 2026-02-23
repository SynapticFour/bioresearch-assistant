# Changelog

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/) und folgt [Semantic Versioning](https://semver.org/lang/de/).

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
