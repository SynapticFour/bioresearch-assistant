# BioResearch Assistant — Benutzerhandbuch

**Version 0.2.0 | Synaptic Four | August 2026**

> 💻 Für API-Zugriff und Konfiguration siehe [Developer Guide](DEVELOPER-GUIDE.md).

---

## Schnellstart (5 Minuten)

### Was ist das System?

BioResearch Assistant ist ein on-premise KI-System für Forschungsinstitute und Unikliniken. Es verbindet **Literature Mining** (PubMed), **persönliche Bibliothek** mit semantischer Suche, Pseudonymisierung, **Phenopackets**, **DRS-Dateiverwaltung**, **BLAST/WES-Pipelines**, **Research Notebook (ELN)** und **FAIR Data Export** in einer Anwendung. Die Software stellt technische Funktionen zur datenschutzfreundlichen Nutzung bereit; ob ein Einsatz rechtlich zulässig ist, hängt vom jeweiligen Szenario und den Verantwortlichen ab.

### Erste Schritte nach Installation

1. **Systemstatus prüfen:** Auf dem **Dashboard** siehst du ob alle Dienste laufen (Papers, Phenopackets, Workflows, Health).
2. **Im Dev-Modus** ist keine Anmeldung nötig; du kannst sofort loslegen.
3. **Literatursuche:** In der linken Navigation „Literatursuche“ wählen, Suchbegriff eingeben und Suchergebnisse in die Bibliothek übernehmen.
4. **Bibliothek:** Gespeicherte Papers durchsuchen (Stichwort oder semantische Suche), bei Bedarf KI-Zusammenfassung anfordern.

### Empfohlener Workflow für neue Nutzer

1. **Literature** → Suchbegriff eingeben (z. B. „BRCA1 breast cancer“) → Suchergebnisse ansehen → Paper „Speichern“.
2. **Bibliothek** → gespeicherte Papers einsehen → „Semantische Suche“ ausprobieren (z. B. „Herzerkrankungen“) → bei Bedarf „Zusammenfassen“.
3. **Notebook** → neues Notizbuch anlegen → Paper verknüpfen → KI-Assistent für Zusammenfassung/Nächste Schritte nutzen.
4. **FAIR Export** → für Publikation: Inhalte auswählen, Metadaten eingeben, FAIR-Score prüfen, ZIP oder Zenodo.

---

## Überblick: Alle Funktionen

| Seite / Bereich        | Funktion                                      | Wann verwenden                                      |
|------------------------|-----------------------------------------------|-----------------------------------------------------|
| Dashboard              | Übersicht Papers, Phenopackets, WES-Runs, Health | Einstieg, Systemstatus, schnelle Links              |
| Literatursuche         | PubMed-Suche, Paper speichern, PII-Prüfung    | Literaturrecherche, Paper in Bibliothek übernehmen  |
| Bibliothek             | Paper verwalten, Keyword/Semantik, KI-Summary | Suche in gespeicherten Papers, Zusammenfassungen   |
| Pseudonymisierung      | Text anonymisieren, Restore, Audit           | Klinische Texte für weitere Nutzung vorbereiten (unter Beachtung der DSGVO durch Verantwortliche) |
| Phenopackets           | HPO-Suche, Phenopacket erstellen/exportieren  | Seltene Erkrankungen, GA4GH-Austausch               |
| PhenoFlow             | HPO Query -> DRS Match -> WES Submit          | Search-to-Execution für Kohortenanalyse              |
| DRS                    | Dateien hochladen/registrieren, Download     | VCF, FASTA, BAM etc. verwalten                      |
| BLAST                  | Sequenzsuche (nt/nr)                          | DNA/Protein gegen Datenbanken                      |
| Pipelines / Workflows  | WES: Nextflow starten, Status, Logs           | BLAST oder Custom-Pipelines ausführen              |
| Research Notebook      | Markdown-ELN, Verknüpfungen, KI-Assistent    | Experimente dokumentieren, mit Papers/DRS verknüpfen |
| FAIR Export            | FAIR-Score, DataCite, Zenodo                  | Publikationsvorbereitung, DFG/de.NBI                |
| Audit & Compliance     | Audit-Log einsehen, CSV-Export                | Nachweis Pseudonymisierung, Betroffenenrechte      |

---

## 1. Dashboard

### Was zeigt es?

Das **Dashboard** gibt eine Übersicht: Anzahl gespeicherter Papers, Anzahl Phenopackets, letzte WES-Runs (Workflows), Systemstatus (Health) und Quick-Links zu Literatursuche, Bibliothek, Pseudonymisierung, Phenopackets, DRS, BLAST, Workflows, Notebook, FAIR Export und Audit.

### Welche Metriken?

- **Papers:** Gesamtanzahl gespeicherter Papers.
- **Phenopackets:** Anzahl gespeicherter Phenopackets.
- **WES-Runs:** Letzte Workflow-Läufe (Run-ID, Status, Dauer).
- **System Status:** Anzeige ob alle Systeme betriebsbereit sind (ok / eingeschränkt / Störung), inkl. Hinweise auf Embeddings, LLM, BLAST, Nextflow.

