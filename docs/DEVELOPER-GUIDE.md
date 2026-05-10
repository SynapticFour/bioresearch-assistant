# BioResearch Assistant — Developer Guide

**Version 1.0.0 | Synaptic Four**

---

## Überblick

Die API des BioResearch Assistant ist **REST-basiert** (FastAPI). Die meisten Endpunkte liegen unter dem Präfix **`/api/v1`**. GA4GH-konforme Dienste (DRS, WES) sind unter **`/ga4gh/drs/v1`** bzw. **`/ga4gh/wes/v1`** erreichbar.

- **UI-Dokumentation (Endnutzer):** [USER-GUIDE.md](USER-GUIDE.md)
- **Interaktive API-Dokumentation:**
  - **Swagger UI:** http://localhost:8000/docs
  - **ReDoc:** http://localhost:8000/redoc

Basis-URL für Beispiele (lokal): `http://localhost:8000`. In Produktion die jeweilige Host-URL verwenden.

---

## Authentifizierung

- **Dev-Modus:** Wenn OIDC nicht konfiguriert ist (`auth_enabled: false`), ist **kein Token** nötig. Alle Aufrufe können ohne `Authorization`-Header erfolgen.
- **Produktion (OIDC):** Login über Keycloak, ELIXIR AAI, Google, Microsoft etc. Nach dem Login erhältst du einen **Bearer Token**, der bei geschützten Endpunkten mitgeschickt werden muss.

**curl Basis-Template (mit Auth):**

```bash
curl -s "http://localhost:8000/api/v1/literature/stats" \
  -H "Authorization: Bearer <token>"
```

Ohne Auth (Dev):

```bash
curl -s "http://localhost:8000/api/v1/literature/stats"
```

---

## Alle Endpoints mit curl-Beispielen

### Literature (API-Prefix: /api/v1)

#### POST /api/v1/literature/search/validate-query

Prüft eine Suchanfrage auf sensitive Daten (PII).

```bash
curl -s -X POST "http://localhost:8000/api/v1/literature/search/validate-query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Patient Müller aus Stuttgart", "language": "de"}'
```

Response:

```json
{
  "safe": false,
  "warning": "Die Suchanfrage enthält möglicherweise sensitive Daten.",
  "detected_types": ["PERSON", "LOCATION"],
  "recommendation": "Bitte pseudonymisieren Sie die Anfrage..."
}
```

Bei unkritischer Anfrage: `{"safe": true, "detected_types": []}`.

---

#### POST /api/v1/literature/search

PubMed-Suche.

```bash
curl -s -X POST "http://localhost:8000/api/v1/literature/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "BRCA1 breast cancer", "max_results": 5, "language": "de"}'
```

Response: Array von Paper-Objekten (pmid, title, abstract, authors, year, journal, doi, summary).

---

#### GET /api/v1/literature/stats

Statistik und zuletzt gespeicherte Papers (Dashboard).

```bash
curl -s "http://localhost:8000/api/v1/literature/stats"
```

Response:

```json
{
  "total_papers": 42,
  "recent_papers": [{ "pmid": "12345678", "title": "...", "abstract": "...", "authors": [], "year": 2023, "journal": null, "doi": null, "summary": null }]
}
```

---

#### POST /api/v1/literature/papers

Paper in Bibliothek speichern. Body: PubMedArticle (pmid, title, abstract, authors, year, journal, doi, optional keywords/summary).

```bash
curl -s -X POST "http://localhost:8000/api/v1/literature/papers" \
  -H "Content-Type: application/json" \
  -d '{"pmid": "12345678", "title": "A study on BRCA1", "abstract": "We investigated...", "authors": ["Smith J"], "year": 2023, "journal": "Nature", "doi": null}'
```

Response: Ein Paper-Objekt (PubMedSearchResponse).

---

#### GET /api/v1/literature/papers/{pmid}

Einzelnes Paper von PubMed abrufen (ohne Speicherung).

```bash
curl -s "http://localhost:8000/api/v1/literature/papers/12345678"
```

Response: Paper-Objekt (pmid, title, abstract, authors, year, journal, doi, summary).

---

### Library (API-Prefix: /api/v1)

#### POST /api/v1/library/papers

Paper in Bibliothek aufnehmen (mit Embedding).

