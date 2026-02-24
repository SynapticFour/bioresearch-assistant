# Software Bill of Materials (SBOM)
Stand: 2026-02-24, Version: 1.4.0

## Backend Dependencies (Python)

| Package | Version | Lizenz | Verwendung |
|---------|---------|--------|------------|
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
| python-jose | ≥3.3 | MIT | JWT |
| authlib | ≥1.3 | BSD | OAuth2/OIDC |
| httpx | ≥0.25 | BSD | HTTP Client |
| slowapi | ≥0.1 | MIT | Rate Limiting |
| alembic | ≥1.12 | MIT | DB Migrationen |
| pydantic | ≥2.0 | MIT | Validierung |
| uvicorn | ≥0.24 | BSD | ASGI Server |
| aiosqlite | ≥0.19 | MIT | SQLite async (Tests) |
| pytest-asyncio | ≥0.21 | Apache 2.0 | Async Tests |

## Frontend Dependencies (JavaScript)

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

## Bekannte Schwachstellen

Regelmäßig geprüft via:
```bash
cd backend && pip-audit
cd frontend && npm audit
```

Stand: 2026-02-24 — Keine bekannten kritischen CVEs.
