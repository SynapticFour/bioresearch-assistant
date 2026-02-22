# Deployment auf Microsoft Azure

**Datensouveränität:** Siehe [README Datensouveränität](../../README.md#datensouveränität) — für Klinikbetrieb Ollama empfohlen.

**Isolation:** `ISOLATION_MODE=user` (pro Person) oder `ISOLATION_MODE=team` (Teams z. B. über Azure AD organization claim). Siehe [ISOLATION-MODES.md](../ISOLATION-MODES.md).

## Warum Azure?

Viele deutsche Unikliniken haben bereits Azure Enterprise Agreements — einfacherer Einstieg für diese Kunden.

## Empfohlene Architektur

| Option | Einsatz | Beschreibung |
|--------|---------|--------------|
| **Option A: Azure Container Instances (ACI)** | Einfach, Einstieg | Einfaches Deployment ohne Kubernetes |
| **Option B: Azure Kubernetes Service (AKS)** | Produktion, Skalierung | Für größere Installationen, GPU-Node-Pools für Ollama |
| Azure Database for PostgreSQL | Beide | Managed PostgreSQL mit pgvector |
| Azure Container Registry (ACR) | Beide | Docker-Images hosten |

---

## Option A: Azure Container Instances (empfohlen zum Start)

### 1. Azure CLI installieren

```bash
brew install azure-cli
az login
```

### 2. Resource Group + Container Registry

```bash
az group create --name bioresearch-rg --location germanywestcentral
az acr create --name bioresearchregistry \
  --resource-group bioresearch-rg --sku Basic
```

### 3. Images pushen

Images werden automatisch bei Push auf `main` nach GHCR gebaut. Für ACR manuell:

```bash
az acr login --name bioresearchregistry
docker tag ghcr.io/synapticfour/bioresearch-assistant/backend:latest bioresearchregistry.azurecr.io/backend:latest
docker push bioresearchregistry.azurecr.io/backend:latest
```

### 4. PostgreSQL mit pgvector

```bash
az postgres flexible-server create \
  --name bioresearch-db \
  --resource-group bioresearch-rg \
  --location germanywestcentral \
  --admin-user bioresearch \
  --admin-password "${DB_PASSWORD}" \
  --sku-name Standard_D2s_v3

# pgvector Extension aktivieren
az postgres flexible-server parameter set \
  --server-name bioresearch-db \
  --resource-group bioresearch-rg \
  --name azure.extensions \
  --value vector
```

### 5. Container starten

```bash
az container create \
  --resource-group bioresearch-rg \
  --name bioresearch-backend \
  --image bioresearchregistry.azurecr.io/backend:latest \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL="${DATABASE_URL}" \
    PSEUDONYMIZATION_ENCRYPTION_KEY="${PSEUDONYMIZATION_ENCRYPTION_KEY}" \
    ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
    SECRET_KEY="${SECRET_KEY}" \
    ENVIRONMENT=production
```

---

## Option B: Azure Kubernetes Service (Produktion)

- Backend-, Frontend- und Ollama-Deployments mit Services
- PostgreSQL z. B. über Bitnami Helm Chart mit pgvector
- Optional: GPU-Node-Pool für Ollama

Siehe `deployment/azure/helm/` (Helm-Chart in Vorbereitung).

---

## Kosten (ca.)

| Ressource | Kosten |
|-----------|--------|
| ACI Backend | ~50 €/Monat |
| PostgreSQL Flexible | ~80 €/Monat |
| Container Registry | ~5 €/Monat |
| **Gesamt** | **~135 €/Monat** |

---

## GitHub Actions

Siehe [Deploy to Azure](../../.github/workflows/deploy-azure.yml).

**Secrets:**

- `AZURE_CREDENTIALS` — Service Principal JSON (`az ad sp create-for-rbac --sdk-auth`)
- `ACR_USERNAME` — Azure Container Registry Benutzername
- `ACR_PASSWORD` — Azure Container Registry Passwort
