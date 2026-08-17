# Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│   React     │────▶│    FastAPI      │────▶│ PostgreSQL   │
│ TypeScript  │     │   Python 3.11   │     │ + pgvector   │
│ Tailwind    │     │   SQLAlchemy    │     │ (768-dim)    │
└─────────────┘     └────────┬────────┘     └──────────────┘
                             │
                    ┌────────▼────────┐
                    │   Ollama (local)│
                    │   Presidio NLP  │
                    └─────────────────┘
```

BRA is a workbench: UI + FastAPI backend. It exposes local GA4GH DRS/WES under `/ga4gh/` unless `FERRUM_DRS_URL` / `FERRUM_WES_URL` are set, in which case those surfaces are proxied to Ferrum ([IDENTITY.md](IDENTITY.md)).

Local LLM is optional (Ollama). External LLM APIs send content to that provider. Locus (on-prem RAG): [LOCUS-MODULE.md](LOCUS-MODULE.md). Deployment matrix: [deployment/README.md](deployment/README.md).
