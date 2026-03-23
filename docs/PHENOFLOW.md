# PhenoFlow v0.1 (Phenopackets -> WES via DRS)

PhenoFlow ist der v0.1 Connector, der eine phänotypische Anfrage (HPO Terms) in automatisierte WES-Workflow Runs übersetzt.
Er nutzt dabei:

- gespeicherte Phenopackets (lokal in `patient_records`, JSONB/JSON: `phenopacket_json`)
- eine neue Mapping-Tabelle `phenopacket_assets` (Phenopacket -> DRS `object_id`)
- den bestehenden DRS-Service, um aus `drs_object_id` einen stream/access-url zu bilden
- den bestehenden WES-Service, um pro Treffer einen `RunRequest` einzureichen

## Scope v0.1 (ohne Data-Connect Federation)

1. Nutzer liefert:
   - `hpo_terms`: Liste von HPO CURIEs (z.B. `HP:0001250`)
   - optionalen Filter auf den Asset-Typ (`file_type`)
   - Workflow-Descriptor inkl. Parameter-Template
2. System:
   - findet innerhalb der aktuellen Isolation (user/team/open) passende gespeicherte Phenopackets
   - verbindet jeden Treffer mit einem verknüpften genomischen Asset (`phenopacket_assets`)
   - löst den DRS `object_id` auf einen stream/access-url auf
   - erstellt einen WES Run pro Phenopacket-Asset-Paar
3. Provenance wird persistiert, ohne sensible Nutzdaten aus Genomen oder klinischen Texten auszugeben.

## Backend API (v0.1)

Prefix: `/api/v1`

### 1. Submit Run

`POST /phenoflow/runs`

Request: `PhenoFlowRunRequest`

Wichtige Felder:

- `hpo_terms`: Liste von HPO CURIEs
- `file_type`: optionaler Filter (`bam|cram|vcf|fastq|other`)
- `limit_matches`: Cap pro Request
- `workflow_url`: Workflow URL/Descriptor (z.B. `nextflow`, oder lokale Pipeline-Datei nach WES-Validierung)
- `workflow_type`, `workflow_type_version`: GA4GH WES Descriptoren
- `workflow_params_template`: Template für `workflow_params` (String-Platzhalter werden je Item ersetzt)

Template Placeholders (v0.1):

- `{{drs_object_id}}` -> DRS `object_id` des Assets
- `{{drs_stream_url}}` -> Access/Stream URL aus DRS
- `{{pseudonym_id}}` -> Phenopacket `pseudonym_id`
- `{{file_type}}` -> Asset `file_type`

Response: `PhenoFlowRunResponse`

- `phenoflow_run_id`: UUID string
- `matched_count`: Anzahl erkannter Phenopacket-Asset-Paare bis zur Limit-Grenze
- `submitted_count`: Anzahl erfolgreich eingereichter WES Runs
- `items`: Liste der Item-Provenance (Queued/Error je Item)
- `errors`: aggregierte Fehlermeldungen (z.B. DRS/Submission Errors)

### 2. Run Detail

`GET /phenoflow/runs/{phenoflow_run_id}`

Response: `PhenoFlowRunDetailResponse`

- `status`: Status des PhenoFlow-Run-Master
- `query_spec`, `workflow_spec`: Persistierte Spezifikation zur Nachvollziehbarkeit
- `items`: Item-level Provenance; falls möglich werden WES `WorkflowRun.state` Werte mitgeführt

## Asset Linking (für das Mapping)

PhenoFlow benötigt eine kanonische Relation:
`Phenopacket (pseudonym_id)` -> `DRS object_id` (+ `file_type`)

Die Mapping-Endpunkte sind:

### List Linked Assets

`GET /phenopackets/{pseudonym_id}/assets`

Response: Liste von Assets (`asset_id`, `drs_object_id`, `file_type`)

### Link Asset

`POST /phenopackets/{pseudonym_id}/assets`

Request: `PhenopacketAssetLinkRequest`

- `drs_object_id`: DRS Objekt-ID (relativ unter `drs_storage_path`)
- `file_type`: Asset-Typ

Response: `PhenopacketAssetLinkResponse` inkl. `asset_id`

### Delete Asset Mapping

`DELETE /phenopackets/{pseudonym_id}/assets/{asset_id}`

Status: `204 No Content`

## Datenmodell (neue Tabellen)

Alle Tabellen werden über Alembic Migrationen bereitgestellt.

### `phenopacket_assets`

Mapping-Tabelle:

- `id`: PK
- `pseudonym_id`: FK/Index auf `patient_records.pseudonym_id`
- `drs_object_id`: DRS `object_id` (String)
- `file_type`: `bam|cram|vcf|fastq|other`
- `user_id`, `team_id`: Isolation scoping Felder
- `created_at`, `updated_at`

### `phenoflow_runs`

Master-Record pro Suchsubmission:

- `phenoflow_run_id`: UUID
- `status`: String (v0.1 nutzt typischerweise `SUBMITTED`)
- `query_spec`: JSON (persistierte HPO Terms + Filter)
- `workflow_spec`: JSON (Workflow Descriptor + Template)
- `user_id`, `team_id`, `start_time`, `end_time`

### `phenoflow_run_items`

Item-level Provenance pro Phenopacket-Asset Paar:

- `phenoflow_run_id`: FK
- `pseudonym_id`, `drs_object_id`, `file_type`
- `wes_run_id`: optional (bei Submission-Error `NULL`)
- `state_snapshot`: z.B. `QUEUED` oder `ERROR`
- `error`: optionaler Error-Text
- `created_at`

## Privacy & DSGVO Constraints

PhenoFlow speichert bewusst keine klinischen Texte oder dekodierte Genomdaten.
Persistiert werden nur:

- Phenopacket Provenance über `pseudonym_id`
- DRS Provenance über `drs_object_id` (Identifier)
- WES Provenance über `wes_run_id`

Beim Lösen/Erzeugen von `workflow_params` werden nur DRS Access URLs in den WES Parametern übergeben.
Klinische Inhalte werden nicht außerhalb des Systems an externe Dienste gesendet.

## Deployment / Konfigurationsknobs (v0.1)

Wichtige Settings:

- `DATABASE_URL`: Postgres (prod) oder SQLite in Tests
- `DRS_STORAGE_PATH`, `DRS_BASE_URL`: DRS File-Storage und URL-Generation
- `WES_WORK_DIR`: Arbeitsdirectory für WES Submissions
- `ISOLATION_MODE`: `user|team|open` (wirkt auf Phenopacket- und Asset-Zugriff)

## GA4GH Alignment (kurzer Hinweis)

PhenoFlow nutzt intern GA4GH-konforme Konzepte:

- Phenopackets als lokales Datenformat für HPO Features
- WES `RunRequest` für Workflow Execution

Data-Connect Federation ist in v0.1 explizit nicht enthalten.

