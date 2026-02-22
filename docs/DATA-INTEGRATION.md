# Eigene Daten integrieren

## Schnellstart

### Wo finde ich was?

| Ich möchte... | Wo? |
|---|---|
| Paper aus PubMed speichern | Literature Mining → Suchen → Speichern |
| Gespeicherte Paper durchsuchen | Bibliothek → Semantische Suche |
| Eigene Paper manuell hinzufügen | API: POST /api/v1/library/papers |
| Genomische Datei registrieren | API: POST /ga4gh/drs/v1/objects |
| Datei über DRS abrufen | API: GET /ga4gh/drs/v1/objects/{id} |
| Phenopacket erstellen | Phenopackets Seite oder API |
| Pipeline starten | Pipelines Seite oder WES API |

### Wichtig: Demo vs. Vollinstallation

| Feature | Railway Demo | Lokale/Hetzner Installation |
|---|---|---|
| Papers speichern | ✅ | ✅ |
| Semantische Suche | ❌ (kein pgvector) | ✅ |
| DRS Dateien | ✅ Metadata | ✅ Metadata + Dateien |
| BLAST | ❌ | ✅ |
| Nextflow | ❌ | ✅ |

Für vollständige Funktionalität:
→ docs/deployment/LOCAL-SETUP.md
→ docs/deployment/DFN-CLOUD.md

---

## 1. Eigene Papers / Bibliothek

### Paper manuell hinzufügen (API)
curl -X POST https://DEINE-URL/api/v1/library/papers \
  -H "Content-Type: application/json" \
  -d '{
    "pmid": "custom-001",
    "title": "Mein Paper Titel",
    "abstract": "Abstract Text...",
    "authors": ["Mustermann M", "Schmidt A"],
    "year": 2024,
    "journal": "Nature Genetics",
    "doi": "10.1000/xyz"
  }'

### Papers aus BibTeX importieren
(Geplantes Feature — Roadmap)

### Papers aus PubMed speichern
1. Literature Mining → Suche starten
2. Paper auswählen → "Speichern" klicken
3. Paper erscheint in Bibliothek

### Semantische Suche aktivieren
Voraussetzung: Vollständige Installation mit pgvector
Nach dem Speichern werden Papers automatisch als
Embeddings gespeichert und sind semantisch durchsuchbar.

---

## 2. Genomische Dateien (GA4GH DRS)

### Datei registrieren (API)
curl -X POST https://DEINE-URL/ga4gh/drs/v1/objects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "patient001.vcf",
    "description": "Variant Call File Patient 001",
    "mime_type": "text/vcf",
    "size": 1048576
  }'

### Unterstützte Dateitypen
| Format | Beschreibung | Verwendung |
|---|---|---|
| VCF | Variant Call Format | Variant Calling Ergebnisse |
| FASTA | Sequenz Format | Referenzgenome, Queries |
| BAM | Aligned Reads | RNA-Seq, WGS Alignment |
| FASTQ | Raw Reads | Input für Pipelines |
| BED | Genomische Intervalle | Annotation |

### Lokale Dateien einbinden
In .env eintragen:
DRS_DATA_DIR=/pfad/zu/meinen/genomischen/daten/

Dateien in diesem Ordner werden automatisch
über die DRS API zugänglich.

### Mit Pipeline verbinden
1. Datei über DRS registrieren → DRS ID erhalten
2. Pipeline starten mit DRS ID als Input:
   POST /ga4gh/wes/v1/runs
   Body: { "workflow_params": { "input_vcf": "drs://DEINE-URL/DRS-ID" } }

---

## 3. Phenopackets — Patientendaten

### Phenopacket erstellen
curl -X POST https://DEINE-URL/api/v1/phenopackets \
  -H "Content-Type: application/json" \
  -d '{
    "pseudonym_id": "PATIENT-001",
    "phenotypes": ["HP:0001250", "HP:0002013"],
    "diseases": ["OMIM:143100"],
    "genes_of_interest": ["BRCA1", "TP53"]
  }'

### HPO Terme finden
Human Phenotype Ontology: https://hpo.jax.org
Suche nach Phänotyp → kopiere HP:XXXXXXX Nummer

### OMIM Nummern finden
Online Mendelian Inheritance in Man: https://omim.org
Suche nach Erkrankung → kopiere OMIM:XXXXXX Nummer

### Wichtig: DSGVO
Niemals echte Patientendaten direkt eingeben!
Immer erst pseudonymisieren:
1. Text → Pseudonymisierung → pseudonymized_text
2. Pseudonym ID aus mapping_id verwenden
3. Phenopacket mit Pseudonym ID erstellen

---

## 4. Bulk Import (für IT-Abteilungen)

### Papers aus CSV importieren
python backend/scripts/import_papers.py \
  --file papers.csv \
  --format pubmed-csv

### Genomische Dateien aus Verzeichnis importieren
python backend/scripts/import_drs.py \
  --directory /pfad/zu/vcf-files/ \
  --type vcf

### Datenbank-Backup
docker compose exec postgres pg_dump \
  -U bioresearch bioresearch > backup.sql

### Datenbank-Restore
docker compose exec -T postgres psql \
  -U bioresearch bioresearch < backup.sql
