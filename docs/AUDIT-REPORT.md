# Code Quality & Security Audit Report

**Projekt:** BioResearch Assistant
**Version:** 1.3.0
**Datum:** August 2026
**Erstellt von:** Synaptic Four
**Methode:** Automatisierte Analyse + manuelle Review

---

## Executive Summary

BioResearch Assistant wurde intern von Synaptic Four im Hinblick auf
Code-Qualität und Sicherheit überprüft. Dieses Dokument beschreibt eine
**interne technische Einschätzung**, keine unabhängige Zertifizierung
oder rechtliche Bewertung.

| Kategorie       | Einordnung (intern) | Details (Auszug) |
|----------------|----------------------|------------------|
| Sicherheit     | solide Basis         | OWASP-orientierter Review, Security Headers, Input Validation, SSRF-Schutz |
| Code-Qualität  | gut strukturiert     | Klare Schichten, Linting, Typisierung |
| Test-Coverage  | ausbaufähig          | Backend ~74 % Line Coverage; Frontend: Vitest-Sanitizer-Tests |
| Dokumentation  | umfangreich          | Benutzer-, Entwickler- und Compliance-Doku vorhanden |
| Datenschutz    | technisch vorbereitet| Pseudonymisierung, Audit, Isolation; rechtliche Bewertung bleibt Betreiber:in vorbehalten |
| GA4GH Standards| weitgehend umgesetzt | WES, DRS, Phenopackets (siehe Developer Guide) |
| Deployment     | vereinfacht          | One-Command Installer, Management-Skripte |

**Kurzfazit:** Aus technischer Sicht für den Einsatz in
Forschungsumgebungen geeignet, mit klar dokumentierten Einschränkungen
und ohne Anspruch auf formale Zertifizierung oder Rechtskonformität.

### Features (Auswahl v1.0.0)

| Feature | Bewertung | Kurzbeschreibung |
|---------|-----------|------------------|
| RAG — Frag deine Bibliothek | ⭐⭐⭐⭐⭐ | Rate limit, Scope, Prompt-Injection-Schutz |
| Research Notebook (ELN) | ⭐⭐⭐⭐☆ | Markdown-ELN, KI-Assistent, Auto-Save. Besonders für Labor-Tagebücher. |
| FAIR Export | ⭐⭐⭐☆☆ | Heuristischer FAIR-Check (nicht zertifiziert); DataCite/Zenodo-Export |

---

## 1. Sicherheitsanalyse

### 1.1 Authentifizierung & Autorisierung
- OpenID Connect / OAuth2 implementiert
- JWT Token Verifikation via JWKS
- GA4GH Passport v1.2 Support
- Dev-Modus mit Mock-User für Entwicklung
- Alle kritischen Endpunkte erfordern Authentifizierung

### 1.2 Eingabevalidierung
- Pydantic v2 für alle API Schemas
- Keine rohen SQL Strings (SQLAlchemy ORM)
- Input-Längen begrenzt (max_length auf Felder)
- Path Traversal Schutz in DRS Server-Pfad

### 1.3 Rate Limiting
- slowapi auf alle sensitiven Endpunkte
- PubMed: NCBI-konforme Rate Limits (3/Sekunde)
- Auth Login: 10/Minute
- Pseudonymisierung: 30/Minute
- Literatursuche: 20/Minute

### 1.4 Datenverschlüsselung
- Pseudonymisierungs-Mappings verschlüsselt (AES-256-GCM, nicht Fernet)
- DB-Verbindung via SSL (Produktions-Konfiguration)
- Bekannte Lücke: DRS Dateien nicht at-rest verschlüsselt (Roadmap v1.5)

### 1.5 CORS
- Eingeschränkte Origins (kein Wildcard in Produktion)
- Spezifische Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH
- Spezifische Headers: Authorization, Content-Type, Accept, Origin
- CORS: kein Wildcard in Produktion (`assert_runtime_hardened`); Credentials nur für bekannte Origins
- Session: httpOnly Cookie (`bra_access_token`), kein Token in localStorage
- Bekannte Frontend-Abhängigkeit: react-router 6.x hat moderate Advisories (GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg); CI blockiert high/critical. Upgrade auf Router 7 ist geplant.

