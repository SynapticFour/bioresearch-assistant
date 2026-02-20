# BioResearch Assistant

On-premise KI-System für Literature Mining, Bioinformatik-Pipelines und DSGVO-konforme Pseudonymisierung (Synaptic Four).

## Monorepo-Struktur

```
backend/          # FastAPI, SQLAlchemy 2.0 async, pgvector, Alembic
frontend/         # React TypeScript (Ordnerstruktur)
ga4gh/            # GA4GH API Implementierungen (DRS, WES, …)
pipelines/        # Nextflow Workflows
```

## Quick Start

1. **Umgebung:** `.env` aus `.env.example` anlegen (mindestens `DATABASE_URL` setzen).

2. **PostgreSQL + pgvector mit Docker:**
   ```bash
   docker compose up -d db
   ```

3. **Backend lokal:**
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate  # bzw. .venv\Scripts\activate unter Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
   API: http://localhost:8000 — Docs: http://localhost:8000/docs

4. **Oder alles mit Docker:**
   ```bash
   cp .env.example .env
   docker compose up --build
   ```

5. **Migrationen (von `backend/` aus):**
   ```bash
   cd backend
   alembic revision --autogenerate -m "init"
   alembic upgrade head
   ```

## Tech Stack (Backend)

- FastAPI, Pydantic v2, pydantic-settings  
- SQLAlchemy 2.0 (async), asyncpg, pgvector  
- Alembic für Migrationen  

Siehe auch `.cursorrules` für Konventionen und weitere Stack-Details.
