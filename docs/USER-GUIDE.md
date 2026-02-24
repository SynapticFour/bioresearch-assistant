# BioResearch Assistant — Benutzerhandbuch

**Version:** 1.4.0  
**Erstellt von:** Synaptic Four

---

## Überblick

BioResearch Assistant ist ein KI-gestütztes Forschungswerkzeug für Biowissenschaftler und medizinische Forscher. Es kombiniert Literaturrecherche, Datenverwaltung und DSGVO-konforme Pseudonymisierung in einem System.

---

## 1. Literatursuche (Literature)

### Was macht diese Seite?

Durchsucht PubMed/NCBI nach wissenschaftlichen Publikationen und speichert relevante Papers in deiner persönlichen Bibliothek.

### Suchtypen

#### Ohne KI (Keyword-Suche)

- Sucht direkt in PubMed via NCBI API
- Findet exakte Begriffe und Synonyme
- Funktioniert immer, auch ohne Ollama

Beispiel-Suchanfragen:

- "BRCA1 breast cancer mutation"
- "COVID-19 long term effects"
- "CRISPR gene editing therapy 2023"

#### Mit KI (Semantische Suche) 🧠

- Nur in gespeicherten Papers (Bibliothek)
- Versteht Bedeutung, nicht nur Wörter
- Findet Papers auch wenn der genaue Begriff nicht im Text vorkommt
- Erfordert: pgvector + sentence-transformers

Beispiel:

- Suchanfrage: "zeige mir alles was mit Herzerkrankungen zu tun hat"
- Findet auch Papers über "cardiac", "myocardial", "coronary" etc.

**WICHTIG:** Semantische Suche sucht NUR in bereits gespeicherten Papers — nicht live in PubMed!

### KI Zusammenfassung

Nach einer PubMed-Suche kannst du einzelne Papers zusammenfassen lassen:

- Klicke auf ein Paper → "🤖 KI Zusammenfassung"
- Erfordert: Ollama mit geladenem Modell (llm_summaries: true im Health Check)
- Das Modell liest Abstract + Titel und erstellt eine strukturierte Zusammenfassung

### PII Warnung

Das System prüft Suchanfragen automatisch auf persönliche Daten (Namen, Geburtsdaten etc.) und warnt dich bevor die Anfrage an PubMed gesendet wird.

---

## 2. Bibliothek (Library)

### Was macht diese Seite?

Verwaltet alle gespeicherten Papers. Hier landen alle Papers die du aus PubMed gespeichert oder manuell eingegeben hast.

### Paper hinzufügen

#### Via PubMed Suche

1. Literature-Seite → Suche ausführen
2. Paper auswählen → "Speichern"
3. Paper erscheint automatisch in der Bibliothek

#### Manuell (ohne PubMed)

1. Bibliothek → "Paper hinzufügen"
2. PMID oder DOI eingeben → Auto-Fill
3. Oder alle Felder manuell ausfüllen

#### Bulk Import

Für viele Papers auf einmal:

1. Bibliothek → "Bulk Import"
2. Unterstützte Formate:
   - ZIP mit papers.json
   - JSON Array
   - CSV (Spalten: pmid, title, abstract, authors, year, journal)
3. Max: 1000 Papers, 50MB

### Suche in der Bibliothek

#### Keyword-Suche (lokal)

- Durchsucht Titel, Abstract, Autoren
- Zeigt "X von Y Papers gefunden"
- Funktioniert ohne Internet

#### Semantische Suche 🧠

- Versteht Bedeutung der Anfrage (KI-Embedding-Modell, multilingual)
- Erfordert: pgvector aktiviert

**Wie funktioniert semantische Suche?**

Die semantische Suche verwendet ein KI-Embedding-Modell (sentence-transformers), das Text in mathematische Vektoren umwandelt und Ähnlichkeiten berechnet.

**Was funktioniert gut:**

- Englische Keywords: "BRCA1 breast cancer"
- Kurze präzise Anfragen: "BRCA1"
- Verwandte Begriffe: "cardiac" findet auch "heart disease" Papers

**Was funktioniert weniger gut:**

- Lange deutsche Befehlssätze wie: "Zeige mir alle Papers die mit BRCA1 zu tun haben" → Besser: "BRCA1 Brustkrebs"
- Sehr allgemeine Anfragen

**Empfohlene Suchstrategie:**

1. Starte mit Schlüsselwörtern: "BRCA1"
2. Falls zu viele Ergebnisse → Slider nach rechts (präziser)
3. Falls zu wenige → Slider nach links (flexibler)
4. Mische Englisch und Deutsch: "BRCA1 Brustkrebs mutation"

**Similarity Score:**

