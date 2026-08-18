# Software Bill of Materials (SBOM)

**Stand:** 2026-08-15 · Version: 1.0.2
**Org level-up:** C8 refresh

This document is a **human-readable summary**. For machine-readable SBOMs, generate from lockfiles at release time (CycloneDX via `cyclonedx-bom` / `npm sbom` when cutting a tag).

## Backend Dependencies (Python)

Source of truth: `backend/requirements.txt` plus hashed `backend/requirements.lock` (`uv pip compile --generate-hashes`).

| Package | Version constraint | Lizenz | Verwendung |
|---------|-------------------|--------|------------|
| fastapi | ≥0.100 | MIT | Web Framework |
| sqlalchemy | ≥2.0 | MIT | ORM |
| asyncpg | ≥0.28 | Apache 2.0 | PostgreSQL Treiber |
| pgvector | ≥0.2 | MIT | Vektor-Extension |
| presidio-analyzer | ≥2.2 | MIT | NLP Pseudonymisierung |
| presidio-anonymizer | ≥2.2 | MIT | Text Anonymisierung |
| spacy | ≥3.7 | MIT | NLP (optional) |
| sentence-transformers | ≥2.2 | Apache 2.0 | Embeddings (optional) |
| paraphrase-multilingual-mpnet-base-v2 | (Modell) | Apache 2.0 | Multilingual Embeddings DE+EN |
| anthropic | ≥0.20 | MIT | LLM API (optional) |
| PyJWT | ≥2.10 | MIT | JWT (OIDC) |
| authlib | ≥1.3 | BSD | OAuth2/OIDC |
| httpx | ≥0.25 | BSD | HTTP Client |
| slowapi | ≥0.1 | MIT | Rate Limiting |
| alembic | ≥1.12 | MIT | DB Migrationen |
| pydantic | ≥2.0 | MIT | Validierung |
| uvicorn | ≥0.24 | BSD | ASGI Server |
| aiosqlite | ≥0.19 | MIT | SQLite async (Tests) |
| pytest-asyncio | ≥0.21 | Apache 2.0 | Async Tests |

## Frontend Dependencies (JavaScript)

Source of truth: `frontend/package-lock.json`.

| Package | Version | Lizenz | Verwendung |
|---------|---------|--------|------------|
| react | ^18 | MIT | UI Framework |
| typescript | ^5 | Apache 2.0 | Typisierung |
| vite | ^5 | MIT | Build Tool |
| tailwindcss | ^3 | MIT | Styling |
| lucide-react | ^0.3 | ISC | Icons |
| react-router-dom | ^6 | MIT | Routing |

## Externe Services (optional)

| Service | Zweck | Daten | DSGVO |
|---------|-------|-------|-------|
| PubMed/NCBI | Literatursuche | Suchanfragen | USA |
| CrossRef | DOI Lookup | DOI Strings | USA |
| HPO API (JAX) | Phänotyp-Suche | Suchbegriffe | USA |
| Anthropic API | LLM (optional) | Texte | USA |
| Ollama (lokal) | LLM (empfohlen) | Keine | Lokal |

## Automated checks (CI)

On every push/PR:

```bash
# backend
pip install pip-audit
pip-audit -r backend/requirements.lock

# frontend (production, high+)
cd frontend && npm ci && npm audit --omit=dev --audit-level=high
```

See `.github/workflows/ci.yml` job `supply-chain`.

## Known vulnerabilities

Dated 2026-08-15 (`pip-audit -r backend/requirements.lock`, `npm audit --omit=dev --audit-level=high`):

| Finding | Status |
|---------|--------|
| cryptography PKCS#7 oracle (fixed in 50.0.0) | **Patched** — `cryptography>=50`; Presidio anonymizer pinned at 2.2.362 so the 2.2.364 `<49` cap does not block the fix. |
| python-ecdsa Minerva (no planned fix) | **Removed** — JWT via PyJWT + cryptography. |
| pytest <9.0.3 | **Patched** — `pytest>=9.0.3` with `pytest-asyncio>=1.3`. |
| transformers 4.57.x (`PYSEC-2025-217`, `PYSEC-2026-2288/2289/2290`) | **Residual** — `sentence-transformers` 2.x cannot take transformers 5. CI ignores these IDs. The app loads a pinned public embedding model, not untrusted checkpoints. Revisit when upgrading sentence-transformers. |
| react-router-dom 6 moderate CVEs | **Residual** — v7 is a breaking upgrade, not taken. CI fails on production `high+` only. |

Dependabot is **disabled** (file removed) so unreviewed majors are not auto-opened. Operators patch from CI supply-chain and the infra monthly hygiene log.
