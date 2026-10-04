# CI triggers

Push to `main` and pull requests run only the secret scan and dependency review. Product CI is manual. A `v*.*.*` tag runs the Release workflow, which publishes the two GHCR images and the small Release files. The offline bundle and the models bundle are built only on `workflow_dispatch`. `build-images.yml` and the deploy workflows stay on `workflow_dispatch`.

Run `make verify-release` before tagging. That command is the pre-commit mirror (ruff, pytest with the coverage floor, frontend typecheck and build), frontend unit tests, `pip-audit` when it is installed, and `npm audit` at high severity for production dependencies.

Minutes below are rough runner time, not a measured bill.

| Workflow | Trigger | Rough minutes | When to run manually |
|---|---|---|---|
| `ci.yml` | `workflow_dispatch` | 10–20 | Before a tag, after `make verify-release`, when you want the same jobs on a GitHub runner. |
| `conformance.yml` | `workflow_dispatch` | 15–40 | FHIR bundle validation and the GA4GH conformance job. Not on the tag. |
| `codeql.yml` | `workflow_dispatch` | 10–20 | Before a release when you want a CodeQL pass. |
| `build-images.yml` | `workflow_dispatch` | 15–30 | Publish GHCR images. The form asks you to type DEPLOY. |
| `release.yml` | tag `v*.*.*`; `workflow_dispatch` | 15–25 on a tag | The tag pushes `ghcr.io/synapticfour/bioresearch-assistant-backend` and `bioresearch-assistant-frontend` (tag and commit SHA) and attaches `install.sh`, `import.sh`, and `SHA256SUMS.txt`. Dispatch builds `bra-offline-*.tar.gz` and, with `include_models_bundle`, the models archive. Those archives are not Release assets. See [RELEASING.md](RELEASING.md). |
| `deploy-all.yml`, `deploy-otc.yml`, `deploy-dfn.yml`, `deploy-azure.yml`, `deploy-railway.yml`, `deploy-vercel.yml` | `workflow_dispatch` | 10–20 each | Only when you intend to deploy that target. |
| `secret-scan.yml` | pull request; push to `main` or `master` | 1–2 | Leave it. It stays on those events. |
| `dependency-review.yml` | pull request | 1–2 | Leave it. It stays on pull requests. |
