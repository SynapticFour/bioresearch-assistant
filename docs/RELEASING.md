# Offline bundle distribution

GitHub rejects a Release asset at or above 2 GiB. `bra-offline-v0.2.2.tar.gz` crossed that limit, so a `v*.*.*` tag does not build `bra-offline-*.tar.gz` or `models-bundle-*.tar.gz` and does not attach them. The tag publishes the two GHCR images plus `install.sh`, `import.sh`, and `SHA256SUMS.txt`. The process is in [RELEASING.md](../RELEASING.md).

Build the archives from **Actions → Release → Run workflow**:

- Every dispatch builds `bra-offline-vX.Y.Z.tar.gz` (app images, no LLM weights) via `scripts/package_release_bundle.sh`.
- Set **include_models_bundle** to also build `models-bundle-vX.Y.Z.tar.gz`. Locally: `BRA_VERSION=vX.Y.Z ./scripts/export_models_bundle.sh`.

`SHA256SUMS.txt` on a tag covers `install.sh` and `import.sh`. A dispatch appends the archives that run produced. Those archives stay on the runner. Copy them, with that checksum file, to one of these:

- **OCI artifact on GHCR.** Push the tarball as an artifact, for example `ghcr.io/synapticfour/bioresearch-assistant-offline:vX.Y.Z`, with `oras push` (or an equivalent OCI layout). The object is pulled like an image. It is not a GitHub Release asset, so the 2 GiB Release limit does not apply. Publish the matching `SHA256SUMS.txt` next to it or in the artifact annotations.
- **A download host you operate.** Object storage or an institute file service. Put the tarball and `SHA256SUMS.txt` at a URL you document for that version. Do not attach the tarball to the GitHub Release.
