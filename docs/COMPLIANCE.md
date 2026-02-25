# Compliance & Regulatory Framework

## BioResearch Assistant — Synaptic Four

### Stand: Februar 2026 | Version: 1.4.2

---

## Übersicht

BioResearch Assistant wurde von Grund auf für den Einsatz in regulierten Umgebungen entwickelt. Diese Dokumentation beschreibt die Konformität mit relevanten Standards, Gesetzen und Frameworks.

---

## 1. DSGVO / GDPR Compliance

### 1.1 Rechtsgrundlagen (Art. 6, 9 DSGVO)

Gesundheits- und Genomdaten sind besondere Kategorien (Art. 9 DSGVO). BioResearch Assistant unterstützt folgende Rechtsgrundlagen:

| Szenario | Rechtsgrundlage |
|----------|----------------|
| Klinische Forschung | Art. 9 Abs. 2 lit. j DSGVO + §27 BDSG |
| Behandlung | Art. 9 Abs. 2 lit. h DSGVO |
| Einwilligung | Art. 6 Abs. 1 lit. a + Art. 9 Abs. 2 lit. a |

### 1.2 Pseudonymisierung (Art. 4 Nr. 5 DSGVO)

✅ Implementiert:

- Presidio-basierte PII-Erkennung
- Verschlüsselte Mapping-Speicherung (AES-256)
- Vollständiges Audit Log aller Operationen
- De-Pseudonymisierung nur mit expliziter Berechtigung
- Deutsche Sondermuster: Patienten-IDs, LANR, Daten

Rechtshinweis: Pseudonymisierte Daten gelten gemäß DSK-Richtlinien (Sept. 2025) als personenbezogen für den Empfänger — auch bei Drittlandübertragungen.

### 1.3 Drittlandtransfers (Art. 44-49 DSGVO)

⚠️ WICHTIG für Anthropic Claude API:

Die KI-Zusammenfassung via Anthropic API überträgt Daten in die USA (Drittland).

Empfehlung für produktiven Einsatz:

- Option A: Ollama (lokal) verwenden → kein Transfer
- Option B: Nur pseudonymisierte Abstracts senden
- Option C: EU-SCCs mit Anthropic abschließen

BioResearch Assistant zeigt in der UI einen Hinweis wenn Anthropic API aktiv ist.

### 1.4 Auftragsverarbeitung (Art. 28 DSGVO)

Wenn BioResearch Assistant für Dritte betrieben wird, ist ein Auftragsverarbeitungsvertrag (AVV) erforderlich. AVV-Template: docs/AVV-TEMPLATE.md

### 1.5 Verzeichnis der Verarbeitungstätigkeiten

BioResearch Assistant verarbeitet:

| Datenkategorie | Zweck | Speicherort |
|----------------|-------|-------------|
| Paper-Abstracts | Literaturrecherche | Lokal (PostgreSQL) |
| Phenopackets | Klinische Dokumentation | Lokal (PostgreSQL) |
| Pseudonym-Mappings | DSGVO-Compliance | Lokal (verschlüsselt) |
| Audit Logs | Nachvollziehbarkeit | Lokal (PostgreSQL) |
| Embeddings | Semantische Suche | Lokal (pgvector) |

### 1.6 Betroffenenrechte (Art. 15-22 DSGVO)

| Recht | Status | Umsetzung |
|-------|--------|-----------|
| Auskunft (Art. 15) | ✅ | Audit Log Export |
| Löschung (Art. 17) | ✅ | DELETE Endpoints |
| Portabilität (Art. 20) | ✅ | FAIR Export (JSON/ZIP) |
| Widerspruch (Art. 21) | ✅ | User Isolation |

---

## 2. Deutsches Recht

### 2.1 BDSG (Bundesdatenschutzgesetz)

§27 BDSG erlaubt Verarbeitung besonderer Kategorien für wissenschaftliche Forschung ohne Einwilligung wenn:

- Forschungszweck nicht anders erreichbar
- Schutzmaßnahmen implementiert (✅ Pseudonymisierung)
- Daten so früh wie möglich anonymisiert

### 2.2 §393 SGB V (Cloud-Verarbeitung)

Seit Juli 2024 gilt für Cloud-Verarbeitung von GKV-Sozialdaten:

