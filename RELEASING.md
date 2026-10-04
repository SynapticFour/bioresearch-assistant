# Releasing

This repository follows Semantic Versioning (`MAJOR.MINOR.PATCH`).

## Release process

1. Run `make verify-release` on the commit you will tag (ruff, pytest with the coverage floor, frontend typecheck, build, and unit tests, plus pip-audit and npm audit when those tools are installed). Product CI does not run on push to `main` or on pull requests. Dispatch conformance or CodeQL from [docs/CI.md](docs/CI.md) when you want those jobs on a runner.
2. Update `CHANGELOG.md` with user-visible changes.
3. Create an annotated tag:
   - `git tag -a vX.Y.Z -m "vX.Y.Z"`
4. Push the tag:
   - `git push origin vX.Y.Z`
5. Verify the GitHub Release from that tag:
   - `ghcr.io/synapticfour/bioresearch-assistant-backend:vX.Y.Z` and `ghcr.io/synapticfour/bioresearch-assistant-frontend:vX.Y.Z` (also tagged with the commit SHA)
   - `install.sh`, `import.sh`, `SHA256SUMS.txt`
6. The offline bundle and the models bundle are not Release assets. A tag does not build them. Distribution: [docs/RELEASING.md](docs/RELEASING.md).

## Versioning rules

- `MAJOR`: breaking API/behavior changes
- `MINOR`: backward-compatible features
- `PATCH`: backward-compatible fixes and maintenance

Customers must set **`BRA_VERSION`** in `.env` — `./install.sh --prod` refuses to start without it.

## Release train (portfolio)

When **Ferrum** or **Solum** is tagged: bump [VERSIONS.lock](VERSIONS.lock) and `config/ci/solum-revision.txt` the same week. Showcase pins **tags that exist on origin/main**. See [Ferrum PORTFOLIO.md](https://github.com/SynapticFour/Ferrum/blob/main/docs/PORTFOLIO.md).

## Backport policy

Security fixes should be backported to actively maintained release lines where feasible.