### Schritt-für-Schritt (UI)

1. Nach dem Login (oder im Dev-Modus direkt) erscheint das **Dashboard** als Startseite.
2. Oben siehst du die **Karten** für Papers, Phenopackets und WES-Runs — klicke auf eine Karte oder die Links darunter, um zur jeweiligen Seite zu wechseln.
3. Der **System-Status** (grün/gelb/rot) steht in einer eigenen Karte; bei Störung die Tooltips bzw. Hinweise lesen.
4. Über die **Navigation links** oder die Quick-Links kommst du zu Literatursuche, Bibliothek, Pseudonymisierung, Phenopackets, DRS, BLAST, Pipelines, Notebook, FAIR Export und Audit.

---

## 2. Literatursuche

### Was macht es?

Durchsucht **PubMed** per Stichwort und liefert Treffer (PMID, Titel, Abstract, Autoren, Jahr, Journal, DOI). Suchanfragen können auf **sensitive Daten (PII)** geprüft werden; Paper können in die **Bibliothek** gespeichert werden.

### Wann verwenden?

- Literaturrecherche zu einem Thema.
- Bevor du suchst: PII-Prüfung nutzen, wenn die Anfrage personenbezogene Daten enthalten könnte.

### Schritt-für-Schritt (UI)

1. In der **linken Navigation** auf **„Literatursuche“** klicken.
2. Optional: Auf **„Anfrage prüfen“** klicken (PII-Check) — bei Warnung Anfrage anpassen oder pseudonymisieren.
3. **Suchfeld** oben: Suchbegriff eingeben (z. B. „BRCA1 breast cancer mutation“), ggf. **Max. Ergebnisse** einstellen.
4. Auf den blauen Button **„Suchen“** (oben rechts neben dem Suchfeld) klicken → die Ergebnisliste erscheint unterhalb.
5. Bei einem Paper auf **„Speichern“** klicken → das Paper landet in der Bibliothek (inkl. Embedding für semantische Suche).
6. Optional: Bei einem Paper **„KI Zusammenfassung“** wählen (erfordert LLM: Ollama oder Anthropic); die Zusammenfassung erscheint nach einigen Sekunden.

---

## 3. Bibliothek

### Was macht es?

Verwaltet **gespeicherte Papers** (aus Literatursuche oder manuell/Bulk). Ermöglicht **Keyword-Filter** (Jahr, Journal), **semantische Suche** (nach Bedeutung), **KI-Zusammenfassung** pro Paper, **Bulk-Import** (CSV/JSON/ZIP) und **Re-Embedding** nach Modellwechsel.

### Wann verwenden?

- Alle gespeicherten Papers anzeigen und filtern.
- Semantische Suche („ähnliche“ Papers nach Bedeutung).
- KI-Zusammenfassung (DE/EN) für Abstracts.
- Viele Papers auf einmal importieren.

### Schritt-für-Schritt (UI)

1. In der Navigation **„Bibliothek“** öffnen.
2. **Paper hinzufügen:** Entweder aus Literatursuche „Speichern“ oder in der Bibliothek auf **„Paper hinzufügen“** klicken und PMID/DOI eingeben (Auto-Fill) oder Felder manuell ausfüllen.
3. **Filter:** Über die Filteroptionen nach Jahr oder Journal eingrenzen; die Liste zeigt „X von Y Papers“.
4. **Semantische Suche:** Suchfeld für semantische Suche nutzen, **Threshold-Slider** (0.3–1.8) anpassen → Treffer mit Ähnlichkeits-Score. Details siehe Abschnitt **„Wie funktioniert die Suche?“**.
5. **KI-Zusammenfassung:** Bei einem Paper auf **„Zusammenfassen“** klicken, Sprache DE/EN wählen; die Zusammenfassung erscheint im Paper-Bereich.
6. **Bulk Import:** Auf **„Bulk Import“** klicken, CSV/JSON oder ZIP auswählen (Format siehe unten), max. 50 MB, max. 1000 Einträge.
7. **Re-Embed:** Wenn semantische Suche leer bleibt obwohl Papers da sind: Re-Embed-Funktion nutzen (in der UI oder über Einstellungen), damit fehlende Embeddings nachgezogen werden.

### Bulk-Import: Formate

- **CSV:** Spalten z. B. `pmid`, `title`, `abstract`, `authors`, `year`, `journal`, `doi`. `authors` als kommagetrennte Liste oder ein Feld. Fehlende PMID werden automatisch ersetzt.
- **JSON:** Array von Objekten mit gleichen Feldern (pmid, title, abstract, authors, year, journal, doi).
- **ZIP:** Enthält JSON-Dateien; jede Datei ein Objekt oder Array von Paper-Objekten.

---

## 4. Pseudonymisierung

### Was macht es?

Ersetzt **personenbezogene und sensible Daten** in Texten durch Platzhalter (reversibel). Mappings werden verschlüsselt gespeichert; **Restore** (Original wiederherstellen) und **De-Pseudonymisierung** (reverse) mit Berechtigungen und Audit. Die Pseudonymisierung ist als technische Maßnahme zur Unterstützung von DSGVO‑Anforderungen gedacht, ersetzt aber keine rechtliche Bewertung des konkreten Einsatzes.

