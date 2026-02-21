# Helm Chart — BioResearch Assistant (AKS)

Helm-Chart für Azure Kubernetes Service (Option B) in Vorbereitung.

Geplante Komponenten:

- **backend** — Deployment + Service (FastAPI)
- **frontend** — Deployment + Service (nginx)
- **ollama** — Deployment + Service (optional GPU Node Pool)
- **postgres** — Bitnami PostgreSQL Chart mit pgvector Extension

Siehe [docs/deployment/AZURE.md](../../../docs/deployment/AZURE.md) für die manuelle ACI-Option.
