# MII Export & Consent (Operational Guide)

## Scope

This document describes the implemented MII-oriented export and consent capabilities in BioResearch Assistant:

- pseudonymized FHIR `Bundle` export for selected modules
- consent-gated export behavior
- asynchronous export jobs with retries/dead-letter
- terminology mapping overrides for governed corrections

This guide documents technical behavior. It is not a legal opinion and not a formal certification statement.

## Endpoints

Base prefix: `/api/v1`

- `POST /mii-export/bundles`  
  Synchronous bundle generation.
- `POST /mii-export/jobs`  
  Asynchronous export job creation (`202 Accepted`).
- `GET /mii-export/jobs/{job_id}`  
  Job status (`queued`, `running`, `succeeded`, `failed`, `dead_letter`).
- `GET /mii-export/jobs/{job_id}/artifact`  
  Download generated FHIR bundle artifact.
- `GET /mii-export/jobs/{job_id}/validation-report`  
  Persisted validation report.
- `GET /mii-export/jobs/metrics`  
  Per-user status counts for export jobs.
- `POST /consents` / `GET /consents` / `POST /consents/{id}/withdraw`  
  Research consent management.
- `POST /terminology/overrides`, `GET /terminology/overrides`, `DELETE /terminology/overrides/{override_id}`  
  Managed terminology mapping overrides.

## Export behavior

### Consent gate

Exports require an active consent matching the policy and requested project constraints.  
If consent checks fail, export is rejected with a consent summary.

### Module mapping

Current module targets:

- diagnosis -> `Condition`
- laboratory -> `Observation`
- biospecimen -> `Specimen`
- genomics -> `Observation`
- person (always) -> `Patient`

Mappings are MII-oriented and include profile metadata in strict mode (or when configured).

### Strict profile/terminology checks

In strict mode the in-process validator checks:

- expected profile canonical in `meta.profile`
- selected binding-level coding systems for diagnosis/lab/phenotype/genomics

External validator-cli/IG checks remain the stronger conformance gate in CI/operations.

## Async jobs

`POST /mii-export/jobs` creates queued jobs.

Worker behavior:

- transient runtime failures -> retry with exponential backoff
- `ValueError` mapping/validation failures -> permanent `failed`
- retry limit exceeded -> `dead_letter`

Job metadata stores attempts, validator package metadata, and validation summary.

## Terminology overrides

Overrides enable controlled remapping of raw source IDs to target coding systems/codes:

- keyed by `(module, raw_id)`
- activate/deactivate via API
- applied at export time before default fallback mapping

Use this to implement local terminology governance while preserving reproducibility.

## Configuration

Important variables:

- `MII_KDS_RELEASE`
- `MII_IG_PACKAGE_ID`
- `MII_IG_PACKAGE_VERSION`
- `MII_DEFAULT_CONSENT_POLICY_ID`
- `MII_BUNDLE_ATTACH_META_PROFILE`
- `MII_EXPORT_MAX_ATTEMPTS`
- `MII_EXPORT_RETRY_BASE_SECONDS`

## Known limits

- Mappings are still documented as partial in selected areas.
- This implementation does not by itself establish formal legal/regulatory conformity.
- Institutional onboarding may require additional local validation, governance, and release approval steps.
