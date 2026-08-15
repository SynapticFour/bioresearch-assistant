# BioResearch Assistant ↔ Solum subject bridge

**Status:** 2026-08-15 · contract aligned with Solum `SubjectLinkBody`
**Contract:** Solum [ADR 0003](https://github.com/SynapticFour/Solum/blob/main/docs/adr/0003-subject-bridge.md)

BRA is **not** a Ferrum wrapper. This join is optional: Phenopacket id → Solum clinical subject. Ferrum DRS objects that carry `solum_subject` can share the same string.

## Mapping

| BRA | Solum `POST /v1/cdr/subject-link` |
|-----|-----------------------------------|
| Authenticated `sub` | `actor` (required) |
| Default `solum:cdr:write` | `capability[]` (required) |
| Default `research` | `purpose` (required) |
| Phenopacket / `pseudonym_id` | `phenopacket_id` and default `solum_subject_id` |
| Optional explicit subject | `solum_subject_id` |
| Optional linked DRS object | `ferrum_drs_id` |

Default rule: **`solum_subject_id = phenopacket_id`** unless the caller supplies a different clinical subject id (e.g. FHIR Patient.id). That string must match Ferrum DRS metadata `solum_subject` when Ferrum is in the picture.

Track B: Solum returns **503** if the CDR façade is not configured (no EHRbase). That is Solum being honest, not a BRA bug.

## API

`POST /api/v1/phenopackets/{pseudonym_id}/solum-subject-link`

```json
{
  "solum_subject_id": "subj-pilot-001",
  "ferrum_drs_id": "drs.example/object-1",
  "purpose": "research",
  "capability": ["solum:cdr:write"],
  "upsert": true
}
```

When `SOLUM_BASE_URL` (+ `SOLUM_SIDECAR_TOKEN`) is set and `upsert` is true, BRA POSTs the **full** SubjectLinkBody and also sends `X-Solum-Actor` / `X-Solum-Capability`. Otherwise it returns the payload for the operator to apply.

## Env

| Variable | Meaning |
|----------|---------|
| `SOLUM_BASE_URL` | Sidecar base URL (e.g. `http://127.0.0.1:8787`) |
| `SOLUM_SIDECAR_TOKEN` | Bearer / sidecar token |
| `SOLUM_SUBJECT_BRIDGE_UPSERT` | Default `true` when URL set |
| `SOLUM_SUBJECT_PURPOSE` | Default `research` |
| `SOLUM_SUBJECT_CAPABILITY` | Default `solum:cdr:write` (comma-separated) |

## Related

- Operator runbook: Ferrum `docs/solum-subject-bridge-runbook.md`
- Showcase co-custody: Showcase `docs/for-customers/co-custody.md`
