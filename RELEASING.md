# Releasing

This repository follows Semantic Versioning (`MAJOR.MINOR.PATCH`).

## Release process

1. Ensure CI is green on `main`.
2. Update `CHANGELOG.md` with user-visible changes.
3. Create an annotated tag:
   - `git tag -a vX.Y.Z -m "vX.Y.Z"`
4. Push the tag:
   - `git push origin vX.Y.Z`
5. Verify GitHub Release artifacts:
   - `bra-offline-vX.Y.Z.tar.gz` (app images, no LLM weights)
   - `SHA256SUMS.txt`
   - `install.sh`, `import.sh`
6. Optional air-gap LLM bundle (large, slow):
   - Re-run workflow **Release** via `workflow_dispatch` with **include_models_bundle**, or locally:
     `BRA_VERSION=vX.Y.Z ./scripts/export_models_bundle.sh`
   - Upload `models-bundle-vX.Y.Z.tar.gz` to the release if built offline.

## Versioning rules

- `MAJOR`: breaking API/behavior changes
- `MINOR`: backward-compatible features
- `PATCH`: backward-compatible fixes and maintenance

Customers must set **`BRA_VERSION`** in `.env` — `./install.sh --prod` refuses to start without it.

## Backport policy

Security fixes should be backported to actively maintained release lines where feasible.
