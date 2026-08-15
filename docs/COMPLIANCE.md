# Compliance & Regulatory Framework

## BioResearch Assistant — Synaptic Four

### Stand: August 2026 | Version: 0.2.0

> **Wichtiger Hinweis (kein Rechtsrat):**
> Dieses Dokument beschreibt technische und organisatorische Maßnahmen,
> die den datenschutzfreundlichen Einsatz des BioResearch Assistant
> unterstützen sollen. Es stellt **keine verbindliche Aussage zur
> Rechtskonformität** eines konkreten Einsatzes dar und ersetzt keine
> individuelle rechtliche Beratung. Ob eine Verarbeitung „DSGVO-konform“
> ist, hängt von Nutzungskontext, Verantwortlichen, Verträgen und
> weiteren Umständen ab.
>
> Zusätzlich: Diese Software ist in dieser Dokumentation als
> Forschungs-/Datenplattform beschrieben und nicht als automatisch
> zertifiziertes Medizinprodukt deklariert. Eine etwaige regulatorische
> Einordnung ist durch die verantwortliche Organisation gesondert zu prüfen.

---

## Übersicht

BioResearch Assistant wurde von Grund auf für den Einsatz in regulierten Umgebungen entwickelt. Diese Dokumentation beschreibt die Konformität mit relevanten Standards, Gesetzen und Frameworks.

---

## 1. DSGVO / GDPR – Technische Unterstützung

### 1.1 Rechtsgrundlagen (Art. 6, 9 DSGVO)

Gesundheits- und Genomdaten sind besondere Kategorien (Art. 9 DSGVO).
BioResearch Assistant kann in Szenarien eingesetzt werden, in denen sich
Verantwortliche auf folgende Rechtsgrundlagen stützen **möchten**:

| Szenario | Rechtsgrundlage |
|----------|----------------|
| Klinische Forschung | Art. 9 Abs. 2 lit. j DSGVO + §27 BDSG |
| Behandlung | Art. 9 Abs. 2 lit. h DSGVO |
| Einwilligung | Art. 6 Abs. 1 lit. a + Art. 9 Abs. 2 lit. a |

### 1.2 Pseudonymisierung (Art. 4 Nr. 5 DSGVO)

Technisch umgesetzt sind u. a.:

- Presidio-basierte PII-Erkennung
- Verschlüsselte Mapping-Speicherung (AES-256)
- Vollständiges Audit Log aller Operationen
- De-Pseudonymisierung nur mit expliziter Berechtigung
- Deutsche Sondermuster: Patienten-IDs, LANR, Daten

Rechtshinweis: Pseudonymisierte Daten gelten gemäß DSK-Richtlinien (Sept. 2025) als personenbezogen für den Empfänger — auch bei Drittlandübertragungen.

### 1.3 Drittlandtransfers (Art. 44-49 DSGVO)

⚠️ WICHTIG für Anthropic Claude API:

Die KI-Zusammenfassung via Anthropic API überträgt Daten in die USA (Drittland).

Empfehlung für produktiven Einsatz (unverbindlich, ohne Gewähr):

- Option A: Ollama (lokal) verwenden → kein Transfer
- Option B: Nur pseudonymisierte Abstracts senden
- Option C: EU-SCCs mit Anthropic abschließen

BioResearch Assistant zeigt in der UI einen Hinweis wenn Anthropic API aktiv ist.

### 1.4 Auftragsverarbeitung (Art. 28 DSGVO)

Wenn BioResearch Assistant für Dritte betrieben wird, **kann** ein
Auftragsverarbeitungsvertrag (AVV) erforderlich sein. Ob dies im
Einzelfall zutrifft, hängt von Rollenverteilung und Einsatzszenario ab.
Ein AVV-Template in `docs/AVV-TEMPLATE.md` dient lediglich als
Startpunkt und ersetzt keine anwaltliche Prüfung.

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

| Recht | Technische Unterstützung | Beispiel |
|-------|--------------------------|----------|
| Auskunft (Art. 15) | Exportfunktionen, Audit-Logs | Audit Log Export |
| Löschung (Art. 17) | Delete-Endpunkte | DELETE /… APIs |
| Portabilität (Art. 20) | Exportfunktionen | FAIR Export (JSON/ZIP) |
| Widerspruch (Art. 21) | Datenisolation, Filter | User/Team Isolation |

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