```bash
curl -s -X POST "http://localhost:8000/api/v1/library/papers" \
  -H "Content-Type: application/json" \
  -d '{"pmid": "98765432", "title": "Gene editing review", "abstract": "Overview of CRISPR...", "authors": ["Author A"], "year": 2024, "journal": "Science", "doi": null}'
```

Response: PubMedSearchResponse.

---

#### GET /api/v1/library/papers

Liste mit optionalen Filtern (year, journal, limit, offset).

```bash
curl -s "http://localhost:8000/api/v1/library/papers?limit=20&offset=0&year=2023&journal=Nature"
```

Response: Array von Paper-Objekten.

---

#### POST /api/v1/library/search/semantic

Semantische Suche (Vektor-Ähnlichkeit). Body: query, limit, threshold (optional).

```bash
curl -s -X POST "http://localhost:8000/api/v1/library/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{"query": "Herzerkrankungen Therapie", "limit": 10, "threshold": 1.0}'
```

Response: Liste von Paper-Objekten, optional mit `similarity_score`.

---

#### POST /api/v1/library/rag

Stellt eine natürlichsprachige Frage an die gespeicherte Bibliothek. Rate Limit: 10/minute.

```bash
curl -X POST http://localhost:8000/api/v1/library/rag \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Welche Therapien für BRCA1?",
    "top_k": 5,
    "language": "de"
  }'
```

Response:

```json
{
  "answer": "In deinen Papers werden...",
  "sources": [
    {
      "pmid": "12345678",
      "title": "BRCA1 targeted therapy...",
      "similarity_score": 94.0,
      "used_chars": 487
    }
  ],
  "question": "Welche Therapien für BRCA1?",
  "model_used": "mistral",
  "context_papers": 3
}
```

---

#### POST /api/v1/library/summarize

KI-Zusammenfassung für ein Paper. Body: pmid, language.

```bash
curl -s -X POST "http://localhost:8000/api/v1/library/summarize" \
  -H "Content-Type: application/json" \
  -d '{"pmid": "98765432", "language": "de"}'
```

Response:

```json
{ "summary": "Diese Arbeit beschreibt...", "cached": false, "language": "de" }
```

---

#### DELETE /api/v1/library/papers/{pmid}

Paper aus Bibliothek entfernen.

```bash
curl -s -X DELETE "http://localhost:8000/api/v1/library/papers/98765432"
```

Response: 204 No Content.

---

#### POST /api/v1/library/bulk-import

Mehrere Papers importieren (multipart: file).

```bash
curl -s -X POST "http://localhost:8000/api/v1/library/bulk-import" \
  -H "Authorization: Bearer <token>" \
  -F "file=@papers.csv"
```

Response: `{"imported": 50, "skipped": 0, "errors": []}`.

---

#### POST /api/v1/library/reembed-all

Alle Papers ohne Embedding neu einbetten.

```bash
curl -s -X POST "http://localhost:8000/api/v1/library/reembed-all"
```

Response: `{"reembedded": 12, "message": "12 Papers neu eingebettet"}`.

---

### Pseudonymize (API-Prefix: /api/v1)

#### POST /api/v1/pseudonymize

Text pseudonymisieren. Body: text, language.

```bash
curl -s -X POST "http://localhost:8000/api/v1/pseudonymize" \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient Max Mustermann, geb. 15.03.1970. Tel. 0711-123456.", "language": "de"}'
```

Response:

```json
{
  "pseudonymized_text": "Patient <PERSON_1>, geb. <DATE_TIME_1>. Tel. <PHONE_NUMBER_1>.",
  "mapping_id": "a1b2c3d4e5f6...",
  "entities_found": [{"type": "PERSON", "start": 7, "end": 21}, {"type": "DATE_TIME", "start": 29, "end": 39}]
}
```

---

#### POST /api/v1/pseudonymize/restore

Originaltext wiederherstellen. Erfordert Header `X-Restore-API-Key`. Body: pseudonymized_text, mapping_id.

```bash
curl -s -X POST "http://localhost:8000/api/v1/pseudonymize/restore" \
  -H "Content-Type: application/json" \
  -H "X-Restore-API-Key: <RESTORE_API_KEY>" \
  -d '{"pseudonymized_text": "Patient <PERSON_1>, geb. <DATE_TIME_1>.", "mapping_id": "a1b2c3d4e5f6..."}'
```

Response: `{"restored_text": "Patient Max Mustermann, geb. 15.03.1970."}`.

---

