# BioResearch Assistant ↔ Solum subject bridge

**Status:** 2026-08-12 · org plan **F3**
**Contract:** Solum [ADR 0003](https://github.com/SynapticFour/Solum/blob/main/docs/adr/0003-subject-bridge.md)

## Mapping

| BRA | Solum subject-link |
|-----|-------------------|
| Phenopacket / `pseudonym_id` | `phenopacket_id` (and default `solum_subject_id` if not overridden) |
| Optional explicit subject | `solum_subject_id` |
| Optional linked DRS object | `ferrum_drs_id` |

Default rule: **`solum_subject_id = phenopacket_id`** unless the caller supplies a different clinical subject id (e.g. FHIR Patient.id). That string must match Ferrum DRS metadata `solum_subject`.

## API

`POST /api/v1/phenopackets/{pseudonym_id}/solum-subject-link`

Body (all optional except using path id as phenopacket id):

```json
{
  "solum_subject_id": "subj-pilot-001",
  "ferrum_drs_id": "drs.example/object-1",
  "upsert": true
}
```

When `SOLUM_BASE_URL` (+ `SOLUM_SIDECAR_TOKEN`) is set and `upsert` is true, BRA POSTs to Solum `/v1/cdr/subject-link`. Otherwise returns the payload for the operator to apply.

## Env

| Variable | Meaning |
|----------|---------|
| `SOLUM_BASE_URL` | Sidecar base URL (e.g. `http://127.0.0.1:8787`) |
| `SOLUM_SIDECAR_TOKEN` | Bearer / sidecar token |
| `SOLUM_SUBJECT_BRIDGE_UPSERT` | Default `true` when URL set |

## Related

- Operator runbook: Ferrum `docs/solum-subject-bridge-runbook.md`
- Showcase co-custody: Showcase `docs/for-customers/co-custody.md`