### 1.6 Audit Trail
- Alle Pseudonymisierungen werden geloggt
- Alle De-Pseudonymisierungen werden geloggt (user_id, timestamp, mapping_id)
- Konfigurierbar: DEPSEUDO_ACCESS=owner/team/admin

### 1.7 OWASP-relevante Endpoints (Auswahl)

| Endpoint | Status | Maßnahmen |
|----------|--------|-----------|
| POST /library/rag | ✅ | Rate limit 10/min, get_scope_filter, Prompt-Injection-Schutz |

---

## 2. Code-Qualität

### 2.1 Architektur
- Klare Schichtentrennung: API / Service / Model
- Dependency Injection via FastAPI
- Async durchgängig implementiert (keine sync Blockaden)
- Railway-spezifische Stubs sauber isoliert
- Lazy Engine Initialization (keine Import-Seiteneffekte)

### 2.2 Linting & Formatting
- Ruff (Python): 0 Fehler
- TypeScript Strict Mode: aktiv
- Konsistente snake_case Benennung im Backend
- Konsistente camelCase Benennung im Frontend

### 2.3 Bekannte Code-Smells
- llm_service.py: summarize_paper() > 50 Zeilen (Refactoring geplant)
- wes_service.py: _execute_nextflow() komplex
- Einige Late Imports zur Vermeidung zirkulärer Imports

### 2.4 Technische Schulden (dokumentiert)
- year Feld: int in API, String(16) in DB (historisch) — Breaking Change in v2.0 geplant
- embedding_service_railway.py: 0% Test Coverage (Railway-spezifischer Stub, schwer testbar)

---

## 3. DSGVO & Datenschutz (technische Perspektive)

### 3.1 Datensouveränität

Zwei Modi sind dokumentiert und konfigurierbar:

Vollständige Souveränität (z. B. Kliniken, On‑Premise):
- LLM_PROVIDER=ollama — keine externen API Calls
- Alle Verarbeitung auf eigenem Server
- Keine Daten verlassen die Institution

Eingeschränkte Souveränität (z. B. externe KI-Dienste):
- LLM_PROVIDER=anthropic — Texte gehen nach USA
- PubMed/CrossRef — Suchanfragen nach außen
- System warnt automatisch bei PII in Suchanfragen

### 3.2 Pseudonymisierung
- Microsoft Presidio (produktionserprobtes NLP)
- Erkannte Entitäten: PERSON, DATE_TIME, PHONE_NUMBER, EMAIL_ADDRESS, LOCATION, IBAN_CODE, CREDIT_CARD, MEDICAL_LICENSE, MEDICAL_RECORD_NUMBER (konfigurierbar via CUSTOM_PATIENT_ID_PATTERNS in .env)
- Reversibel mit konfigurierbarem Zugriff
- Vollständiger Audit Trail

### 3.3 Datenisolation
- ISOLATION_MODE: user / team / open
- Automatische Team-Erkennung via Email-Domain
- GA4GH Passport AffiliationAndRole Support
- Alle DB-Abfragen mit Scope-Filter

### 3.4 PubMed Sicherheit
- Automatische PII-Erkennung in Suchanfragen
- Warnung vor dem Absenden wenn PII erkannt
- User kann Anfrage überarbeiten oder bestätigen

---

## 4. GA4GH Standards (Implementierungsstand)

### 4.1 Workflow Execution Service (WES) v1.1
- POST /ga4gh/wes/v1/runs
- GET /ga4gh/wes/v1/runs/{run_id}
- GET /ga4gh/wes/v1/runs/{run_id}/status
- GET /ga4gh/wes/v1/service-info
- Nextflow Integration (lokale Installation)

### 4.2 Data Repository Service (DRS) v1.3
- GET /ga4gh/drs/v1/objects/{object_id}
- POST /ga4gh/drs/v1/objects
- GET /ga4gh/drs/v1/service-info
- Unterstützte Formate: VCF, FASTA, BAM, FASTQ, BED

### 4.3 Phenopackets v2
- GA4GH Phenopacket Schema
- HPO Term Support mit Live-Suche
- OMIM Disease Links
- JSON-LD Export
- DSGVO-konforme Pseudonym-IDs erzwungen

### 4.4 GA4GH Passports v1.2
- ResearcherStatus Visa
- AffiliationAndRole Visa (Team-Erkennung)
- ControlledAccessGrants Visa

