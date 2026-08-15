# Sicherheitsrichtlinie — BioResearch Assistant

## Unterstützte Versionen

| Version | Support |
|---------|---------|
| 1.0.x   | ✅ Aktiv |
| < 1.0   | ❌ Kein Support |

## Sicherheitslücken melden

**Bitte keine öffentlichen GitHub Issues für Sicherheitslücken!**

### Kontakt
E-Mail: contact@synapticfour.com

### Was wir brauchen
- Beschreibung der Lücke
- Schritte zur Reproduktion
- Mögliche Auswirkungen
- Betroffene Versionen

### Was du erwarten kannst
- Bestätigung innerhalb 48 Stunden
- Status-Update innerhalb 7 Tagen
- Fix innerhalb 90 Tagen (je nach Schwere)
- Erwähnung im CHANGELOG (wenn gewünscht)

## Sicherheits-Architektur

### Authentifizierung
- OpenID Connect / OAuth2
- JWT (RS256/ES256) via JWKS, Issuer-Prüfung wenn `OIDC_ISSUER` gesetzt
- Session: httpOnly Cookie, kein Token in localStorage
- GA4GH Passport v1.2
- Produktion startet nicht ohne OIDC / mit `DEPLOYMENT=local` / `ISOLATION_MODE=open`

### Datenschutz
- Microsoft Presidio Pseudonymisierung
- Audit Trail für alle De-Pseudonymisierungen
- Konfigurierbare Datenisolation (user/team/open)
- Patienten-ID Erkennung ist konfigurierbar. Institutionsspezifische Formate können via CUSTOM_PATIENT_ID_PATTERNS konfiguriert werden. Siehe docs/USER-GUIDE.md für Details.
- Vollständige Datensouveränität mit Ollama

### Netzwerk
- Rate Limiting auf alle sensitiven Endpunkte
- CORS mit eingeschränkten Origins/Methods
- HTTPS in Produktion erforderlich

### Datenbank
- Parameterisierte Queries (SQLAlchemy ORM)
- Kein dynamisches SQL
- Pseudonymisierungs-Mappings verschlüsselt (AES-256-GCM, 32-Byte-Key)

## OWASP Top 10 – Maßnahmen

| Risiko | Maßnahme |
|--------|----------|
| A01 Broken Access Control | Alle datenliefernden Endpoints nutzen `get_current_user`; WES/BLAST/DRS/Notebook/PhenoFlow nutzen Scope-Filter. DRS-Objekte ohne ACL sind außerhalb `open` unsichtbar. |
| A02 Cryptographic Failures | PSEUDONYMIZATION_ENCRYPTION_KEY 64 Hex-Zeichen (AES-256-GCM); JWT_SECRET mind. 32 Zeichen bei Nutzung. |
| A03 Injection | BLAST-Sequenz: Whitelist IUPAC. BLAST-DB: Allowlist. WES `workflow_url`: Allowlist / Basename `.nf`. Notebook content max_length 500k. RAG Prompt-Injection-Filter. |
| A04 Insecure Design | Rate Limits: Notebook 30–60/min, AI-Assist 10/min, FAIR Download 5/min, Zenodo 3/min. |
| A05 Security Misconfiguration | Production-Guard `assert_runtime_hardened`. Kein Default-Passwort `bioresearch`. Kein `docker.sock` im Default-Compose. `/docs` in Produktion aus. Security-Header + HSTS. |
| A07 Auth Failures | Dev-User nur bei explizitem `DEPLOYMENT=local\|development\|test`; Produktion fail-closed. |
| A09 Logging | FAIR-Export/Zenodo nur user_id/title (kein Token, keine PII) geloggt. RAG: user_id, question_length, papers_used — keine Frage im Log (PII-Risiko). |
| A10 SSRF | Zenodo: nur feste Hosts (zenodo.org, sandbox.zenodo.org); BLAST `-db` Allowlist; keine user-kontrollierten Workflow-Pfade. |

### RAG Prompt-Injection Schutz (v0.1.0)

Alle Nutzereingaben, die ans LLM weitergegeben werden (Fragen, Notebook-Inhalte, Abstracts), werden auf Prompt-Injection-Patterns geprüft und gefiltert. Erkannte Muster werden durch `[FILTERED]` ersetzt und ein Log-Warning ausgegeben; die Anfrage wird nicht blockiert.

## Regulatorische Compliance

Siehe [docs/COMPLIANCE.md](docs/COMPLIANCE.md) für vollständige Übersicht aller relevanten Standards:

- DSGVO/GDPR inkl. DSK-Richtlinien Sept. 2025
- §393 SGB V (Cloud-Gesundheitsdaten)
- GDNG 2025
- GAIA-X: Design-Alignment, keine Zertifizierung (siehe COMPLIANCE.md)
- GA4GH Framework
- FAIR Prinzipien
- OWASP Top 10

## Sicherheitsmeldungen

Bitte melden Sie Sicherheitslücken an:
**contact@synapticfour.com**

Wir verpflichten uns zu:

- Bestätigung innerhalb 48 Stunden
- Behebung kritischer Lücken innerhalb 7 Tage
- Responsible Disclosure nach 90 Tagen

## Sichere Entwicklung

- **Backend:** `cd backend && ruff check app/ && ruff format --check app/`
- **Abhängigkeiten:** `pip-audit` (Python), `npm audit` (Frontend); bekannte CVEs beheben.
- **Keine sensiblen Daten in Logs:** Kein Token, kein Klartext von Patiententexten.

- Embeddings auf Railway nicht verfügbar (kein pgvector)
- Demo-Modus (ISOLATION_MODE=open) nicht für Produktion
- Anthropic API überträgt Texte nach USA
