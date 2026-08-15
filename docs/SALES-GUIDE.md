## Sales Guide – BioResearch Assistant

**Version:** 0.2.0 — **Lizenz:** BUSL 1.1 (Production use requires commercial license)
Dieses Dokument richtet sich an Vertrieb, Pre‑Sales und Gründer:innen.

---

### 1. Lizenzmodell & Positionierung

- **Lizenzmodell:**
  - Code ist **öffentlich einsehbar** (GitHub‑Repository).
  - Lizenz: **Business Source License 1.1 (BUSL 1.1)**
    - Nicht‑produktiver Einsatz (Forschung, Evaluation, Beiträge) ist erlaubt.
    - **Produktive Nutzung** (z. B. Klinikbetrieb, SaaS, kommerzielle Nutzung) erfordert eine **kommerzielle Lizenz von Synaptic Four**.
  - Nach Ablauf der Change‑Frist wird der Code für die jeweilige Version unter Apache‑2.0 freigegeben (BUSL‑Mechanismus).

- **Kernbotschaft:**
  - „Sie erhalten Einblick in die komplette Codebasis (Open Source *sichtbar*),
     aber das Produkt bleibt kommerziell lizenziert für produktiven Einsatz.“

- **Zielgruppen:**
  - Universitätskliniken, universitäre Forschungsgruppen, öffentliche Forschung.
  - Biotech/Pharma, CROs, Klinik-IT, Genomics‑Zentren.
  - Cloud‑/Hosting‑Partner (z. B. OTC, DFN‑Cloud) als Reseller.

---

### 2. Warum der **Code selbst** ein Verkaufsargument ist

1. **Transparenz & Vertrauen**
   - Vollständiger Python/FastAPI‑/React‑Code liegt offen.
   - Kund:innen und deren IT‑Security können:
     - Architektur, Datenflüsse und Sicherheitsmaßnahmen nachprüfen.
     - GA4GH‑Endpunkte (DRS, WES, Phenopackets) im Code nachvollziehen.
     - DSGVO‑relevante Stellen (Pseudonymisierung, Audit‑Log) einsehen.
   - Vorteil gegenüber „Black‑Box“-Produkten: geringere Hürde für Security‑Review, NIS2‑/ISO‑Audits, Krankenhaus‑IT‑Freigabe.

2. **Hohe Codequalität als Vertrauenssignal**
   - Klare Schichtentrennung: `api/` – `services/` – `models/` – `schemas/`.
   - Durchgängig Type Hints, Ruff‑Linting, strukturierte Tests.
   - Zahlreiche Doku‑Dateien (`USER-GUIDE`, `DEVELOPER-GUIDE`, `COMPLIANCE`, `SECURITY`, `AUDIT-REPORT`, `SBOM`).
   - Sales‑Argument: „Ihre Teams sehen, dass wir sauber entwickeln – das reduziert Integrationsrisiko.“

3. **Vendor Lock‑in reduzieren (aber nicht abschaffen)**
   - Offen einsehbarer Code senkt die wahrgenommene Abhängigkeit:
     - Kunden können bei Bedarf eigene Anpassungen oder Integrationen evaluieren.
     - Trotzdem: BUSL verhindert unkontrollierte Forks in der Produktion.
   - Botschaft: **„Hohe Transparenz ohne, dass Sie Ihre Geschäftsgrundlage verlieren.“**

4. **Kompatibel mit Forschung & Open Science**
   - Forschende können:
     - Pipelines, GA4GH‑Implementierungen und Embedding‑Code verstehen.
     - eigene Erweiterungen als Pull‑Requests beitragen.
     - die Software in nicht‑produktiver Umgebung (z. B. Sandbox) testen.
   - Sales‑Takeaway: „Die Forschungs‑Community kann mitgestalten, produktive Nutzung läuft über Lizenz.“

---

### 3. Value Proposition – technisch & fachlich

**Kernelemente (technischer Blick):**

- **On‑Premise KI‑Plattform**
  - Vollständiger Stack: PostgreSQL + pgvector, FastAPI‑Backend, React‑Frontend, Ollama, BLAST, Nextflow.
  - Ziel: KI, Pseudonymisierung, GA4GH‑Dienste und Literatur‑Workflows „unter einem Dach“.

- **GA4GH‑Alignment**
  - Implementierte Endpunkte für:
    - **DRS** (file-based Repositories mit Checksums, service‑info).
    - **WES** (Nextflow‑Workflows als WES‑Runs).
    - **Phenopackets v2** (Patientenphänotypen mit HPO, OMIM).
  - Vorteil: Anbindung an GA4GH‑Ökosystem, geringere Integrationsaufwände.

- **Pseudonymisierung & Audit**
  - Microsoft Presidio + AES‑basierte Verschlüsselung.
  - Vollständiges Audit‑Log von Pseudonymisierung und De‑Pseudonymisierung.
  - Isolation per User/Team und konfigurierbare De‑Pseudonymisierungs‑Rollen.

- **Research Notebook & Literatur‑Workflows**
  - Markdown‑ELN mit KI‑Assistent, Paper‑Verknüpfung, DRS‑Links.
  - PubMed‑Suche + semantische Suche in der eigenen Bibliothek.
  - FAIR‑Export mit Score, Metadaten, optionalem Zenodo‑Upload.

**Kernelemente (fachlicher Blick):**