- 🟢 80–100%: Sehr ähnlich
- 🟡 60–79%: Ähnlich
- 🟠 40–59%: Entfernt verwandt

### KI Zusammenfassung pro Paper

Jedes Paper in der Bibliothek hat einen "🤖 Zusammenfassen" Button (wenn Ollama läuft).

---

## 3. Pseudonymisierung (Pseudonymize)

### Was macht diese Seite?

Ersetzt persönliche Daten in Texten durch Platzhalter — DSGVO-konform und reversibel.

### Erkannte Entitäten

| Entität      | Beispiel           | Platzhalter        |
|-------------|--------------------|--------------------|
| Person      | "Max Mustermann"   | &lt;PERSON_1&gt;   |
| Datum       | "15.03.1970"      | &lt;DATE_TIME_1&gt; |
| Email       | "arzt@klinik.de"   | &lt;EMAIL_ADDRESS_1&gt; |
| Telefon     | "0711-123456"      | &lt;PHONE_NUMBER_1&gt; |
| Ort         | "Stuttgart"       | &lt;LOCATION_1&gt;  |
| IBAN        | "DE89 3704..."     | &lt;IBAN_CODE_1&gt; |
| Arzt-Nr     | "Ärztin 4711"     | &lt;MEDICAL_LICENSE_1&gt; |

### Beispiel

**Eingabe:**

"Patient Max Mustermann, geb. 15.03.1970, wurde am 22.01.2024 vorgestellt. Tel. 0711-123456. Ärztin 4711."

**Ausgabe:**

"Patient &lt;PERSON_1&gt;, geb. &lt;DATE_TIME_1&gt;, wurde am &lt;DATE_TIME_2&gt; vorgestellt. &lt;PHONE_NUMBER_1&gt;. &lt;MEDICAL_LICENSE_1&gt;."

### Eigene Patienten-ID Formate konfigurieren

Jede Institution hat eigene Patienten-ID Formate. Das System erkennt bereits gängige Formate (L-2024-98765, P-12345, Fallnummer: 123456), aber eigene Formate können in der .env konfiguriert werden.

**Schritt 1:** .env öffnen:
```bash
nano ~/bioresearch/.env
```

**Schritt 2:** Eigene Patterns hinzufügen:
```
CUSTOM_PATIENT_ID_PATTERNS=L-\d{4}-\d{5},P-\d{4,8}
```

**Schritt 3:** Backend neu starten:
```bash
cd ~/bioresearch
docker compose -f docker-compose.full.yml restart backend
```

**Gängige Regex-Formate:**
| Format | Regex | Beispiel |
|--------|-------|---------|
| Labor-ID | L-\d{4}-\d{5} | L-2024-98765 |
| Patient-ID | P-\d{4,8} | P-12345 |
| 8-stellig | \d{8} | 12345678 |
| Fallnummer | F-\d{6} | F-123456 |
| Beliebig | [A-Z]{2}\d{6} | AB123456 |

### De-Pseudonymisierung

Nur für berechtigte Nutzer (konfigurierbar):

- **owner:** nur du selbst
- **team:** dein Team
- **admin:** nur Administratoren

Alle De-Pseudonymisierungen werden im Audit Trail geloggt.

### DSGVO Hinweis

- Bei Ollama: alle Daten bleiben lokal ✅
- Bei Anthropic API: Texte gehen nach USA ⚠️

---

## 4. Phenopackets

### Was macht diese Seite?

Erstellt standardisierte Patientenbeschreibungen nach GA4GH Phenopackets v2 Standard.

### Wann verwenden?

- Für seltene Erkrankungen
- Für genetische Studien
- Für internationalen Datenaustausch

### Workflow (3 Schritte)

1. **Patient:** Pseudonym-ID, Geburtsjahr, Geschlecht (keine echten Namen!)
2. **Phänotypen:** HPO-Begriffe suchen und auswählen  
   Beispiel: "breast" → "Breast carcinoma (HP:0003002)"
3. **Erkrankung:** OMIM/ORPHA Diagnose verknüpfen

### HPO Suche

- Suche auf Englisch oder Deutsch
- Beispiele:
  - "cardiac" → Herzphänotypen
  - "breast" → Brustphänotypen
  - "BRCA" → BRCA-assoziierte Phänotypen

---

## 5. DRS — Datei-Verwaltung

### Was macht diese Seite?

Verwaltet biologische Datendateien nach GA4GH DRS v1.2 Standard.

### Unterstützte Formate

| Format      | Verwendung              |
|------------|-------------------------|
| .vcf       | Varianten (SNPs, Indels)|
| .fasta/.fa | Sequenzen               |
| .bam       | Alignments              |
| .fastq     | Rohe Sequenzierungsdaten|
| .bed       | Genomische Regionen     |
| .gz        | Komprimierte Dateien    |

