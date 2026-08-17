# BioResearch Assistant

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL%201.1-blue.svg)](LICENSE)
[![GAIA-X](https://img.shields.io/badge/GAIA--X-not%20certified-lightgrey.svg)](docs/GAIA-X-ALIGNMENT.md)
[![Datenschutz](https://img.shields.io/badge/DSGVO-technical%20controls%20only-lightgrey.svg)](docs/COMPLIANCE.md)

On-premises researcher workbench: literature, phenopackets, notebooks, and local GA4GH DRS/WES. Optional: proxy DRS/WES to Ferrum when `FERRUM_DRS_URL` / `FERRUM_WES_URL` are set.

**Maturity: Early access.** Supported line is 0.2.x. Gaia-X and DSGVO badges are **not** certifications. HelixTest CI is a technical signal, not GA4GH certification.

> This README describes technical capabilities, not legal advice. See [docs/COMPLIANCE.md](docs/COMPLIANCE.md) and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## Ferrum / GA4GH suite

These ten public repositories are from the same organisation and can be composed. They are not a fifth product and not a bundle SKU. Each repository keeps its own version and license. Roles, maturity, and who consumes whom: [SUITE-OVERVIEW](https://github.com/SynapticFour/Ferrum/blob/main/docs/SUITE-OVERVIEW.md).

## Quick start

```bash
pip install -r backend/requirements.txt
make prove    # backend pytest, no Docker
make up       # unattended install or start
```

Requires Docker, Python 3.11+ (3.12 recommended), about 8 GB RAM. After `make up`: frontend `http://localhost:3000`, API `http://localhost:8000`. Stop: `make down`. Remove volumes: `make destroy`.

DRS and WES in the feature list are **BRA’s own local surfaces**, or Ferrum when those URLs are set — not a claim that BRA is Ferrum.

## Documentation

- [Getting started](docs/GETTING-STARTED.md)
- [Architecture](docs/ARCHITECTURE.md)
- [For evaluators](docs/FOR-EVALUATORS.md)
- [User guide](docs/USER-GUIDE.md) · [Developer / API](docs/DEVELOPER-GUIDE.md) · [Install](docs/INSTALL.md)

## License

Business Source License 1.1 — see [LICENSE](LICENSE). Change Date is four years from each version, not a calendar date.
