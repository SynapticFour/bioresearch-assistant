# Versioning

Published tags:

| Tag | Meaning |
|-----|---------|
| **v1.0.0** (2026-03-01) | **Mistake.** Initial import was tagged 1.0.0. It is **not** a production 1.0. Do not deploy or cite it as GA. |
| **v0.2.0** (2026-08-15) | Pre-1.0 product tag. Does **not** include the optional Ferrum DRS/WES HTTP proxy (that landed on `main` after the tag). |
| **v0.2.1** | Cut after the Ferrum proxy + visa-verify + suite HelixTest pin (suite 2026.08-draft). Use this for Ferrum join demos. |
| **v0.2.2** | Service-registry lookup for DRS and WES, Ollama only under the Compose profile, and the local `make verify-release` gate. |

BUSL Change Date is **four years from each version** (same pattern as Ferrum), not `2030-03-01`.

Current app version is **0.2.2** in `backend/pyproject.toml` and `frontend/package.json`.
