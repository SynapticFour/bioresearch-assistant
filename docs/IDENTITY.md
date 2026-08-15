# Who BioResearch Assistant is for

BioResearch Assistant (BRA) is a **researcher workbench**: Phenopackets, literature, BLAST, notebooks, its **own** GA4GH WES/DRS HTTP surface.

It is a complete product without Ferrum. It does not import Ferrum crates and is not a thin wrapper around the suite.

## Audience

Clinician-scientists, lab groups, Uniklinik research units who want one on-prem UI for phenotype + literature + jobs.

**Not for:** being the institutional GA4GH archive (that is Ferrum), being the hospital consent engine (that is Solum), issuing Passports (that is ga4gh-infra).

## Standalone

See the root [README](../README.md) install path (`docker compose` / backend + frontend). Proof: backend pytest coverage gate in CI.

## Optional composition

| Join | What you gain | Contract |
|------|----------------|----------|
| Solum | Phenopacket id bound to a clinical subject | `docs/SOLUM-SUBJECT-BRIDGE.md` — full `SubjectLinkBody` |
| Ferrum | Shared `solum_subject` on DRS objects | Convention only; no Ferrum import |
| HELIOS | Signed evidence of a pipeline BRA kicked off | Operator exports artefacts; BRA does not embed HELIOS |

When Solum Track B (CDR) is off, subject-link upsert returns 503 from Solum. BRA surfaces that as a failed upsert and still returns the payload.