### Wann verwenden?

- Vor dem Versand von klinischen Texten an externe Dienste (z. B. KI).
- Wenn du Suchanfragen mit Personendaten prüfen willst (Literatursuche).
- Wenn du Texte wiederherstellen musst (nur mit Berechtigung, in Produktion mit API-Key).

### Erkannte Entitäten (vollständig)

| Entität         | Beispiel            | Platzhalter           |
|-----------------|---------------------|-----------------------|
| PERSON          | „Max Mustermann“   | &lt;PERSON_1&gt;       |
| DATE_TIME       | „15.03.1970“       | &lt;DATE_TIME_1&gt;    |
| EMAIL_ADDRESS   | „arzt@klinik.de“   | &lt;EMAIL_ADDRESS_1&gt; |
| PHONE_NUMBER    | „0711-123456“      | &lt;PHONE_NUMBER_1&gt;  |
| LOCATION        | „Stuttgart“        | &lt;LOCATION_1&gt;      |
| IBAN_CODE       | „DE89 3704…“       | &lt;IBAN_CODE_1&gt;     |
| MEDICAL_LICENSE  | „Ärztin 4711“     | &lt;MEDICAL_LICENSE_1&gt; |
| Patienten-IDs   | konfigurierbar (CUSTOM_PATIENT_ID_PATTERNS) | entsprechende Platzhalter |

### Eigene Patienten-ID-Formate

In der `.env` können Admins Regex-Patterns setzen (siehe [Developer Guide](DEVELOPER-GUIDE.md)). Nach Änderung Backend neu starten.

### De-Pseudonymisierung (reverse)

Nur für berechtigte Nutzer (konfigurierbar):

- **owner:** nur der User, der pseudonymisiert hat
- **team:** alle im gleichen Team
- **admin:** nur Admins

Alle Reverse-Vorgänge werden im Audit-Log erfasst.

### Schritt-für-Schritt (UI)

1. In der Navigation **„Pseudonymisierung“** öffnen.
2. **Text** in das große Eingabefeld einfügen, **Sprache** (de/en) wählen.
3. Auf **„Pseudonymisieren“** klicken → darunter erscheinen der Ausgabe-Text mit Platzhaltern und die **Mapping-ID** (für Restore/Reverse sichern).
4. **Audit Log:** Über **„Audit“** in der Navigation die Audit-Seite öffnen; Filter nach Datum/Sprache nutzen, bei Bedarf **„Export CSV“** klicken (Button oben rechts).
5. **Restore** und **Reverse** sind in der Produktion über die API mit entsprechenden Berechtigungen möglich (siehe Developer Guide).

---

## 5. Phenopackets

### Was macht es?

Erstellt und verwaltet **GA4GH Phenopackets v2** — standardisierte Beschreibungen von Patienten (nur **Pseudonym-IDs**, keine echten Personendaten). Enthält HPO-Phänotypen, Erkrankungen (OMIM/Orphanet), Gene, Metadaten. Export als JSON-LD, Validierung gegen Schema.

### Was sind Phenopackets?

Phenopackets sind ein Austauschformat für phänotypische und genetische Befunde (GA4GH). Sie ermöglichen einheitliche Beschreibungen von Fällen für Forschung und Diagnostik (z. B. seltene Erkrankungen).

### HPO-Suche

In der UI: Im Phenopacket-Formular **Phänotypen suchen** (Suchfeld für HPO), z. B. „cardiac“, „breast“, „seizure“ — Treffer auswählen und dem Phenopacket zuordnen.

### Schritt-für-Schritt (UI)

1. **„Phenopackets“** in der Navigation öffnen.
2. **„Neu“** oder **„Phenopacket erstellen“** klicken.
3. **Pseudonym-ID** vergeben, **Phänotypen** über HPO-Suche hinzufügen, optional **Erkrankungen** und **Gene** eintragen.
4. **„Erstellen“** bzw. **„Speichern“** klicken → das Phenopacket wird gespeichert.
5. In der Liste ein Phenopacket auswählen und **„Export“** wählen → JSON-LD wird heruntergeladen.
6. **Validierung** gegen das Phenopackets-v2-Schema ist über die API möglich (Developer Guide).

---

## 6. DRS — Dateiverwaltung

### Was macht es?

**GA4GH Data Repository Service (DRS) v1.3:** Biologische Dateien (VCF, FASTA, BAM, FASTQ, BED, .gz) registrieren, Metadaten abrufen, Download/Stream. Upload bis 500 MB; größere Dateien über Server-Pfad registrieren.

### Unterstützte Formate und Größenlimits

| Format        | Verwendung                    |
|---------------|-------------------------------|
| .vcf          | Varianten (SNPs, Indels)     |
| .fasta / .fa  | Sequenzen                     |
| .bam          | Alignments                    |
| .fastq        | Rohe Sequenzierungsdaten     |
| .bed          | Genomische Regionen           |
| .gz           | Komprimierte Dateien          |

