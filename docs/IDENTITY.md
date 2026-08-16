# Who BioResearch Assistant is for

BioResearch Assistant (BRA) is a **researcher workbench**: Phenopackets, literature, BLAST, notebooks. It is a complete product **without Ferrum**. For labs that have no archive, it exposes its **own** GA4GH WES/DRS HTTP surface.

When Ferrum is present, BRA **consumes** Ferrum DRS/WES as a GA4GH client. Set `FERRUM_DRS_URL` and/or `FERRUM_WES_URL` (include the `/ga4gh/drs/v1` and `/ga4gh/wes/v1` prefixes). BRA then proxies those HTTP surfaces to Ferrum and `/api/v1/health` reports `ga4gh_backend.drs|wes: ferrum`. Leave the URLs unset for BRA's **own** local DRS/WES.

**One institute, one DRS.** With Ferrum URLs set, `GET /ga4gh/drs/v1/service-info` (and WES service-info) is Ferrum's document — not `org.ga4gh.bioresearch.*`. BRA is the workbench client. Do not run BRA’s local DRS as a second institutional archive beside Ferrum.

## Audience

Clinician-scientists, lab groups, Uniklinik research units who want one on-prem UI for phenotype + literature + jobs.

**Not for:** being the institutional GA4GH archive (that is Ferrum), being the hospital consent engine (that is Solum), issuing Passports (that is ga4gh-infra).

## Standalone

```bash
git clone https://github.com/SynapticFour/bioresearch-assistant.git && cd bioresearch-assistant
pip install -r backend/requirements.txt
make prove       # backend pytest, no Docker (coverage gate is CI)
make up          # compose stack
```

See the root [README](../README.md) for the installer. CI keeps the 72 % coverage gate.

## Optional composition

| Join | What you gain | Contract |
|------|----------------|----------|
| Ferrum | Use Ferrum as the institutional DRS/WES | `FERRUM_DRS_URL` / `FERRUM_WES_URL` (optional `FERRUM_BEARER_TOKEN`). Contract is the **published GA4GH DRS/WES OpenAPI**. Ferrum’s [utoipa dump](https://github.com/SynapticFour/Ferrum/blob/main/docs/openapi/ferrum.openapi.json) is only for Ferrum-only paths. Lab Kit profile `bra-companion` only sets those URLs (bring `BRA_IMAGE`). Health: `ga4gh_backend`. `solum_subject` convention still joins Phenopackets to Ferrum objects |
| ga4gh-infra | Same Passport *and nested visa JWTs* the broker issued | Point `OIDC_ISSUER` at the broker. BRA verifies the ID token (JWKS) **and** each `ga4gh_passport_v1` visa JWT (broker JWKS, then visa `iss` discovery — same split Ferrum uses). BRA does **not** issue Passports. When Ferrum URLs are set, `Authorization` is forwarded unless `FERRUM_BEARER_TOKEN` overrides it; Ferrum still enforces bytes on DRS/WES. |
| Solum | Phenopacket id bound to a clinical subject | `docs/SOLUM-SUBJECT-BRIDGE.md` — full `SubjectLinkBody`. Pin: `config/ci/solum-revision.txt` |
| HELIOS | Signed evidence of a pipeline BRA kicked off | Operator exports artefacts; BRA does not embed HELIOS |

When Solum Track B (CDR) is off, subject-link upsert returns 503 from Solum. BRA surfaces that as a failed upsert and still returns the payload.