- BSI C5 Type 2 Zertifizierung erforderlich
- Nur EU/EWR Rechenzentren

Status BioResearch Assistant:

- ✅ On-premise Installation: §393 SGB V nicht anwendbar
- ⚠️ Cloud-Deployment: BSI C5 Zertifizierung des Cloud-Anbieters prüfen (DFN-Cloud ✅, OTC ✅, Azure DE ✅)

### 2.3 Landesdatenschutzgesetze

Deutschland hat 16 Landesdatenschutzgesetze. On-premise Installation ermöglicht Betrieb unter dem jeweiligen Landesrecht. Empfehlung: Lokalen Datenschutzbeauftragten konsultieren.

### 2.4 GDNG (Gesundheitsdatennutzungsgesetz)

Seit Januar 2025 in Kraft. Ermöglicht erleichterte Nutzung von Gesundheitsdaten für Forschung. BioResearch Assistant unterstützt GDNG-konforme Pseudonymisierung und Audit-Trails.

---

## 3. GAIA-X Compliance

### 3.1 Standard Compliance (Level 0)

✅ Selbsterklärung möglich — bereits implementiert:

- Transparenz: Self-Description API (/api/v1/gaia-x)
- Datenschutz: DSGVO-konforme Verarbeitung
- Sicherheit: OWASP Top 10, Verschlüsselung
- Interoperabilität: GA4GH Standards, REST API
- Portabilität: FAIR Export, Standard-Formate

### 3.2 Label Level 1

Für Level 1 ist Selbsterklärung ausreichend. Empfohlene nächste Schritte:

1. GAIA-X Wizard verwenden (wizard.lab.gaia-x.eu)
2. Verifiable Credential erstellen (VC-JWT)
3. Bei GAIA-X Clearing House einreichen

### 3.3 Implementierte GAIA-X Anforderungen

| Kriterium | Status | Details |
|-----------|--------|---------|
| P1 Governance | ✅ | BUSL 1.1 Lizenz, Changelog |
| P2 Datenschutz | ✅ | DSGVO, Pseudonymisierung |
| P3 Sicherheit | ✅ | OWASP, Verschlüsselung, HTTPS |
| P4 Portabilität | ✅ | FAIR Export, Open Standards |
| P5 Transparenz | ✅ | Self-Description API |
| P6 Nachhaltigkeit | ⚠️ | Nicht bewertet |

---

## 4. GA4GH Standards

### 4.1 Implementierte Standards

| Standard | Version | Status |
|----------|---------|--------|
| WES (Workflow Execution Service) | v1.1 | ✅ |
| DRS (Data Repository Service) | v1.4 | ✅ |
| Phenopackets | v2.0 | ✅ |
| GA4GH Passports (AAI) | v1.0 | ✅ (optional) |

### 4.2 Framework for Responsible Sharing

GA4GH Framework Prinzipien — Umsetzung:

- Respect Persons: Pseudonymisierung, Betroffenenrechte
- Solidarity: FAIR Datenexport, Interoperabilität
- Fairness: Open Source (BUSL 1.1)
- Respect for Privacy: On-premise, lokale KI
- Reciprocity: GA4GH Standards implementiert
- Risk/Benefit: Audit Logs, Zugriffskontrollen

### 4.3 Data Use Ontology (DUO)

Empfehlung: DUO-Codes in FAIR Export und Phenopackets integrieren:

- DUO:0000007 disease specific research
- DUO:0000042 general research use
- DUO:0000011 population origins or ancestry research

---

## 5. Internationale Standards

### 5.1 FAIR Prinzipien

| Prinzip | Status | Umsetzung |
|---------|--------|-----------|
| Findable | ✅ | DOI via Zenodo, DataCite |
| Accessible | ✅ | REST API, DRS |
| Interoperable | ✅ | GA4GH, JSON-LD, Dublin Core |
| Reusable | ✅ | Lizenzen, DMP, Metadaten |

### 5.2 ISO/IEC 27001 (Informationssicherheit)

Relevante Kontrollen implementiert:

- A.8 Asset Management: Audit Logs ✅
- A.9 Access Control: User Isolation ✅
- A.10 Kryptographie: AES-256, HTTPS ✅
- A.12 Betriebssicherheit: Docker, Backups ✅
- A.14 Systementwicklung: OWASP Review ✅
- A.16 Incident Management: Error Logging ✅
- A.18 Compliance: DSGVO, GA4GH ✅