### Datei hochladen

#### Drag & Drop (bis 500MB)

1. Datei in die Upload-Zone ziehen
2. Automatische Registrierung im DRS
3. DRS-ID wird generiert

#### Große Dateien (&gt;500MB)

Server-Pfad angeben: `/data/sequences/patient_001.bam`  
Die Datei muss bereits auf dem Server liegen.

---

## 6. BLAST Sequenzsuche

### Was macht diese Seite?

Führt BLAST-Alignments aus — vergleicht DNA/Protein-Sequenzen mit bekannten Datenbanken.

### Voraussetzung

BLAST muss installiert sein (blast: true im Health Check).

### Beispiel FASTA Eingabe

```
>query_sequence
ATGAAAGCTTGGGCTAGCTAGCTAG
```

- **DNA:** Nucleotide-Sequenz (z. B. blastn)
- **Protein:** Aminosäuren (z. B. blastp)

Nach dem Start erhältst du Treffer mit Score, E-Wert und Alignment. Die Ausführung läuft über GA4GH WES (Nextflow-Pipelines).

---

## 7. Pipelines / Workflows (WES)

### Was macht diese Seite?

Führt Bioinformatik-Pipelines über den GA4GH Workflow Execution Service (WES) v1.1 aus. Nextflow-Workflows können gestartet und der Status (running, complete, failed) eingesehen werden.

### Voraussetzung

Nextflow muss im Backend verfügbar sein (nextflow: true im Health Check).

---

## 10. Research Notebook (ELN)

### Was ist das?

Ein elektronisches Laborbuch direkt in der App. Dokumentiere Experimente, Hypothesen und Ergebnisse in Markdown — verknüpft mit deinen Papers, Phenopackets und Sequenzdaten.

### Workflow

1. Notizbuch → "Neues Notizbuch"
2. Titel und Inhalt in Markdown schreiben
3. Papers aus der Bibliothek verknüpfen (PMID eingeben)
4. DRS-Objekte und Phenopackets (Pseudonym-ID) verknüpfen
5. KI-Assistent für Zusammenfassung oder nächste Schritte nutzen
6. Auto-Save speichert alle 2 Sekunden nach der letzten Änderung

### KI-Assistent

- **Zusammenfassung:** Fasst den Notizinhalt in 2–4 Sätzen zusammen
- **Nächste Schritte:** Schlägt basierend auf dem Inhalt konkrete Forschungsschritte vor
- **Beides:** Beide Ausgaben in einem Aufruf

### Export

- Markdown-Export über den Download-Button im Editor
- Optional: PDF-Export (Backend benötigt reportlab)

---

## 11. FAIR Data Export

### Was ist FAIR?

FAIR steht für **Findable, Accessible, Interoperable, Reusable** — der internationale Standard für Forschungsdaten. DFG und de.NBI fordern FAIR-Konformität für geförderte Projekte.

### Export erstellen

1. FAIR Export → **Schritt 1:** Inhalte auswählen (Literatur, Phenopackets, Notizbücher, optional DRS)
2. **Schritt 2:** Metadaten eingeben (Titel, Autoren, Lizenz, Förderung, Keywords)
3. **Schritt 3:** FAIR-Score prüfen und Empfehlungen umsetzen
4. ZIP herunterladen oder zu Zenodo hochladen

### FAIR-Score

| Score   | Bedeutung |
|--------|-----------|
| 80–100 | Sehr gut — bereit für Publikation |
| 60–79  | Gut — kleine Verbesserungen empfohlen |
| &lt;60  | Metadaten unvollständig |

### Zenodo-Upload

Optional: Direkt zu Zenodo hochladen. Voraussetzung: `ZENODO_TOKEN` in der .env setzen. Zenodo vergibt nach Veröffentlichung automatisch einen DOI.

---

## Häufige Fragen

### Semantische Suche findet nichts, obwohl Papers vorhanden sind?

Papers, die vor der Embedding-Aktivierung gespeichert wurden, haben keine Embeddings. Lösung:

```bash
curl -X POST http://localhost:8000/api/v1/library/reembed-all \
  -H "Authorization: Bearer DEIN_TOKEN"
```

Oder über die API-Dokumentation:  
http://localhost:8000/docs → **POST** `/api/v1/library/reembed-all` ausführen (mit Anmeldung).

---

## Support & Kontakt

- **Dokumentation:** [docs/](.)
- **Installation:** [INSTALL.md](INSTALL.md)
- **Sicherheit:** [SECURITY.md](../SECURITY.md) (Sicherheitslücken melden)
- **Synaptic Four:** info@synapticfour.de

---

*Letzte Aktualisierung: 2026-02-24, Version 1.4.0*