#### POST /api/v1/pseudonymize/reverse

De-Pseudonymisierung (berechtigter User). Body: mapping_id.

```bash
curl -s -X POST "http://localhost:8000/api/v1/pseudonymize/reverse" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"mapping_id": "a1b2c3d4e5f6..."}'
```

Response: mapping_id, original_text, pseudonymized_text, accessed_by, access_time.

---

#### GET /api/v1/pseudonymize/audit-log

Audit-Log (limit, offset).

```bash
curl -s "http://localhost:8000/api/v1/pseudonymize/audit-log?limit=100&offset=0"
```

Response: Array von Einträgen (operation_id, user_id, timestamp, entities_count, input_hash, operation_type, language, mapping_id).

---

### Phenopackets (API-Prefix: /api/v1)

#### GET /api/v1/phenopackets/hpo/search

HPO-Terme suchen. Query-Parameter: q.

```bash
curl -s "http://localhost:8000/api/v1/phenopackets/hpo/search?q=breast"
```

Response: Liste von HPO-Termen.

---

#### POST /api/v1/phenopackets

Phenopacket anlegen. Body: pseudonym_id, phenotypes, diseases, genes_of_interest, notes.

```bash
curl -s -X POST "http://localhost:8000/api/v1/phenopackets" \
  -H "Content-Type: application/json" \
  -d '{"pseudonym_id": "P-2024-001", "phenotypes": ["HP:0003002"], "diseases": ["OMIM:114480"], "genes_of_interest": ["BRCA1"], "notes": null}'
```

Response: Erstelltes Phenopacket (GA4GH-Struktur).

---

#### GET /api/v1/phenopackets

Alle Phenopackets (nach Isolation).

```bash
curl -s "http://localhost:8000/api/v1/phenopackets"
```

Response: Array von Phenopacket-JSON.

---

#### GET /api/v1/phenopackets/{id}

Ein Phenopacket nach Pseudonym-ID.

```bash
curl -s "http://localhost:8000/api/v1/phenopackets/P-2024-001"
```

---

#### GET /api/v1/phenopackets/{id}/export

Export als JSON-LD.

```bash
curl -s "http://localhost:8000/api/v1/phenopackets/P-2024-001/export"
```

---

#### POST /api/v1/phenopackets/validate

Phenopacket-JSON validieren. Body: Phenopacket-Objekt.

```bash
curl -s -X POST "http://localhost:8000/api/v1/phenopackets/validate" \
  -H "Content-Type: application/json" \
  -d '{"id": "example", "subject": {}, "phenotypicFeatures": []}'
```

Response: Validierungsergebnis.

---

#### DELETE /api/v1/phenopackets/{id}

Phenopacket löschen.

```bash
curl -s -X DELETE "http://localhost:8000/api/v1/phenopackets/P-2024-001"
```

Response: 204 No Content.

---

#### GET /api/v1/phenopackets/{id}/assets

Gelinkte DRS-Assets zu einem Phenopacket auflisten.

```bash
curl -s "http://localhost:8000/api/v1/phenopackets/P-2024-001/assets"
```

Response:

```json
[
  {
    "asset_id": 1,
    "drs_object_id": "demo_BRCA1_exon10.fasta",
    "file_type": "other"
  }
]
```

---

#### POST /api/v1/phenopackets/{id}/assets

DRS-Asset mit Phenopacket verknüpfen.

```bash
curl -s -X POST "http://localhost:8000/api/v1/phenopackets/P-2024-001/assets" \
  -H "Content-Type: application/json" \
  -d '{"drs_object_id": "demo_variants.vcf", "file_type": "vcf"}'
```

---

#### DELETE /api/v1/phenopackets/{id}/assets/{asset_id}

Asset-Link entfernen.

```bash
curl -s -X DELETE "http://localhost:8000/api/v1/phenopackets/P-2024-001/assets/1"
```

Response: 204 No Content.

---

### PhenoFlow (API-Prefix: /api/v1)

#### POST /api/v1/phenoflow/runs

Search-to-Execution starten (HPO Query -> DRS Resolution -> WES Submit).

```bash
curl -s -X POST "http://localhost:8000/api/v1/phenoflow/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "hpo_terms": ["HP:0001250"],
    "file_type": "bam",
    "limit_matches": 50,
    "workflow_url": "nextflow",
    "workflow_type": "NEXTFLOW",
    "workflow_type_version": "DSL2",
    "workflow_params_template": {
      "input_bam": "{{drs_stream_url}}",
      "sample_id": "{{pseudonym_id}}"
    }
  }'
```

