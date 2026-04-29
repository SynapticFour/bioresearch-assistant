## Compliance & Sicherheit – Kurzüberblick

**Stand:** März 2026 — **Hinweis:** Dies ist eine technische Zusammenfassung,
keine Rechtsberatung und keine Bestätigung formaler Zertifizierungen.

---

### 1. Datenschutz & DSGVO (technische Sicht)

- On‑Premise‑Betrieb als Standard (Datenverarbeitung im eigenen Rechenzentrum).
- Pseudonymisierung von Texten (Microsoft Presidio) mit:
  - verschlüsselter Speicherung von Mappings (AES‑basiert),
  - Audit‑Logs für Pseudonymisierung und De‑Pseudonymisierung,
  - konfigurierter Zugriff („owner“, „team“, „admin“).
- Datenisolation über `ISOLATION_MODE` (user / team / open).
- Exportfunktionen (FAIR‑Export, JSON/ZIP), die Betroffenenrechten
  technisch unterstützen können (Auskunft, Löschung, Portabilität).

Ob ein Einsatz „DSGVO-konform“ ist, hängt vom jeweiligen Szenario,
Vertragssituation und den Verantwortlichen beim Betreiber ab.

---

### 2. Externe Dienste & Datensouveränität

- **Ollama (lokales LLM)**:
  - Standardempfehlung für klinische Szenarien.
  - Modell läuft lokal; keine KI‑Texte verlassen das System.
- **Anthropic API (Claude)**:
  - Optional für Forschung; Texte werden in ein Drittland übertragen (USA).
  - Für produktiven Einsatz sind zusätzliche rechtliche Schritte nötig
    (z. B. SCCs, DPIA, Verträge mit dem Anbieter).
- **PubMed / externe Kataloge**:
  - Suchanfragen werden extern verarbeitet; PII‑Prüfung in der UI warnt
    vor potentiell sensitiven Inhalten.

---

### 3. GAIA‑X, GA4GH, FAIR – technische Alignment‑Punkte

- **GAIA‑X**:
  - Architektur „GAIA‑X ready by design“ (Self‑Description, OIDC, On‑Premise).
  - Keine GAIA‑X‑Zertifizierung; Alignment‑Details in `GAIA-X-ALIGNMENT.md`.
- **GA4GH**:
  - Implementierung orientiert sich an WES v1.1, DRS und Phenopackets v2.
  - Endpunkte sind in `DEVELOPER-GUIDE.md` beschrieben.
- **FAIR**:
  - FAIR‑Export mit Score, Metadaten und optionalem Zenodo‑Upload.
  - Report dient als Hilfsmittel; keine Garantie einer bestimmten FAIR‑Bewertung
    durch Dritte.

---

### 4. Sicherheit (hochlevel)

- Verschlüsselung:
  - Transport: TLS (abhängig von Infrastruktur),
  - Pseudonymisierungs‑Mappings: AES‑256‑basiert,
  - DB‑Passwörter: lange zufällige Secrets.
- Zugriffskontrolle:
  - OIDC/JWT‑basierte Authentifizierung,
  - Scope‑Filter in allen datenführenden Endpunkten.
- Logging & Audit:
  - Pseudonymisierung, De‑Pseudonymisierung, FAIR‑Export.

Weitere Details: `SECURITY.md` und `AUDIT-REPORT.md`.

---

### 5. Pflichten der Betreiber:innen (Auszug)

Vor Go‑Live sollten Betreiber*innen u. a. prüfen:

- Datenschutz-Folgenabschätzung (DPIA/DSFA) und Verzeichnis der Verarbeitung.
- Verträge (AVV, BAA etc.) mit Hosting‑Provider und ggf. Synaptic Four.
- Technische Maßnahmen: Verschlüsselung at rest, Backups, Monitoring.
- Rollen & Rechte: OIDC‑Integration, `ISOLATION_MODE`, Team‑Zuweisungen.

Die Verantwortung für Rechtskonformität und Informationssicherheit
liegt immer bei den verantwortlichen Stellen des jeweiligen Einsatzes.

