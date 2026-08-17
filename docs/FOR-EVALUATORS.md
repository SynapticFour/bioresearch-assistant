# For evaluators

Factual snapshot of this repository. Not a sales brief. Not legal advice.

## Maturity

**Early access.** Supported line is **0.2.x**. Gaia-X self-description and DSGVO-related badges in the README are grey on purpose: **not certified**. HelixTest CI is a technical signal against published OpenAPI, not GA4GH certification.

BRA is a workbench. It is not the institutional GA4GH archive (Ferrum), not the hospital consent engine (Solum), and does not issue Passports (ga4gh-infra).

## License

Business Source License 1.1. Change Date is four years from each version (the old calendar date `2030-03-01` was a mistaken tag). See [LICENSE](../LICENSE) and [VERSIONING.md](VERSIONING.md). No combo SKU with Ferrum or Solum.

## Tested in this tree

| Claim | Evidence |
|-------|----------|
| Backend tests | `make prove` (no Docker). Coverage gate is CI (`--cov-fail-under=72`). |
| Local DRS/WES | BRA’s own `/ga4gh/` surfaces when Ferrum URLs are unset |
| Optional Ferrum proxy | `FERRUM_DRS_URL` / `FERRUM_WES_URL` — health reports `ga4gh_backend` |
| SBOM | Human-readable [SBOM.md](SBOM.md); machine-readable SBOMs are generated from lockfiles at release |

## Not tested / not claimed

| Topic | Status |
|-------|--------|
| Gaia-X labelling | API reports `gaia_x_ready: false`. Not certified. |
| GDPR / DSGVO / HIPAA as a certificate | Technical controls only. Not a legal determination. |
| MII-KDS | Export is MII-KDS-oriented; not a site conformance check. Some mappings are `partial`. |
| Formal AVV template | Not shipped in this tree. |
| Third-party audit | None published. |

## Contact

Questions can be sent to [contact@synapticfour.com](mailto:contact@synapticfour.com).