## 3. GAIA-X – Architektonische Ausrichtung

### 3.1 Architektur-Alignment („Level 0“)

Die Architektur des BioResearch Assistant orientiert sich an
GAIA‑X‑Prinzipien. Eine **formale GAIA‑X Zertifizierung liegt nicht vor**.

- Transparenz: Self-Description API (/api/v1/gaia-x)
- Datenschutz: Pseudonymisierung, Audit-Logs, On‑Premise‑Option
- Sicherheit: Maßnahmen entlang OWASP Top 10, Verschlüsselung
- Interoperabilität: GA4GH Standards, REST API
- Portabilität: FAIR Export, Standard-Formate

### 3.2 Perspektive „Label Level 1“

Für ein GAIA‑X‑Label sind zusätzliche organisatorische und rechtliche
Schritte nötig. Mögliche nächste Schritte (aus Sicht der Betreiber):

1. GAIA-X Wizard verwenden (wizard.lab.gaia-x.eu)
2. Verifiable Credential erstellen (VC-JWT)
3. Bei GAIA-X Clearing House einreichen

### 3.3 Ausgewählte GAIA-X Anforderungen (technische Sicht)

| Kriterium | Technische Maßnahmen (Beispiele) |
|-----------|----------------------------------|
| P1 Governance | Versionierung, Changelog, Lizenz (BUSL 1.1) |
| P2 Datenschutz | Pseudonymisierung, Audit, On‑Premise‑Option |
| P3 Sicherheit | Verschlüsselung, AuthN/Z, OWASP-orientiertes Review |
| P4 Portabilität | Docker, Standardprotokolle, FAIR Export |
| P5 Transparenz | Self‑Description API, offene Schnittstellen |
| P6 Nachhaltigkeit | Nicht bewertet, kundenspezifisch |

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

Ausgewählte Kontrollen werden technisch unterstützt, eine formale
ISO‑27001‑Zertifizierung liegt **nicht** vor:

- A.8 Asset Management: Audit Logs ✅
- A.9 Access Control: User Isolation ✅
- A.10 Kryptographie: AES-256, HTTPS ✅
- A.12 Betriebssicherheit: Docker, Backups ✅
- A.14 Systementwicklung: OWASP Review ✅
- A.16 Incident Management: Error Logging ✅
- A.18 Compliance: DSGVO, GA4GH ✅

### 5.3 HIPAA (USA)

Für US-Kunden können folgende Funktionen beim Erreichen
von HIPAA-Anforderungen unterstützen:

- PHI Pseudonymisierung ✅
- Audit Logs ✅
- Verschlüsselung at rest und in transit ✅
- Zugriffskontrolle ✅

Hinweis: Eine vollständige HIPAA‑Compliance erfordert zusätzliche
vertragliche, organisatorische und technische Maßnahmen (z. B. BAA)
und kann nicht allein durch die Software gewährleistet werden.

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
| Daten in Ruhe | AES-256-GCM (Pseudonym-Mappings) | NIST SP 800-38D |
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

### 6.4 Encryption at Rest (Art. 32 DSGVO — Betreiberpflicht)

**Option C: Cloud-Provider Encryption**

AWS EBS, Azure Managed Disks, OTC EVS bieten transparente Disk-Verschlüsselung. Bei BSI C5-zertifizierten Anbietern standardmäßig aktiv.

**Konsequenz ohne Encryption at Rest**

Bei einem Datenleck ohne Verschlüsselung:

- Meldepflicht an Aufsichtsbehörde (Art. 33)
- Meldepflicht an Betroffene (Art. 34)
- Bußgeldrisiko bis 4% des Jahresumsatzes
- Mit Verschlüsselung: Art. 34 Meldung an Betroffene entfällt in der Regel

**Empfehlung Synaptic Four:** Installation Guide um Encryption at Rest Sektion erweitern. Kunden auf diese Pflicht explizit hinweisen.

---

## 7. Empfehlungen für Produktionsbetrieb

### 7.1 Vor dem Go-Live (Checkliste für Betreiber:innen)

Die folgende Liste bietet eine technische Orientierung und ersetzt keine
individuelle Beratung:

