# Architecture Overview

This document explains the system at a level that helps contributors reason about change impact.

## Goals

- Keep behavior predictable and testable.
- Keep security and operational concerns explicit.
- Keep extension points clear for new features.

## High-level structure

- **Web UI + API**: FastAPI backend (`backend/app`), React/TypeScript frontend.
- **BioResearch Assistant core**: literature workflows, pseudonymisation, GA4GH DRS/WES/Phenopackets, MII export, notebooks, FAIR export.
- **Locus (RAG module)**: optional on-premise RAG stack (Ollama-class local inference, curated indexes). **Not** a medical device. See [docs/LOCUS-MODULE.md](docs/LOCUS-MODULE.md).

## Data and control flows

1. The browser talks only to the FastAPI app (`/api/v1/...` and `/ga4gh/...`).
2. `get_current_user` authenticates every mutating and data-read route. Unauthenticated access is allowed only when `DEPLOYMENT` is an explicit `local` / `development` / `test` target.
3. `apply_scope` / `get_scope_filter` (`app/core/isolation.py`) restrict SQLAlchemy queries by `user_id` or `team_id` according to `ISOLATION_MODE`.
4. Persistence is PostgreSQL (pgvector in production; SQLite in unit tests). DRS bytes live on disk under `drs_storage_path` with a sidecar ACL file.
5. WES runs Nextflow or BLAST as subprocesses; remote `http(s)` workflow URLs are opt-in (`WES_ALLOW_REMOTE_WORKFLOWS`).
6. LLM calls go through `get_llm_service()` (Ollama / Anthropic / OpenAI-compatible). Untrusted RAG/notebook context is wrapped before prompting.

## Reliability and security boundaries

- Trust the Bearer token `sub` and derived team id; never trust spoofable `X-User-Id` when `sub` is present.
- Treat workflow URLs, BLAST `program`, and Nextflow param keys as attacker-controlled until allowlisted.
- `/health` is liveness (always 200 if the process is up). `/health/ready` is 503 when the database is down.
- Railway images must not overwrite Presidio/embedding modules; `DEPLOYMENT=railway` selects lightweight stubs at import/factory time.

## Key extension points

- **Locus (curated RAG):** `locus_chunks` in PostgreSQL, `POST/GET` under `/api/v1/locus/*` — add ingestion jobs or admin UIs to load subscription bundles; keep separate from the user `papers` RAG path (`/library/rag`).
- **Library RAG (your papers):** `papers` + `POST /api/v1/library/rag` — unchanged; do not conflate with Locus retrieval.
- **Isolation:** new owned tables should set `user_id`/`team_id` via `get_scope_values` and filter with `apply_scope`.

## Operations after deploy

Run Alembic through **010** on PostgreSQL (`cd backend && alembic upgrade head`). Tests use SQLite `create_all` and do not apply these migrations.

- **009** adds `workflow_runs.user_id`/`team_id` and a composite paper unique constraint.
- **010** (Postgres only) replaces that constraint with partial unique indexes so `pmid` is unique among NULL-owner rows, and adds a GIN index on `patient_records.phenopacket_json`.

Then backfill owners that isolation would otherwise hide:

```
cd backend && python scripts/backfill_tenancy.py --user-id <token-sub> [--team-id <team>] [--dry-run]
```

## Postponed follow-ups

These remain open on purpose. Revisit when the product needs the extra architecture, not as leftover audit bugs.

| Item | Why postponed |
| --- | --- |
| OAuth tokens in httponly cookies only | SPA already stores `access_token` in `localStorage` (`frontend/src/services/auth.ts`). Login now uses HMAC state + PKCE S256. Moving tokens out of JSON would be a frontend breaking change. |
| Prompt-injection denylist expansion | Wrapping untrusted context is the real control. More substrings is still theater. |
| WES/MII as Redis/Celery job queue | Cross-node cancel/retry needs a queue. Same-host WES cancel now kills via PID file; MII retries add jitter. |
| Full Presidio/spaCy on Railway | Slim image is intentional; `DEPLOYMENT=railway` uses the lightweight PII path. |
| Full mypy/pyright | Untyped codebase; multi-day, not a bugfix. |
| Default tests to `ISOLATION_MODE=user` | HTTP tests share one `dev-user`; `conftest` sets `user`. Isolation coverage lives in `test_isolation.py` and `test_hospital_hardening.py`. |
| DRS catalog index (replace `rglob`) | List is now paginated; a DB-backed catalog is larger scope. |
| FAIR `accessible`/`interoperable` hardcoded True | Scoring heuristic, not a security bug. ZIP build now uses a spooled temp file. |
| `poetry.lock` regeneration | `package = []` is a stub. `uv.lock` and `requirements.txt` are the install source of truth. |