---

## 5. Test-Coverage

### Gesamtergebnis
Gesamt Coverage: 68%
Ziel: 80%+
Test-Isolation: Vollständig (SQLite In-Memory)
Externe Dependencies: Alle gemockt
CI/CD: GitHub Actions

### Gut abgedeckt (>80%)
- app/core/encryption.py 97%
- app/core/config.py 93%
- app/core/isolation.py 90%
- app/services/pseudonymization_service.py 90%
- app/services/pubmed_service.py 86%
- app/services/embedding_service.py 80%

### Verbesserungsbedarf (<60%)
- app/services/blast_service.py 17%
- app/api/v1/endpoints/health.py 31%
- app/core/auth.py 42%
- app/api/v1/endpoints/literature.py 43%
- app/services/hpo_service.py 38%
- app/services/embedding_service_railway.py 0%

### Fehlende Tests (Roadmap)
- Load Tests (k6 oder locust) — v1.4
- End-to-End Tests (Playwright) — v1.4
- BLAST Service Integration Tests — v1.4
- Auth Flow End-to-End — v1.4

---

## 6. Abhängigkeiten & Lizenzen

Alle Dependencies: MIT, Apache 2.0, BSD oder ähnlich.
Keine GPL-inkompatiblen Lizenzen.
Vollständige Liste: docs/SBOM.md

Letzte Sicherheits-Prüfung: 2026-08-15
pip-audit — blocking in CI; JWT via PyJWT/cryptography (no python-ecdsa).
npm audit — production `high+` in CI. Residual: react-router 6 moderate CVEs (v7 is a breaking upgrade, not taken).
sentence-transformers still pulls `transformers` 4.x; remaining transformer advisories that require 5.x or have no fix are listed in [SBOM.md](SBOM.md).

---

## 7. Deployment & Operations

### 7.1 One-Command Installation
```bash
./install.sh   # macOS / Linux
install.bat    # Windows
```
Installiert: PostgreSQL+pgvector, Backend, Frontend, Ollama, BLAST, Nextflow — vollständig konfiguriert.

### 7.2 Produktions-Readiness
- Health Check Endpunkt mit Feature Flags
- Ehrliche Feature-Anzeige (was wirklich verfügbar ist)
- Graceful Degradation (Railway Demo Fallbacks)
- Automatische Backup Scripts
- Management Scripts für Operations

### 7.3 Monitoring
- Basis-Logging implementiert (strukturiert)
- Fehlend: Prometheus Metriken (Roadmap v1.4)
- Fehlend: Sentry Error Tracking (Roadmap v1.5)
- Fehlend: Alerting (Roadmap v1.5)

---

## 8. Bekannte Einschränkungen & Roadmap

### Aktuell bekannte Einschränkungen

| # | Einschränkung | Schwere | Roadmap |
|---|---------------|---------|---------|
| 1 | Test Coverage 68% (Ziel: 80%) | Mittel | v1.4 |
| 2 | Keine Load Tests | Mittel | v1.4 |
| 3 | Kein Monitoring/Alerting | Mittel | v1.4-1.5 |
| 4 | DRS Dateien nicht at-rest verschlüsselt | Niedrig | v1.5 |
| 5 | Inter-Instanz GAIA-X Föderation fehlt | Niedrig | v2.0 |
| 6 | year: int/String Inkonsistenz DB vs. API | Niedrig | v2.0 |
| 7 | installer.py: noch nicht auf allen Plattformen getestet | Niedrig | v1.3.1 |

### Roadmap

v1.4 (geplant):
- Prometheus + Grafana Integration
- Load Tests mit k6
- End-to-End Tests mit Playwright
- Coverage auf 80%+

v1.5 (geplant):
- Sentry Error Tracking
- DRS Datei-Verschlüsselung at-rest
- Alerting (PagerDuty / E-Mail)

v2.0 (geplant):
- Inter-Instanz GAIA-X Föderation
- Breaking API Changes (/api/v2/)
- year als int in DB (Migration)
- Multi-Site Deployment

---

## 9. Bewertung für Kunden