- ☐ Datenschutz-Folgenabschätzung (DSFA/DPIA) gemäß Art. 35 DSGVO prüfen und ggf. durchführen
- ☐ Rollenklärung: Verantwortlicher / Auftragsverarbeiter / ggf. gemeinsame Verantwortlichkeit
- ☐ Vertragslage prüfen (z. B. AVV/BAA mit Hosting‑Provider und ggf. Synaptic Four)
- ☐ Lokalen Datenschutzbeauftragten und Informationssicherheitsbeauftragten einbinden
- ☐ Verzeichnis der Verarbeitungstätigkeiten (VVT) aktualisieren
- ☐ OIDC Provider konfigurieren (kein Dev‑Mode in Produktion)
- ☐ CORS_ORIGINS auf notwendige Domains einschränken
- ☐ Verschlüsselung at rest (Datenbank/Volumes) und Backups implementieren
- ☐ Monitoring und Incident‑Prozess (z. B. Log‑Überwachung, Alarmierung) etablieren

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

## 12. NIS2 Direktive / NIS2UmsuCG

### Status Deutschland

Das NIS2-Umsetzungsgesetz (NIS2UmsuCG) ist am 6. Dezember 2025 in Kraft getreten — ohne Übergangsfrist. Betroffene Unternehmen mussten sich bis 6. März 2026 beim BSI registrieren.

### Gilt NIS2 für eure Kunden?

| Kundentyp | NIS2 betroffen? | Begründung |
|-----------|-----------------|------------|
| Unikliniken (Charité, UKHD...) | ✅ Ja | Gesundheitssektor, Größe |
| Große Pharma/CROs (>50 MA) | ✅ Ja | Gesundheitssektor |
| Universitäten/Forschungsgruppen | ⚠️ Wahrscheinlich nein | Bildungseinrichtungen ausgenommen |
| Kleine CROs (<50 MA, <10M€) | ✅ Nein | Unter Größenschwelle |
| de.NBI / Helmholtz | ⚠️ Prüfen | Abhängig von Einordnung |

### Gilt NIS2 für Synaptic Four?

Aktuell (Startup-Phase): Wahrscheinlich nein — unter der Größenschwelle (50 MA / 10M€). Bei Wachstum: Prüfung erforderlich.

### Was NIS2-Kunden von Software erwarten

Kunden die selbst unter NIS2 fallen, werden von ihren Softwarelieferanten (Supply Chain Security) verlangen:

- Vulnerability Disclosure Policy ✅
- Patch-Management Prozess ✅
- Security Incident Response ✅
- SBOM (Software Bill of Materials) ✅

BioResearch Assistant erfüllt diese Anforderungen bereits weitgehend.

### NIS2 und ISO 27001

Unternehmen mit ISO 27001 erfüllen ca. 70–80% der NIS2-Anforderungen. BioResearch Assistant Roadmap:

- 2026: BSI C5 Self-Assessment
- 2026/27: ISO 27001 Zertifizierung

### Verkaufsargument

Für NIS2-betroffene Kunden ist BioResearch Assistant mit:

- On-premise Deployment
- Vollständigem Audit Log
- OWASP-reviewed Codebase
- Security Headers
- Incident Reporting Unterstützung

…ein deutlich besseres Risikoprofil als Cloud-Alternativen mit US-Hosting.

---

## 9. Roadmap (Compliance-relevante Versionen)

| Version | Geplant | Feature |
|---------|---------|---------|
| 1.1.0 | 2026 Q2 | Hybrid Search, ELN Collaboration |
| 1.2.0 | 2026 Q3 | GAIA-X Level 1, DUO Codes |
| 2.0.0 | 2027 Q1 | Crypt4GH, ISO 27001 |

---

## 10. Kontakt & Verantwortlichkeit

**Verantwortlicher (Art. 4 Nr. 7 DSGVO):**
Synaptic Four
[Adresse]
contact@synapticfour.com

**Technisch-organisatorische Maßnahmen (TOM):**
Auf Anfrage: contact@synapticfour.com

**Sicherheitsmeldungen:**
contact@synapticfour.com
(PGP Key auf Anfrage)

---

*Dieses Dokument wird bei wesentlichen Änderungen der Rechtslage aktualisiert. Letzte Überprüfung: März 2026.*
*Kein Rechtsrat — für verbindliche Einschätzung deutschen IT-Anwalt konsultieren.*
