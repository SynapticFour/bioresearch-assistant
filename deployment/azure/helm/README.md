# Helm Chart — BioResearch Assistant (AKS / K8s)

Dieses Verzeichnis enthaelt ein lauffaehiges Basis-Helm-Chart fuer:

- **backend** (FastAPI)
- **frontend** (nginx)
- **ollama** (optional)
- **postgres** (pgvector Image)
- optional **Ingress**

## Schnellstart

```bash
cd deployment/azure/helm
helm install bioresearch . -n bioresearch --create-namespace
```

Upgrade:

```bash
helm upgrade bioresearch . -n bioresearch
```

## Wichtige Values

- `backend.secretEnv.*` fuer Secrets
- `backend.existingSecret` falls Secret extern verwaltet wird
- `ollama.enabled` und `ollama.models.pullOnStart`
- `postgres.enabled` (bei externem DB-Service auf `false`)
- `ingress.enabled`

## Beispiel: Institut mit A100

```bash
helm upgrade --install bioresearch . -n bioresearch \
  --set ollama.enabled=true \
  --set ollama.models.pullOnStart=true \
  --set ollama.models.list[0]=gpt-oss:120b \
  --set ollama.persistence.size=300Gi
```

Hinweis: Fuer GPU Scheduling werden in der Regel zusaetzlich Node-Selector,
Tolerations und GPU-Ressourcenlimits benoetigt (cluster-spezifisch).

Siehe auch `docs/deployment/AZURE.md` und `docs/deployment/README.md`.