- „Eine Plattform, die typische Forschungspfade abbildet“:
  - Literatur finden → speichern → semantisch durchsuchen → Notizbuch anlegen → Phenopackets/DRS verknüpfen → FAIR‑Export.
  - Weniger Tool‑Fragmentierung, weniger Copy‑Paste zwischen Systemen.

---

### 4. Wie man das Lizenzmodell erklärt (Forschung vs. kommerziell)

**Für Forschung, Lehre, interne Evaluation:**

- „Sie dürfen den BioResearch Assistant **kostenlos** in nicht‑produktiven Umgebungen nutzen: für Forschung, Lehre, interne Prototypen.“
- „Sie können Pull‑Requests schicken, Issues anlegen und die Entwicklung mitgestalten.“
- „Der Quellcode ist vollständig einsehbar (GitHub).“

**Für produktiven Einsatz / kommerzielle Nutzung:**

- „Sobald Sie die Software **für Patientenversorgung, produktive Studien, Services für Dritte oder als Teil eines kommerziellen Angebots** nutzen möchten, benötigen Sie eine kommerzielle Lizenz von Synaptic Four (BUSL‑Konzept).“
- „Damit erhalten Sie zusätzlich:**
  - Priorisierten Support / SLAs,
  - Migrations- und Integrationsunterstützung,
  - ggf. Anpassungen an kundenspezifische Compliance‑Anforderungen.“

**Typische Formulierungsbeispiele:**

- „Für Unis/Forschung: Sie können sofort loslegen, ohne Budgetfreigabe. Wenn Sie in die Klinik gehen wollen, sprechen wir über eine Lizenz.“
- „Für Unternehmen: Sie sehen den Code, können Ihre Security‑Teams prüfen lassen – und sichern sich über die Lizenz die Gewissheit, dass Betrieb & Support langfristig getragen werden.“

---

### 5. Welche Teile des Repos man Kunden aktiv zeigen kann

**Empfehlung für Demos/Workshops:**

- `README.md`
  - Einstieg, Features, Architekturskizze.

- `docs/USER-GUIDE.md`
  - Zeigt, dass die UI‑Flows durchdacht sind und dokumentiert wurden.

- `docs/DEVELOPER-GUIDE.md`
  - Für technische Ansprechpartner: konkrete Endpunkte, Curl‑Beispiele, GA4GH‑Abschnitte.

- `docs/COMPLIANCE-SUMMARY.md`
  - Für Datenschutz/Security‑Stakeholder als ersten Überblick.

- `docs/COMPLIANCE.md` + `docs/SECURITY.md` + `docs/GAIA-X-ALIGNMENT.md`
  - Für Audits, Datenschutz‑Beauftragte, Informationssicherheit.

- `docs/AUDIT-REPORT.md` und `docs/SBOM.md`
  - Für Security‑Teams (Code‑/Security‑Audit, Abhängigkeiten).

**Code-Beispiele zum Vorzeigen:**

- Pseudonymisierung (`backend/app/services/pseudonymization_service.py`) – zeigt, wie Mappings verschlüsselt werden.
- Health & GAIA‑X‑Endpoints – zeigen Feature‑Flags und Self‑Description.
- DRS/WES‑Endpoints – demonstrieren GA4GH‑Alignment.

---

### 6. Gesprächsleitfaden (Beispiele)

**Klinik‑IT / CISO:**

- Fokus auf:
  - On‑Premise‑Architektur, keine Cloud‑Pflicht.
  - Einsehbarer Code, SBOM, Audit‑Report.
  - Pseudonymisierung, Audit‑Logs, GA4GH‑Standards.
- Satzbeispiele:
  - „Sie können sich jede Zeile des Codes ansehen und prüfen, ob sie zu Ihrem Sicherheitsprofil passt.“
  - „Wir liefern Ihnen Doku und SBOM, damit Ihre Audits schneller durch sind.“

**PI / Forschungsgruppenleiter:**

- Fokus auf:
  - End‑to‑End Forschungsworkflow (Literatur → Notebook → Phenopackets → FAIR).
  - Kostenlose Nutzung in Forschung, spätere Lizenz für Klinik.
- Satzbeispiele:
  - „Für Ihre Studie können Sie heute starten – wenn die Klinik das Ergebnis in die Regelversorgung übernimmt, kommen wir ins Spiel mit der Lizenz.“

**Industrie / CRO:**

- Fokus auf:
  - GA4GH‑Anbindung, FAIR‑Export, Integrationen.
  - Möglichkeit, Teile zu erweitern (eigene Pipelines, DRS‑Backends).
- Satzbeispiele:
  - „Sie sparen sich Jahre Eigenentwicklung und erhalten trotzdem eine Plattform, die ihr Team versteht und erweitern kann.“

---

### 7. Grenzen & Ehrlichkeit (Wichtig im Verkauf)

- Nicht versprechen:
  - „DSGVO‑konform out of the box“ oder „GAIA‑X zertifiziert“.
  - „Ersetzt euer RIS/PACS/LIMS vollständig“.
- Stattdessen betonen:
  - „Wir liefern Bausteine und eine durchdachte Architektur; Sie behalten die Hoheit über Rechtskonformität und Integration.“
  - „Wir arbeiten offen mit Ihrem Datenschutz/Security zusammen.“

Damit bleibt der Sales‑Pitch ambitioniert, aber glaubwürdig und rechtlich sauber.