### Empfohlen für
- Forschungsinstitute (mit Ollama)
- Universitäten (DFN-AAI Integration)
- Bioinformatik-Gruppen
- Nicht-klinische Studien
- Open-Science Projekte
- Pilotprojekte in Kliniken
- DFG-geförderte Forschungsprojekte (FAIR Export erfüllt DFG Anforderungen)
- de.NBI Partner Institutionen (GA4GH + FAIR Standards)

### Mit Einschränkungen
- Klinischer Betrieb mit Patientendaten: Ollama erforderlich; Penetration Test vor Produktiveinsatz empfohlen; Zusätzliche Validierung je nach Institution

### Nicht empfohlen
- Als Medizinprodukt (FDA/MDR reguliert)
- Ohne IT-Begleitung in der Erstinstallation

---

## 10. Engineering controls implemented (Februar 2026)

> **Kein Zertifikat / kein Rechtsrat:** Die Spalte „Umgesetzt?“ bedeutet nur, dass
> entsprechende **technische Kontrollen oder Features im Code/Doku vorhanden** sind
> (interne Einschätzung). Sie ist **keine** formale Zertifizierung, Akkreditierung,
> Konformitätsbewertung oder verbindliche Aussage zur Rechtskonformität eines
> konkreten Einsatzes. Ob ein Betrieb „DSGVO-konform“, „HIPAA-ready“ o. Ä. ist,
> hängt von Konfiguration, Verträgen und den Verantwortlichen vor Ort ab — siehe
> die Hedging-Hinweise in [docs/COMPLIANCE.md](COMPLIANCE.md).

| Rahmen / Standard | Umgesetzt? (Engineering) | Technische Details (Auszug) |
|-------------------|--------------------------|------------------------------|
| DSGVO/GDPR | ✅ Kontrollen vorhanden | Pseudonymisierung, Audit, Betroffenenrechte-Hilfen |
| BDSG §27 | ✅ Kontrollen vorhanden | Forschungsprivileg technisch unterstützt |
| §393 SGB V | ✅ On-premise-Pfad | Cloud: Anbieter/Betreiber prüfen |
| GDNG 2025 | ✅ Kontrollen vorhanden | Pseudonymisierung, Audit-Trail |
| DSK Sept. 2025 | ✅ Kontrollen vorhanden | Keine Klartextdaten an US-KI (bei Ollama-Pfad) |
| GAIA-X (Design-Alignment) | ✅ Kontrollen vorhanden | Self-Description API; keine formale GAIA-X-Zertifizierung |
| GAIA-X Level 1 | 🔜 geplant | Roadmap 2026 Q2 |
| GA4GH WES v1.1 | ✅ implementiert | Spezifikationsorientierte API |
| GA4GH DRS | ✅ implementiert | Spezifikationsorientierte API |
| GA4GH Phenopackets v2 | ✅ implementiert | Spezifikationsorientierte API |
| FAIR Prinzipien | ✅ Feature vorhanden | FAIR Export |
| OWASP Top 10 | ✅ Review (intern) | Review März 2026, RAG mit Prompt-Injection-Schutz |
| ISO 27001 | 🔜 geplant | Roadmap 2026 Q4 — kein ISO-Zertifikat |
| HIPAA | ⚠️ Teilkontrollen | Technisch orientiert; BAA/rechtliche Bewertung Betreiber:in |
| ICH GCP E6(R3) | ✅ Teilkontrollen | Audit Trail, Pseudonymisierung — kein GCP-Zertifikat |
| EHDS (2025/327) | 🔜 Orientierungsarbeit | Secondary Use ab 2029; kein EHDS-Zertifikat |
| NIS2 / NIS2UmsuCG | ✅ Supply-Chain-Hilfen | Kunden/Betreiber können direkt betroffen sein |
| Encryption at Rest | ⚠️ Betreiberpflicht | TOM-Dokumentation vorhanden; nicht überall at-rest |

Vollständige Einordnung und Hedging: [docs/COMPLIANCE.md](COMPLIANCE.md)

---

## 11. Kontakt & Support

**Synaptic Four**
E-Mail: contact@synapticfour.com
Security: contact@synapticfour.com
Web: https://www.synapticfour.com
GitHub: https://github.com/SynapticFour/bioresearch-assistant

---

*Dieser Report wird mit jedem Release aktualisiert.*
*Letzte Aktualisierung: März 2026, v1.0.0*
