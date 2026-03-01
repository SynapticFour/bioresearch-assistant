# Daten-Integration — BioResearch Assistant

## Wo finde ich was?

| Aufgabe | Wo in der UI | Endpunkt |
|--------|--------------|----------|
| Paper manuell eingeben | Bibliothek → "Paper hinzufügen" | POST /api/v1/library/papers |
| Paper via DOI/PMID | Bibliothek → "Paper hinzufügen" → "Automatisch ausfüllen" | POST /api/v1/library/extract-metadata |
| Papers bulk importieren | Bibliothek → "Bulk Import" | POST /api/v1/library/bulk-import |
| PubMed durchsuchen | Literatur Mining | POST /api/v1/literature/search |
| Genomische Datei registrieren | DRS → Drag & Drop | POST /ga4gh/drs/v1/objects |
| Phenopacket erstellen | Phenopackets → "Neues Phenopacket" | POST /api/v1/phenopackets |
| Text pseudonymisieren | Pseudonymisierung | POST /api/v1/pseudonymize |
| De-pseudonymisieren | Pseudonymisierung → Audit Log | POST /api/v1/pseudonymize/reverse |
| Pipeline starten | Pipelines | POST /ga4gh/wes/v1/runs |

## Paper-Import

### Manuell

Bibliothek → "Paper hinzufügen" → Felder ausfüllen. Abstract wird für semantische Suche verwendet.

### Via DOI oder PubMed ID (automatisch)

Bibliothek → "Paper hinzufügen" → DOI oder PubMed ID eingeben → "Automatisch ausfüllen". Metadaten werden automatisch via CrossRef oder PubMed API geholt.

### Bulk Import (ZIP/JSON/CSV)

Bibliothek → "Bulk Import". Unterstützte Formate:

- ZIP mit papers.json
- JSON Array
- CSV (pmid, title, abstract, authors, year, journal)

### Via API (für IT-Abteilungen)

```
POST /api/v1/library/papers
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "pmid": "12345678",
  "title": "...",
  "abstract": "...",
  "authors": ["Smith J"],
  "year": 2024,
  "journal": "Nature"
}
```

## Genomische Dateien (DRS)

### Drag & Drop Upload

DRS → Datei direkt in die Drop-Zone ziehen. Unterstützte Formate: VCF, FASTA, BAM, FASTQ, BED. Automatische Metadaten-Extraktion aus Dateiheader.

### Große Dateien (>500MB)

Datei auf Server kopieren, dann Server-Pfad angeben: DRS → "Datei registrieren" → Server-Pfad eingeben.

Empfehlung für IT:

```
scp /local/path/file.bam server:/data/drs/
```

Dann in UI: `/data/drs/file.bam`

### Via API

```
POST /ga4gh/drs/v1/objects
Content-Type: multipart/form-data
```

## Phenopackets

### Geführte Erstellung (3 Schritte)

1. Klinischen Text eingeben (pseudonymisiert!)
2. Extrahierte HPO-Terme und Gene prüfen
3. Pseudonym ID vergeben und speichern

### HPO Term Suche

Phenopackets → "Neues Phenopacket" → HPO Suche. Sucht in Human Phenotype Ontology.

## Pseudonymisierung

### Eingehende Texte pseudonymisieren

Pseudonymisierung → Text eingeben → Pseudonymisieren. Erkannte Entitäten: Namen, Daten, E-Mails, Telefonnummern, Patienten-IDs.

### De-Pseudonymisierung

Pseudonymisierung → Audit Log → "De-pseudonymisieren" Button. Zugriff konfigurierbar: `DEPSEUDO_ACCESS=owner` / `team` / `admin`. Jeder Zugriff wird im Audit Log protokolliert.

### DSGVO Hinweis

- Mit Ollama: Alle Daten bleiben auf dem Server ✅
- Mit Anthropic API: Texte werden übertragen ⚠️

## Sicherheits-Hinweise

### PubMed Suche

Suchanfragen werden an PubMed (extern) gesendet. Das System warnt automatisch, wenn in der Suchanfrage sensitive Daten erkannt werden.

### Datenisolation

- `ISOLATION_MODE=user` → Jeder Nutzer sieht nur seine Daten
- `ISOLATION_MODE=team` → Team teilt Daten
- `ISOLATION_MODE=open` → Alle sehen alles (nur Demo)
