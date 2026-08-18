# Getting started

**Prerequisites:** Docker Desktop, Python 3.11+ (3.12 recommended), about 8 GB RAM (16 GB recommended), about 10 GB free disk. Full variants: [INSTALL.md](INSTALL.md).

## Zero-risk proof (no Docker)

```bash
pip install --require-hashes --no-deps --extra-index-url https://download.pytorch.org/whl/cpu -r backend/requirements.lock
make prove
```

Coverage gate stays in CI (`pytest --cov-fail-under=72`), not in `make prove`.

## Compose stack

```bash
make up
```

Interactive first-time setup: `make install` or `python install.py`. After start:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

Local Vite frontend is typically `http://localhost:5173`.

Stop and keep data: `make down`. Remove volumes: `make destroy`.

## Optional Ferrum / Solum

Leave `FERRUM_DRS_URL` / `FERRUM_WES_URL` unset to use BRA’s **own** local DRS/WES. Set them (including `/ga4gh/drs/v1` and `/ga4gh/wes/v1` prefixes) to proxy those HTTP surfaces to Ferrum. See [IDENTITY.md](IDENTITY.md).

Solum subject-link: [SOLUM-SUBJECT-BRIDGE.md](SOLUM-SUBJECT-BRIDGE.md).

Next: [ARCHITECTURE.md](ARCHITECTURE.md) · [FOR-EVALUATORS.md](FOR-EVALUATORS.md).