Response: `phenoflow_run_id`, `matched_count`, `submitted_count`, `items[]`.

---

#### GET /api/v1/phenoflow/runs

PhenoFlow-Runs (scoped) auflisten.

```bash
curl -s "http://localhost:8000/api/v1/phenoflow/runs"
```

---

#### GET /api/v1/phenoflow/runs/{phenoflow_run_id}

Details eines PhenoFlow-Runs inkl. Item-Provenance und WES-State.

```bash
curl -s "http://localhost:8000/api/v1/phenoflow/runs/<phenoflow_run_id>"
```

---

### DRS (Basis-URL: /ga4gh/drs/v1)

#### GET /ga4gh/drs/v1/service-info

DRS-Service-Metadaten.

```bash
curl -s "http://localhost:8000/ga4gh/drs/v1/service-info"
```

---

#### GET /ga4gh/drs/v1/objects

Alle DRS-Objekte.

```bash
curl -s "http://localhost:8000/ga4gh/drs/v1/objects" -H "Authorization: Bearer <token>"
```

Response: `{"objects": [{"id": "...", "name": "...", "size": 1234, ...}]}`.

---

#### POST /ga4gh/drs/v1/objects

Objekt registrieren (Upload oder Pfad). Form: name, file (oder path/server_path), description.

```bash
curl -s -X POST "http://localhost:8000/ga4gh/drs/v1/objects" \
  -H "Authorization: Bearer <token>" \
  -F "name=myfile.fasta" \
  -F "file=@/path/to/myfile.fasta"
```

Response: DRS-Objekt (id, name, size, access_methods, …).

---

#### GET /ga4gh/drs/v1/objects/{object_id}

Metadaten eines Objekts.

```bash
curl -s "http://localhost:8000/ga4gh/drs/v1/objects/myfile.fasta" -H "Authorization: Bearer <token>"
```

---

#### GET /ga4gh/drs/v1/objects/{object_id}/stream

Datei streamen (Download).

```bash
curl -s -o downloaded.fasta "http://localhost:8000/ga4gh/drs/v1/objects/myfile.fasta/stream" -H "Authorization: Bearer <token>"
```

---

### BLAST (API-Prefix: /api/v1)

#### GET /api/v1/blast/db-status

BLAST-Datenbank verfügbar?

```bash
curl -s "http://localhost:8000/api/v1/blast/db-status"
```

Response (verfügbar): `{"available": true, "database": "/blast/db/nt", "info": "..."}`. Nicht verfügbar: `{"available": false, "reason": "...", "setup": "Run ./setup-blast-db.sh"}`.

---

#### POST /api/v1/blast/search

BLAST starten. Body: query (FASTA oder Sequenz), database (z. B. nt).

```bash
curl -s -X POST "http://localhost:8000/api/v1/blast/search" \
  -H "Content-Type: application/json" \
  -d '{"query": ">seq1\nATGAAAGCTTGGGCTAGCTAGCTAG", "database": "nt"}'
```

Response: `{"run_id": "uuid-..."}`.

---

#### GET /api/v1/blast/results/{run_id}

BLAST-Ergebnisse. Query: papers=true optional (related papers).

```bash
curl -s "http://localhost:8000/api/v1/blast/results/<run_id>?papers=true"
```

Response: results (run_id, hits, statistics), optional papers.

---

### WES (Basis-URL: /ga4gh/wes/v1)

#### GET /ga4gh/wes/v1/service-info

WES-Infos.

```bash
curl -s "http://localhost:8000/ga4gh/wes/v1/service-info" -H "Authorization: Bearer <token>"
```

Response: Service-Metadaten (id, name, type, workflow_type_versions, system_state_counts, …).

---

#### POST /ga4gh/wes/v1/runs

Workflow starten. Form: workflow_type, workflow_type_version, workflow_url, optional workflow_params, tags, etc.

```bash
curl -s -X POST "http://localhost:8000/ga4gh/wes/v1/runs" \
  -H "Authorization: Bearer <token>" \
  -F "workflow_type=NEXTFLOW" \
  -F "workflow_type_version=DSL2" \
  -F "workflow_url=blast"
```

Response: `{"run_id": "uuid-..."}`.