### 5.3 HIPAA (USA)

Für US-Kunden relevant:

- PHI Pseudonymisierung ✅
- Audit Logs ✅
- Verschlüsselung at rest und in transit ✅
- Zugriffskontrolle ✅

Hinweis: Vollständige HIPAA-Compliance erfordert BAA mit dem Betreiber.

### 5.4 ICH GCP E6(R3) (Klinische Studien)

Für klinische Forschung:

- Audit Trail ✅
- Datensicherheit ✅
- Pseudonymisierung ✅
- FAIR Export für eCRF-Kompatibilität ✅

---

## 6. Technische Sicherheitsmaßnahmen

### 6.1 Verschlüsselung

| Bereich | Methode | Standard |
|---------|---------|----------|
| Daten in Ruhe | Fernet (AES-128-CBC) | NIST |
| Daten in Transit | TLS 1.2+ | BSI TR-02102 |
| Passwörter | secrets.token_urlsafe(64) | OWASP |
| Pseudonym-Mappings | AES-256 | NIST |

### 6.2 Zugriffskontrolle

- OIDC/JWT Authentifizierung
- Rollenbasierte Isolation (User/Team/Open)
- Rate Limiting (slowapi)
- Security Headers (OWASP)

### 6.3 Audit

- Vollständiges Audit Log aller Pseudonymisierungen
- De-Pseudonymisierungen protokolliert
- FAIR Export Aktionen protokolliert
- Log-Retention: konfigurierbar

---

## 7. Empfehlungen für Produktionsbetrieb

### 7.1 Vor dem Go-Live

☐ Datenschutz-Folgenabschätzung (DSFA/DPIA) gemäß Art. 35 DSGVO durchführen  
☐ AVV mit Synaptic Four abschließen (Template: docs/AVV-TEMPLATE.md)  
☐ Lokalen Datenschutzbeauftragten einbinden  
☐ Verzeichnis der Verarbeitungstätigkeiten (VVT) aktualisieren  
☐ OIDC Provider konfigurieren (kein Dev-Mode!)  
☐ CORS_ORIGINS einschränken

### 7.2 KI-Konfiguration

| Modus | Datenschutz | Empfehlung |
|-------|-------------|------------|
| Ollama (lokal) | ✅ Optimal | Für Gesundheitsdaten |
| Anthropic API | ⚠️ USA-Transfer | Nur pseudonymisierte Daten |
| Kein KI | ✅ Optimal | Maximale Kontrolle |

### 7.3 Cloud vs. On-Premise

| Deployment | §393 SGB V | DSGVO | Empfehlung |
|------------|------------|-------|------------|
| On-premise | ✅ | ✅ | Kliniken |
| DFN-Cloud | ✅ | ✅ | Unis |
| OTC (Telekom) | ✅ | ✅ | Unternehmen |
| Azure DE | ✅ | ✅ | Enterprise |
| US-Cloud | ❌ | ⚠️ | Nicht empfohlen |

---

## 8. Roadmap Compliance

| Version | Geplant | Feature |
|---------|---------|---------|
| 1.4.x | 2026 Q1 | AVV-Template fertigstellen |
| 1.5.0 | 2026 Q2 | GAIA-X Level 1 Credential |
| 1.5.0 | 2026 Q2 | DUO-Codes in Phenopackets |
| 1.6.0 | 2026 Q3 | BSI C5 Self-Assessment |
| 2.0.0 | 2026 Q4 | ISO 27001 Zertifizierung |

---

## 9. Kontakt & Verantwortlichkeit

**Verantwortlicher (Art. 4 Nr. 7 DSGVO):**  
Synaptic Four  
[Adresse]  
datenschutz@synapticfour.de

**Technisch-organisatorische Maßnahmen (TOM):**  
Auf Anfrage: tom@synapticfour.de

**Sicherheitsmeldungen:**  
security@synapticfour.de  
(PGP Key auf Anfrage)

---

*Dieses Dokument wird bei wesentlichen Änderungen der Rechtslage aktualisiert. Letzte Überprüfung: Februar 2026.*  
*Kein Rechtsrat — für verbindliche Einschätzung deutschen IT-Anwalt konsultieren.*