- **Upload:** max. 500 MB pro Datei.
- **Größere Dateien:** Bereits auf dem Server liegende Dateien unter dem DRS-Speicherpfad per Pfadangabe registrieren (Admin/Einstellungen).

### VCF Metadaten-Extraktion

Beim Upload einer **VCF-Datei** extrahiert das System automatisch Metadaten aus dem **VCF-Header**:

- **Referenzgenom** (z. B. GRCh38)
- **Contigs** (Chromosomen/Contig-Zeilen)
- **Sample-Namen** (aus der #CHROM-Zeile)

Diese Metadaten können für die Katalogisierung und Dokumentation genutzt werden.

⚠️ **Was es NICHT macht:**
Das System verknüpft **VCF-Varianten NICHT automatisch mit PubMed-Artikeln**. Für Literatursuche zu Varianten oder Genen: Gen-Name bzw. Suchbegriffe **manuell** in die **Literatursuche** (Seite „Literatur“) eingeben.

### Schritt-für-Schritt (UI)

1. **DRS** über die Navigation oder einen Link (z. B. vom Dashboard) öffnen.
2. **Upload:** Datei per **Drag & Drop** in die Upload-Zone ziehen oder per Klick **„Datei auswählen“** (bis 500 MB).
3. **Große Dateien:** Wenn die Datei bereits auf dem Server liegt, kann ein Admin sie über Pfad registrieren (siehe Developer Guide).
4. **Objekte auflisten:** Die Seite zeigt die registrierten DRS-Objekte; über Objekt-ID oder Aktionen **Download** starten (Stream).
5. **Download:** Auf das gewünschte Objekt klicken und die Download- bzw. Stream-Option nutzen.

---

## 6.5 PhenoFlow (Search-to-Execution)

### Was macht es?

**PhenoFlow v0.1** verbindet drei bestehende Bereiche:

1. Phenopackets (HPO-basierte Fallbeschreibung)
2. DRS (Datei-Objekte wie BAM/VCF)
3. WES (Workflow-Ausführung)

Damit kannst du eine phänotypische Anfrage direkt in eine Workflow-Ausführung übersetzen.

### Typischer Anwendungsfall

"Finde alle Fälle mit `HP:0001250`, die ein verknüpftes BAM-Asset haben, und starte den Workflow."

### Voraussetzungen

- Phenopacket existiert (z. B. `DEMO-P001`)
- Mindestens ein DRS-Asset ist mit dem Phenopacket verknüpft
- WES/Workflow-Backend ist erreichbar (Health/Workflows prüfen)

### Schritt-für-Schritt (UI)

1. **Phenopackets** öffnen und einen Fall auswählen.
2. Im Detaildialog unter **Linked DRS Assets** prüfen, ob Assets verknüpft sind.
3. Falls nötig: im Detaildialog `drs_object_id` + `file_type` eintragen und **Asset verknüpfen**.
4. In der Navigation **PhenoFlow** öffnen.
5. HPO-Terme eingeben (z. B. `HP:0001250`), optional `file_type` setzen.
6. Workflow-Descriptor + `workflow_params_template` prüfen.
7. **PhenoFlow Run starten**.
8. Unter **Matches/History** die erzeugten WES Run IDs und Zustände kontrollieren.

### Hinweise für kliniknahe Forschung

- Es werden nur Identifier/Provenance gespeichert (`pseudonym_id`, `drs_object_id`, `wes_run_id`).
- Keine dekodierten Genomdaten werden persistent in PhenoFlow gespeichert.
- Für produktive Nutzung weiterhin klinische Governance und lokale SOPs beachten.

---

## 7. BLAST Sequenzsuche

### Was macht es?

Startet eine **BLAST-Suche** (DNA/Protein gegen Datenbanken wie nt/nr) über WES (Nextflow). Du erhältst eine Run-ID; die **Ergebnisse** (Treffer, Score, E-Wert, Alignment) werden auf der Seite angezeigt; optional werden passende Papers aus der Bibliothek vorgeschlagen.

### Voraussetzungen

- BLAST-Datenbank eingerichtet (z. B. nt oder andere unter dem konfigurierten DB-Pfad).
- Im Dashboard bzw. Health sollte **BLAST** und ggf. **Nextflow** als verfügbar angezeigt werden. Setup z. B. mit `./setup-blast-db.sh`.

### FASTA-Format

Eingabe als FASTA oder reine Sequenz, z. B.:

```
>query_sequence
ATGAAAGCTTGGGCTAGCTAGCTAG
```

- **DNA:** Nucleotid-Zeichen (IUPAC).
- **Protein:** Aminosäuren (IUPAC).
Das System erkennt den Typ in der Regel automatisch.

### Datenbank auswählen

In der BLAST-UI die **Datenbank** wählen (z. B. nt, nr oder eine andere eingerichtete DB). Ist keine Datenbank verfügbar, zeigt die Seite einen Hinweis (z. B. „Datenbank nicht verfügbar“).

### Schritt-für-Schritt (UI)

1. **BLAST** in der Navigation öffnen (oder über „Pipelines“/„Workflows“).
2. **DB-Status** prüfen: Grüner Hinweis = Datenbank verfügbar; sonst zuerst Setup durchführen.
3. **Sequenz** (FASTA oder Rohsequenz) in das Eingabefeld einfügen, **Datenbank** auswählen.
4. Auf **„BLAST starten“** klicken → eine Run-ID erscheint, die Ergebnisse werden automatisch geladen (Polling).
5. **Ergebnisse** anzeigen: Treffer mit Score, E-Wert, Alignment; optional **„Related papers“** aktivieren, um passende Literatur aus der Bibliothek anzuzeigen.

---

## 8. Pipelines & Workflows (WES)

### Was macht es?

**GA4GH Workflow Execution Service (WES) v1.1:** Nextflow- (und ggf. andere) Workflows starten, **Status** abfragen, **Logs** lesen, Runs **abbrechen**. BLAST läuft darüber; zusätzlich können Custom-Nextflow-Pipelines (z. B. main.nf, nf-core) gestartet werden.

### Wann verwenden?

- BLAST über die WES-Integration (siehe BLAST).
- Eigene Nextflow-Pipelines (Workflow-URL z. B. main.nf, blast oder URL zu einer .nf-Datei).

### Schritt-für-Schritt (UI: Workflows/Pipelines)

1. **„Pipelines“** oder **„Workflows“** in der Navigation öffnen (beide führen zur gleichen Seite).
2. **Workflow-Typ** wählen (z. B. BLAST, STAR, GATK, Custom).
3. Bei **BLAST:** Sequenz und DB wie unter BLAST eingeben. Bei **Custom:** URL und ggf. Parameter eintragen.
4. Auf **„Start“** bzw. **„Workflow starten“** klicken → Run wird erstellt, die **Run-ID** erscheint in der Liste.
5. In der **Run-Liste** Status einsehen (QUEUED, RUNNING, COMPLETE, FAILED …), **Dauer** und **Logs** über Detail-Ansicht öffnen (z. B. auf einen Run klicken).
6. Bei laufendem Run **„Abbrechen“** klicken, um den Run zu stoppen.

---

## 9. Research Notebook (ELN)

### Was macht es?

**Elektronisches Laborbuch** in Markdown: Notizen, Verknüpfungen zu Papers (PMID), DRS-Objekten und Phenopackets (Pseudonym-ID). **KI-Assistent** erzeugt Zusammenfassung und/oder „Nächste Schritte“. Auto-Save (nach kurzer Pause), Export als Markdown oder PDF (wenn reportlab installiert).

### Markdown-Syntax (kurz)

- Überschriften: `#`, `##`, `###`
- Fett: `**text**`, Kursiv: `*text*`
- Listen: `-` oder `1.`
- Links: `[text](url)`
Verknüpfungen zu Papers/DRS/Phenopackets werden in der App über die **„Link“**-Funktion gespeichert, nicht als reine Markdown-Links.

### KI-Assistent

Der KI-Assistent kann **zwei Dinge** tun:

**Zusammenfassung (summary):**
Fasst den **Inhalt deines Notizbuchs** in 2–3 Sätzen zusammen. Nützlich, wenn du nach einer Pause wieder einsteigen willst oder einen Kollegen einbriefen möchtest.

**Schritte:**
1. Notizbuch öffnen
2. Auf **„KI Assistent“** klicken (Button in der Toolbar oder neben dem Editor)
3. Modus **„Zusammenfassung“** wählen
4. Warten (~10–30 s je nach LLM-Modell)
5. Die Zusammenfassung erscheint unter dem Editor (und wird im Notizbuch gespeichert)

**Nächste Schritte (next_steps):**
Das LLM liest deinen **Notizinhalt** und schlägt basierend darauf **nächste Forschungsschritte** vor — z. B. welche Experimente sinnvoll wären oder welche Fragen noch offen sind.

Wenn **Papers verknüpft** sind, liest der KI-Assistent deren **Abstracts automatisch** als zusätzlichen Kontext.

⚠️ **Wichtig:** Ohne verknüpfte Papers liest der KI-Assistent nur den Text deines Notizbuchs. Für bessere Ergebnisse: Papers verknüpfen oder relevante Inhalte **direkt in die Notiz** kopieren.

### Schritt-für-Schritt (UI)

1. **„Notebook“** in der Navigation öffnen → **„Neues Notizbuch“** klicken.
2. **Titel** und **Inhalt** in Markdown eingeben; Auto-Save speichert nach kurzer Pause.
3. **Verknüpfen:** Über **„Link hinzufügen“** (oder ähnlich) Paper (PMID), DRS (Objekt-ID) oder Phenopacket (Pseudonym-ID) verknüpfen.
4. **KI-Assistent:** Auf **„KI Assistent“** klicken, Modus **„Zusammenfassung“**, **„Nächste Schritte“** oder **„Beides“** wählen und warten; Ergebnis erscheint unter dem Editor.
5. **Export:** **„Export“** bzw. **„Download“** wählen → Markdown oder PDF herunterladen.

---

## 10. FAIR Data Export

### Was macht es?

Erstellt **FAIR-konforme Export-Pakete** (ZIP) mit ausgewählten Papers, Phenopackets, Notizbüchern und optional DRS-Dateien. **FAIR-Score** (Findable, Accessible, Interoperable, Reusable), **DataCite/Dublin-Core-Metadaten**, optional **Zenodo-Upload** (DOI nach Veröffentlichung).

### FAIR-Score verstehen

- **80–100:** Sehr gut, publikationsreif.
- **60–79:** Gut, kleine Verbesserungen empfohlen.
- **&lt;60:** Metadaten unvollständig.

### Data Management Plan (DMP)

Der FAIR Export generiert automatisch einen **DMP als Markdown-Datei**, basierend auf den **Metadaten**, die du im Wizard eingegeben hast:

**Was im DMP steht:**
- Projekttitel und Beschreibung
- Autoren
- Lizenz (z. B. CC-BY-4.0)
- Förderung (z. B. DFG Projekt-Nr.)
- Kurze FAIR-Prinzipien-Erklärung

**Was der DMP NICHT enthält:**
- Keine KI-generierten Texte
- Keine automatische Analyse der Daten
- Kein vollständiger DFG-DMP

💡 **Tipp:** Den generierten DMP als **Startpunkt** verwenden und **manuell ergänzen** für offizielle Einreichungen (DFG, Horizon Europe etc.).

### Wizard Schritt für Schritt (UI)

1. **„FAIR Export“** in der Navigation öffnen.
2. **Schritt 1:** Inhalte wählen (Papers, Phenopackets, Notebooks, optional DRS) — entsprechende Checkboxen setzen.
3. **Schritt 2:** Metadaten eingeben: Titel, Beschreibung, Autoren, Lizenz (z. B. CC-BY-4.0), Keywords, Förderung (z. B. DFG).
4. **Schritt 3:** FAIR-Compliance prüfen, Empfehlungen umsetzen (Score und Hinweise anzeigen).
5. **„ZIP herunterladen“** klicken oder **„Zu Zenodo hochladen“** (wenn Zenodo konfiguriert ist).

### Zenodo konfigurieren

Zenodo-Upload muss vom Administrator in der Umgebung konfiguriert werden (z. B. Token in .env). Optional kann beim Upload ein Token angegeben werden (siehe Developer Guide).

---

## 11. Audit & Compliance

### Was wird geloggt?

- **Pseudonymisierung:** Operation, User, Zeitstempel, Anzahl ersetzter Entitäten, Hash des Eingabetexts (kein Klartext), Operationstyp (pseudonymize/restore/De-Pseudonymisierung), Sprache, Mapping-ID.
- **FAIR Export:** Aktionen werden serverseitig geloggt (z. B. User, Titel).

### Audit-Log lesen und exportieren

- **UI (Audit-Seite):** In der Navigation **„Audit“** öffnen. Filter nach **Datum (von/bis)** und **Sprache** einstellen. Die Tabelle zeigt Zeitstempel, Operation, Entities, Sprache, Mapping-ID. Oben rechts **„Export CSV“** klicken → UTF-8-CSV mit BOM wird heruntergeladen.
- Für API-Zugriff (z. B. limit/offset) siehe [Developer Guide](DEVELOPER-GUIDE.md).

### DSGVO Betroffenenrechte

- **Auskunft/Nachweis:** Audit-Log exportieren (CSV) — zeigt Verarbeitungen ohne Klartext-Inhalte (nur Hash).
- **Löschung:** Paper aus Bibliothek löschen (in der Bibliothek beim Paper „Löschen“); Pseudonym-Mappings müssen ggf. separat verwaltet/gelöscht werden.
- Weitere Hinweise: [docs/COMPLIANCE.md](COMPLIANCE.md).

---

## Wie funktioniert die Suche?

BioResearch Assistant hat zwei verschiedene Suchmechanismen — es ist wichtig, den Unterschied zu verstehen:

### PubMed: Keyword-Suche

Die PubMed-Suche funktioniert wie eine klassische Datenbanksuche:

- Deine Suchbegriffe werden direkt an PubMed gesendet
- PubMed sucht nach exakten Wortübereinstimmungen (inkl. MeSH-Begriffe)
- "BRCA1 Therapie" findet Papers die genau diese Wörter enthalten

**Vorteil:** Präzise, nachvollziehbar, vollständig
**Nachteil:** Synonyme und verwandte Konzepte werden nur gefunden wenn PubMed sie intern mappt

---

### Bibliothek: Vektorbasierte Ähnlichkeitssuche

Die Suche in deiner gespeicherten Bibliothek funktioniert grundlegend anders — und ist wichtig richtig zu verstehen um keine falschen Erwartungen zu haben.

**Was passiert technisch:**

1. Dein Suchbegriff wird durch ein KI-Modell (paraphrase-multilingual-mpnet) in einen mathematischen Vektor umgewandelt — eine Liste von 768 Zahlen die die "Position" deines Begriffs in einem hochdimensionalen Bedeutungsraum darstellen
2. Alle gespeicherten Papers wurden beim Speichern ebenfalls in solche Vektoren umgewandelt
3. Das System berechnet die mathematische Ähnlichkeit (Cosine-Distanz) zwischen deinem Suchvektor und allen Paper-Vektoren
4. Die ähnlichsten Papers werden zurückgegeben

**Was das in der Praxis bedeutet:**

✅ **Was gut funktioniert:**

- Synonyme: "Herzinfarkt" findet auch Papers über "Myokardinfarkt" — weil das Modell weiß dass diese Konzepte verwandt sind
- Sprachübergreifend: Deutsche Suche kann englische Papers finden
- Konzeptuelle Nähe: "Krebs Immuntherapie" findet auch Papers über "Checkpoint-Inhibitoren" ohne dass du den Begriff kennst

⚠️ **Was NICHT funktioniert:**

- Logische Fragen: "Papers die Therapie A BESSER als Therapie B bewerten" — das Modell versteht keine logischen Relationen
- Zeitliche Filter via Suche: "neueste Papers" hat keine Bedeutung im Vektorraum (Datumsfilter separat verwenden!)
- Sehr spezifische Zahlen: "p < 0.05" oder "n = 200" sind im Vektorraum bedeutungslos
- Negationen: "Papers OHNE Nebenwirkungen" funktioniert nicht zuverlässig

**Was es NICHT ist:**

Die Ähnlichkeitssuche ist KEIN Chatbot und KEIN KI-Assistent der deine Frage "versteht" wie Claude oder ChatGPT es tun würden. Sie beantwortet keine Fragen — sie findet ähnliche Dokumente.

- **Falsche Erwartung:** ❌ "Welche meiner gespeicherten Papers empfehlen Metformin für ältere Patienten?" → Das System kann diese Frage nicht beantworten.
- **Richtige Verwendung:** ✅ "Metformin ältere Patienten Diabetes" → Das System findet Papers deren Inhalt diesem Themenbereich ähnelt.

---

### Der Ähnlichkeits-Score

Jedes Ergebnis zeigt einen Prozentsatz:

| Score | Bedeutung | Interpretation |
|-------|-----------|----------------|
| 🟢 80-100% | Sehr ähnlich | Thematisch sehr nah |
| 🟡 60-79% | Ähnlich | Verwandtes Thema |
| 🟠 40-59% | Entfernt verwandt | Überschneidungen |

Wichtig: 100% bedeutet nicht "perfekte Antwort" — es bedeutet "mathematisch am ähnlichsten in deiner Bibliothek". Ein Score von 65% kann trotzdem das relevanteste Paper sein.

---

### Threshold-Slider: Was er wirklich macht

Der Slider (0.3 → 1.8) kontrolliert nicht "wie gut" die Ergebnisse sind, sondern "wie streng" der Ähnlichkeitsfilter ist:

- **Niedriger Wert (0.3-0.5):** Nur sehr ähnliche Papers — wenige aber thematisch eng verwandte Ergebnisse
- **Mittlerer Wert (0.8-1.2):** Ausgewogener Mix — empfohlen als Startpunkt
- **Hoher Wert (1.5-1.8):** Viele Ergebnisse — auch entfernt verwandte Papers werden angezeigt

Empfehlung: Mit 1.0 starten, dann anpassen.

---

### 🧠 Frag deine Bibliothek (RAG)

**Hinweis „Locus“:** Synaptic Four fasst den **On-Premise-RAG-Stack** für den **klinisch-bioinformatischen** Kontext (inkl. optionaler **kuratierter Indizes**, z. B. Leitlinien, MII-KDS, GA4GH-Dokumentation) unter dem **Modulnamen Locus** in der Produkt- und Websitedokumentation zusammen — funktional gehört das zur gleichen Plattform **BioResearch Assistant**. Details: [LOCUS-MODULE.md](LOCUS-MODULE.md).

**Locus im Backend (API):** Mit `LOCUS_ENABLED=1` (nach `alembic` und Index-Daten) nutzt `POST /api/v1/locus/rag` die Tabelle `locus_chunks` — geteilte, kuratierte Korpusschnitte, **nicht** deine persönliche Paper-Bibliothek (`/library/rag` bleibt dafür). `GET /api/v1/locus/status` zeigt, ob Locus an ist und ob Chunks existieren. Demo-Seed: `python scripts/seed_locus_demo.py` im Backend.

**So verwendest du RAG:**

1. Bibliothek öffnen
2. Tab „Frag deine Bibliothek“ wählen
3. Natürlichsprachige Frage eingeben, z. B.:
   - „Welche Nebenwirkungen von Metformin werden erwähnt?“
   - „Gibt es Papers über CRISPR bei Sichelzellanämie?“
   - „Was sagen meine Papers über Immuntherapie bei Lungenkrebs?“
4. Anzahl Papers als Kontext wählen (1–20)
5. Sprache wählen (DE/EN)
6. „Fragen“ klicken (~10–60 s je nach LLM)

**Was du bekommst:**

- Prosa-Antwort vom LLM
- Liste der verwendeten Papers mit Ähnlichkeits-Score
- Disclaimer mit Anzahl verwendeter Papers

⚠️ **Wichtige Einschränkungen:**

- Antwort basiert NUR auf deinen gespeicherten Papers
- Mindestens 1 Paper mit Embedding muss vorhanden sein
- Bei leerer Bibliothek: Fehlermeldung
- Kein Ersatz für vollständige Literaturrecherche

**Wann verwenden vs. Semantische Suche:**

| Ziel                         | Tool                |
|-----------------------------|---------------------|
| Papers zu Thema finden      | Semantische Suche   |
| Frage zu Thema beantworten  | RAG                 |
| Sehr spezifische Papers     | Keyword-Suche       |

---

## Empfohlene Workflows

### Workflow A: Neue Forschungsfrage

1. **Literature** → Suchbegriff (z. B. Thema + Jahr) → relevante Papers speichern.
2. **Bibliothek** → Semantische Suche zur Verfeinerung, KI-Zusammenfassungen lesen.
3. **Notebook** → Neues Notizbuch, Hypothesen/Design in Markdown, Papers verknüpfen, KI „Nächste Schritte“.
4. **FAIR Export** → Für Publikation: Inhalte + Metadaten, FAIR-Score, ZIP oder Zenodo.

### Workflow B: Klinischer Fall

1. **Pseudonymisierung** → Klinischen Text pseudonymisieren, mapping_id sichern.
2. **Phenopackets** → Phenopacket mit Pseudonym-ID anlegen, HPO/OMIM/Genes eintragen.
3. **Literatursuche** → Mit Phänotypen/Diagnosen als Suchbegriffe (ohne PII) suchen, Paper speichern.
4. **DRS** → Befunddateien (z. B. VCF) hochladen, in Notizen oder Phenopacket referenzieren.

### Workflow C: Genomische Analyse

1. **DRS** → FASTA/VCF hochladen oder registrieren.
2. **BLAST** → Sequenz eingeben, DB wählen, Run starten, Ergebnisse inkl. Papers auswerten.
3. **WES** → Bei Custom-Pipeline: Workflow starten, Status/Logs prüfen.
4. **Notebook** → Experiment dokumentieren, DRS-Objekte und Runs verknüpfen.

### Workflow D: Publikationsvorbereitung

1. **Bibliothek + Notebooks + Phenopackets** → Alle gewünschten Inhalte sammeln und verknüpfen.
2. **FAIR Export** → Wizard: Inhalte wählen, DataCite-Felder ausfüllen, FAIR-Check.
3. **Zenodo** → Optional Upload, DOI nach Veröffentlichung im Zenodo-Dashboard.

---

## Roadmap

| Feature | Version | Status |
|---------|---------|--------|
| RAG — Frag deine Bibliothek | v0.1.0 | ✅ Enthalten |
| Locus (RAG + Domänen-Indizes, siehe [LOCUS-MODULE.md](LOCUS-MODULE.md)) | laufend | ✅ / optional Abo |
| Hybrid Search (Vektor + Keyword) | v1.1.0 | Geplant |
| Team Collaboration im ELN | v1.1.0 | Geplant |
| VCF → Literatursuche Button | v1.1.0 | Geplant |
| Crypt4GH, ISO 27001 | v2.0.0 | Geplant |

---

## Häufige Fragen

### Semantische Suche findet nichts, obwohl Papers in der Bibliothek sind?

Papers, die vor Aktivierung der Embeddings gespeichert wurden, haben keinen Vektor. **Lösung:** In der Bibliothek die **Re-Embed**-Funktion nutzen (falls angeboten) oder einen Administrator bitten, die fehlenden Embeddings nachziehen zu lassen. Technische Details: [Developer Guide](DEVELOPER-GUIDE.md).

### BLAST „Datenbank nicht verfügbar“?

BLAST-Datenbank muss eingerichtet sein (z. B. mit `./setup-blast-db.sh`). Die BLAST-Seite zeigt den Status; bei „nicht verfügbar“ zuerst das Setup durchführen.

### Zenodo-Upload schlägt fehl?

Zenodo muss vom Administrator konfiguriert werden (Token in der Umgebung). Netzwerk/Firewall prüfen (zenodo.org erreichbar). Siehe auch [Developer Guide](DEVELOPER-GUIDE.md).

### PDF-Export beim Notebook nicht verfügbar?

Das Backend benötigt die Bibliothek `reportlab`. Alternativ: Export als **Markdown** wählen und lokal zu PDF konvertieren (z. B. mit Pandoc oder einem Editor).

### Im Dev-Modus brauche ich keinen Token?

Ja. Wenn keine OIDC-Anmeldung konfiguriert ist, kannst du die Anwendung ohne Login nutzen.

---

**Support & weitere Dokumentation**

- [INSTALL.md](INSTALL.md) — Installation
- [docs/COMPLIANCE.md](COMPLIANCE.md) — Compliance (DSGVO, NIS2, FAIR, …)
- [SECURITY.md](../SECURITY.md) — Sicherheit, Meldung von Lücken
- **Synaptic Four:** contact@synapticfour.com · https://www.synapticfour.com

*Letzte Aktualisierung: August 2026, Version 0.2.0*