---

#### GET /ga4gh/wes/v1/runs

Liste der Runs. Query: page_size, page_token.

```bash
curl -s "http://localhost:8000/ga4gh/wes/v1/runs?page_size=20" -H "Authorization: Bearer <token>"
```

---

#### GET /ga4gh/wes/v1/runs/{run_id}

Run-Details (Logs, Outputs).

```bash
curl -s "http://localhost:8000/ga4gh/wes/v1/runs/<run_id>" -H "Authorization: Bearer <token>"
```

---

#### GET /ga4gh/wes/v1/runs/{run_id}/status

Nur Status.

```bash
curl -s "http://localhost:8000/ga4gh/wes/v1/runs/<run_id>/status" -H "Authorization: Bearer <token>"
```

Response: `{"run_id": "...", "state": "COMPLETE"}` (oder RUNNING, FAILED, …).

---

#### POST /ga4gh/wes/v1/runs/{run_id}/cancel

Run abbrechen.

```bash
curl -s -X POST "http://localhost:8000/ga4gh/wes/v1/runs/<run_id>/cancel" -H "Authorization: Bearer <token>"
```

Response: `{"run_id": "..."}`.

---

### Notebooks (API-Prefix: /api/v1)

#### POST /api/v1/notebooks

Notizbuch anlegen. Body: title, content, tags.

```bash
curl -s -X POST "http://localhost:8000/api/v1/notebooks" \
  -H "Content-Type: application/json" \
  -d '{"title": "Experiment 2024-03", "content": "# Ziel\n...", "tags": ["CRISPR"]}'
```

Response: Notebook-Objekt (id, title, content, tags, linked_pmids, linked_drs_ids, linked_phenopacket_ids, ai_summary, ai_next_steps, created_at, updated_at).

---

#### GET /api/v1/notebooks

Liste (skip, limit, search, tag).

```bash
curl -s "http://localhost:8000/api/v1/notebooks?skip=0&limit=20&search=CRISPR&tag=genetics"
```

Response: `{"items": [...], "total": 5, "skip": 0, "limit": 20}`.

---

#### GET /api/v1/notebooks/{id}

Ein Notizbuch.

```bash
curl -s "http://localhost:8000/api/v1/notebooks/<notebook_id>"
```

---

#### PUT /api/v1/notebooks/{id}

Notizbuch aktualisieren. Body: title, content, tags (optional).

```bash
curl -s -X PUT "http://localhost:8000/api/v1/notebooks/<notebook_id>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Neuer Titel", "content": "# Aktualisiert\n...", "tags": ["tag1"]}'
```

---

#### POST /api/v1/notebooks/{id}/ai-assist

KI-Assistent. Body: mode (summary | next_steps | both).

```bash
curl -s -X POST "http://localhost:8000/api/v1/notebooks/<notebook_id>/ai-assist" \
  -H "Content-Type: application/json" \
  -d '{"mode": "both"}'
```

Response: Aktualisiertes Notebook inkl. ai_summary, ai_next_steps.

---

#### POST /api/v1/notebooks/{id}/link

Ressource verknüpfen. Body: type (paper | drs | phenopacket), id (PMID, DRS-ID oder Pseudonym-ID).

```bash
curl -s -X POST "http://localhost:8000/api/v1/notebooks/<notebook_id>/link" \
  -H "Content-Type: application/json" \
  -d '{"type": "paper", "id": "12345678"}'
```

---

#### GET /api/v1/notebooks/{id}/export

Export als Markdown oder PDF. Query: format=md oder format=pdf.

```bash
curl -s -o notebook.md "http://localhost:8000/api/v1/notebooks/<notebook_id>/export?format=md"
```

---

#### DELETE /api/v1/notebooks/{id}

Notizbuch löschen.

```bash
curl -s -X DELETE "http://localhost:8000/api/v1/notebooks/<notebook_id>"
```

Response: 204 No Content.

---

### FAIR Export (API-Prefix: /api/v1)

#### POST /api/v1/fair-export/preview

Vorschau (Anzahlen). Body: title, include_papers, include_phenopackets, include_notebooks, include_drs.

```bash
curl -s -X POST "http://localhost:8000/api/v1/fair-export/preview" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Dataset", "include_papers": true, "include_phenopackets": true, "include_notebooks": true, "include_drs": false}'
```

Response: papers_count, phenopackets_count, notebooks_count, include_*-Flags.

