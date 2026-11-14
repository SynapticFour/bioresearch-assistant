# Versioning

Published tags:

| Tag | Meaning |
|-----|---------|
| **v1.0.0** (2026-03-01) | **Mistake.** Initial import was tagged 1.0.0. It is **not** a production 1.0. Do not deploy or cite it as GA. |
| **v0.2.0** (2026-08-15) | Pre-1.0 product tag. Does **not** include the optional Ferrum DRS/WES HTTP proxy (that landed on `main` after the tag). |
| **v0.2.1** | Cut after the Ferrum proxy + visa-verify + suite HelixTest pin (suite 2026.08-draft). Use this for Ferrum join demos. |
| **v0.2.2** | Service-registry lookup for DRS and WES, Ollama only under the Compose profile, and the local `make verify-release` gate. |

Versions released before this change were published under the Business Source License 1.1. From this commit on, the code is published under Apache-2.0. See [LICENSING-HISTORY.md](../LICENSING-HISTORY.md). The old calendar date `2030-03-01` was a mistaken tag. It is not a change date for this tree.

Current app version is **0.2.2** in `backend/pyproject.toml` and `frontend/package.json`.

Tag `v0.2.2` points at `003fbb1f4939df36e29dec3d837f04d5c716be6b`. The default branch this documentation was cut from is `491879effd3b1cd167bc3cc2498ec8590d9ec0a3`, the next commit. That commit is not the tag. The version fields stay 0.2.2.