---

#### POST /api/v1/fair-export/compliance-check

FAIR-Score berechnen. Body: title, description, license, funding, etc.

```bash
curl -s -X POST "http://localhost:8000/api/v1/fair-export/compliance-check" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Dataset", "description": "Description", "license": "CC-BY-4.0", "funding": "DFG 123456"}'
```

Response: FAIRComplianceReport (findable, accessible, interoperable, reusable, score, recommendations).

---

#### POST /api/v1/fair-export/download

ZIP herunterladen. Body: FAIRExportOptions (title, description, authors, license, include_*, keywords, funding).

```bash
curl -s -o fair_export.zip -X POST "http://localhost:8000/api/v1/fair-export/download" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Dataset", "description": "", "authors": ["Author A"], "license": "CC-BY-4.0", "include_papers": true, "include_phenopackets": true, "include_notebooks": true, "include_drs": false, "keywords": [], "funding": null}'
```

---

#### POST /api/v1/fair-export/zenodo

Paket zu Zenodo hochladen. Body: options (FAIRExportOptions), optional zenodo_token.

```bash
curl -s -X POST "http://localhost:8000/api/v1/fair-export/zenodo" \
  -H "Content-Type: application/json" \
  -d '{"options": {"title": "My Dataset", "description": "", "authors": ["Author A"], "license": "CC-BY-4.0", "include_papers": true, "include_phenopackets": true, "include_notebooks": true, "include_drs": false, "keywords": [], "funding": null}}'
```

Response: deposition_id, doi, record_url, message.

---

### MII Export, Consent, Terminology (API-Prefix: /api/v1)

#### POST /api/v1/consents

Broad-Consent-Eintrag für ein Pseudonym anlegen.

```bash
curl -s -X POST "http://localhost:8000/api/v1/consents" \
  -H "Content-Type: application/json" \
  -d '{
    "pseudonym_id": "P-2026-001",
    "policy_version": "2026-1",
    "status": "active",
    "valid_from": "2026-01-01T00:00:00Z",
    "covered_project_ids": ["proj-a"]
  }'
```

#### POST /api/v1/mii-export/bundles

Synchroner MII-orientierter FHIR-Bundle-Export.

```bash
curl -s -X POST "http://localhost:8000/api/v1/mii-export/bundles" \
  -H "Content-Type: application/json" \
  -d '{
    "pseudonym_ids": ["P-2026-001"],
    "modules": ["diagnosis", "laboratory", "biospecimen", "genomics"],
    "strict_profile_validation": true
  }'
```

#### POST /api/v1/mii-export/jobs

Asynchronen Exportjob starten (202 Accepted).

```bash
curl -s -X POST "http://localhost:8000/api/v1/mii-export/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "pseudonym_ids": ["P-2026-001"],
    "modules": ["diagnosis", "laboratory"]
  }'
```

#### GET /api/v1/mii-export/jobs/{job_id}

Jobstatus (queued/running/succeeded/failed/dead_letter) inkl. Validator-Metadaten.

#### GET /api/v1/mii-export/jobs/{job_id}/artifact

FHIR-Bundle-Artefakt eines abgeschlossenen Jobs herunterladen.

#### GET /api/v1/mii-export/jobs/metrics

Per-User Jobzahlen nach Status.

#### POST /api/v1/terminology/overrides

Kuratierte Override-Regel für Terminologie-Mapping anlegen/ersetzen.

```bash
curl -s -X POST "http://localhost:8000/api/v1/terminology/overrides" \
  -H "Content-Type: application/json" \
  -d '{
    "module": "diagnosis",
    "raw_id": "ORPHA:558",
    "target_system": "http://snomed.info/sct",
    "target_code": "999001",
    "target_display": "Governed override"
  }'
```

#### GET /api/v1/terminology/overrides

Alle aktiven/inaktiven Terminologie-Overrides listen.

#### DELETE /api/v1/terminology/overrides/{override_id}

Override deaktivieren (soft delete).

---

**Rechtlich sichere Einordnung (für technische Doku):**

- Die Endpunkte liefern technische Unterstützung für MII-nahe Workflows, sind aber **keine rechtsverbindliche Compliance-Aussage**.
- MII/FHIR-Exporte sind **implementierungsabhängig zu validieren** (lokale Prozesse, IG-Versionen, Governance).
- Dieses Dokument ersetzt **keine** medizinische, regulatorische oder rechtliche Bewertung durch die verantwortliche Stelle.

---

### Auth (API-Prefix: /api/v1)

#### GET /api/v1/auth/login

Redirect zur OIDC-Anmeldung. Query: provider=oidc | google | microsoft. Im Browser: `http://localhost:8000/api/v1/auth/login?provider=oidc`.

---

#### GET /api/v1/auth/callback

OIDC Callback (Code gegen Token). Wird vom Provider aufgerufen.

---

#### GET /api/v1/auth/me

Aktueller User (inkl. Isolation, team_id, scope).

```bash
curl -s "http://localhost:8000/api/v1/auth/me" -H "Authorization: Bearer <token>"
```

---

#### GET /api/v1/auth/status

Auth-Konfiguration.

```bash
curl -s "http://localhost:8000/api/v1/auth/status"
```

Response: auth_enabled, oidc_issuer, mode, ga4gh_passport_support, supported_providers.

---

### Health (API-Prefix: /api/v1)

#### GET /api/v1/health

Liveness: Status, Version, Feature-Flags (embeddings, semantic_search, llm_summaries, spacy_ner, blast, nextflow), deployment, data_sovereignty.

```bash
curl -s "http://localhost:8000/api/v1/health"
```

---

#### GET /api/v1/health/ready

Readiness: Datenbankverbindung.

```bash
curl -s "http://localhost:8000/api/v1/health/ready"
```

Response: `{"status": "ready", "database": "connected"}` oder `{"status": "not_ready", "database": "disconnected", "error": "..."}`.

---

### GAIA-X (API-Prefix: /api/v1)

#### GET /api/v1/gaia-x/self-description

GAIA-X Self-Description (JSON).

```bash
curl -s "http://localhost:8000/api/v1/gaia-x/self-description"
```

---

#### GET /api/v1/gaia-x/compliance

GAIA-X Compliance-Status (principles, standards, deployment_model, data_location, certification_status).

```bash
curl -s "http://localhost:8000/api/v1/gaia-x/compliance"
```

---

## Konfigurationsreferenz

Alle relevanten Umgebungsvariablen (`.env`) — aus `backend/app/core/config.py`. Beispielwerte dienen der Orientierung.

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| **Application** | | |
| APP_VERSION | Anzeigeversion (Health, UI) | `1.4.2` |
| DEBUG | Debug-Modus | `false` |
| ENVIRONMENT | Umgebungsname | `development` |
| DEPLOYMENT | Ziel (z. B. railway für Demo-Limits) | `` oder `railway` |
| **API** | | |
| API_V1_PREFIX | API-Prefix | `/api/v1` |
| **Database** | | |
| DATABASE_URL | PostgreSQL (async, z. B. asyncpg) | `postgresql+asyncpg://user:pass@localhost:5432/db` |
| **CORS** | | |
| CORS_ORIGINS | Komma-getrennte Origins | `http://localhost:5173,http://localhost:3000` |
| **LLM** | | |
| LLM_PROVIDER | Routing: `auto`, `anthropic`, `ollama`, `openai_compatible` | `auto` |
| ANTHROPIC_API_KEY | Claude API Key (primär) | `sk-ant-...` oder leer |
| OLLAMA_URL | Ollama-URL (Fallback) | `http://localhost:11434` |
| LLM_CLAUDE_MODEL | Claude-Modell | `claude-sonnet-4-6` |
| OLLAMA_MODEL | Ollama-Modell | `mistral:7b` |
| OPENAI_BASE_URL | OpenAI-kompatible API (inkl. `/v1`), z. B. SGLang | `http://localhost:30000/v1` |
| OPENAI_MODEL | Modell-ID beim OpenAI-kompatiblen Server | z. B. Hugging-Face-Pfad |
| OPENAI_API_KEY | Optionaler Bearer für lokales Inference | leer |
| **Pseudonymisierung** | | |
| PSEUDONYMIZATION_ENCRYPTION_KEY | AES-256 Key (64 Hex-Zeichen) | `openssl rand -hex 32` |
| RESTORE_API_KEY | API-Key für Restore (X-Restore-API-Key) | optional |
| DEPSEUDO_ACCESS | Wer darf de-pseudonymisieren | `owner` \| `team` \| `admin` |
| CUSTOM_PATIENT_ID_PATTERNS | Regex für Patienten-IDs (kommagetrennt) | `L-\d{4}-\d{5},P-\d{4,8}` |
| **WES** | | |
| WES_WORK_DIR | Arbeitsverzeichnis für WES-Runs | `/tmp/wes` |
| **BLAST** | | |
| BLAST_WORKFLOW_PATH | Pfad zu blast_search.nf | optional |
| **DRS** | | |
| DRS_STORAGE_PATH | Stammverzeichnis DRS-Objekte | `/tmp/drs` |
| DRS_BASE_URL | Basis-URL für DRS | `http://localhost:8000/ga4gh/drs/v1` |
| **OIDC** | | |
| OIDC_ISSUER | Issuer-URL (z. B. Keycloak Realm) | `https://keycloak.example/realms/my` |
| OIDC_CLIENT_ID | Client-ID | |
| OIDC_CLIENT_SECRET | Client-Secret | |
| OIDC_REDIRECT_URI | Redirect nach Login | `http://localhost:8000/api/v1/auth/callback` |
| JWT_SECRET | Session/Token (min. 32 Zeichen wenn gesetzt) | optional |
| JWT_ALGORITHM | Algorithmus | `RS256` |
| MICROSOFT_TENANT_ID | Azure AD Tenant (bei Microsoft Login) | `common` |
| **FAIR Export** | | |
| ZENODO_TOKEN | Zenodo API Token | optional |
| **Isolation** | | |
| ISOLATION_MODE | Sichtbarkeit der Daten | `user` \| `team` \| `open` |
| **MII Export / Consent** | | |
| MII_KDS_RELEASE | Ziel-Release für MII-KDS Profilset | `2026` |
| MII_IG_PACKAGE_ID | IG-Package-ID für Validator/Metadaten | `de.medizininformatikinitiative.kerndatensatz.meta` |
| MII_IG_PACKAGE_VERSION | IG-Package-Version | `2026.0.0` |
| MII_DEFAULT_CONSENT_POLICY_ID | Default Policy-ID für Broad Consent | `mii-broad-consent` |
| MII_BUNDLE_ATTACH_META_PROFILE | Profile-CANONICAL in `meta.profile` anhängen | `true` |
| MII_EXPORT_MAX_ATTEMPTS | Max. Retry-Versuche für async Exportjobs | `3` |
| MII_EXPORT_RETRY_BASE_SECONDS | Basis für Exponential-Backoff | `2.0` |

---

## Deployment

### Docker Compose

Vollständige Installation mit Backend, Frontend, Datenbank und optionalen Diensten (Ollama, Nextflow) über Docker Compose. Siehe [INSTALL.md](INSTALL.md) und die Skripte im Projektroot (z. B. `install.sh`, `docker-compose.full.yml`). Nach dem Start:

- Backend/API: Port 8000
- Frontend: Port 5173 (Vite) oder gebaut als statische Dateien hinter Reverse-Proxy
- Health: `http://<host>:8000/api/v1/health`

### Railway

Für Demo-Deployments kann die App auf Railway ausgerollt werden. `DEPLOYMENT=railway` aktiviert ggf. Einschränkungen (z. B. semantische Suche auf Railway kann leer zurückgeben). Datenbank und Secrets (z. B. PSEUDONYMIZATION_ENCRYPTION_KEY, DATABASE_URL) in Railway als Environment Variables setzen.

### Eigener Server

- **Backend:** Python 3.11+, FastAPI, PostgreSQL mit pgvector. Abhängigkeiten per `pip install -r backend/requirements.txt`. Alembic für Migrationen. Empfohlen: Gunicorn/Uvicorn hinter Reverse-Proxy (nginx), HTTPS.
- **Frontend:** `npm run build` in `frontend/`, statische Dateien von nginx oder CDN ausliefern; API-Proxy auf Backend (z. B. `/api` → `http://127.0.0.1:8000/api`).
- **OIDC:** Für Produktion OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET und OIDC_REDIRECT_URI konfigurieren; Redirect-URI beim IdP registrieren.
- **BLAST/Nextflow:** Für BLAST und WES-Pipelines BLAST-DB und Nextflow auf dem Server installieren bzw. in Containern bereitstellen.

Weitere Details: [INSTALL.md](INSTALL.md), [SECURITY.md](../SECURITY.md).

---

*Letzte Aktualisierung: 2026-04-15, Version 1.4.2*
