# Deployment auf Open Telekom Cloud

> Gesamtuebersicht aller Deployment-Wege: `docs/deployment/README.md`

**Datensouveränität:** Siehe [README Datensouveränität](../../README.md#datensouveränität) — Konfiguration Ollama vs. Anthropic API.

**Isolation:** `ISOLATION_MODE=team` oder `user` je nach Einsatz. Siehe [ISOLATION-MODES.md](../ISOLATION-MODES.md).

## Warum Open Telekom Cloud?

- GAIA-X Mitglied und konform
- BSI C5 zertifiziert
- Deutsches Rechenzentrum (Frankfurt)
- Stark bei deutschen Behörden und Kliniken

## Empfohlene Architektur

| Komponente | Typ | Beschreibung |
|------------|-----|--------------|
| ECS (Elastic Cloud Server) | s3.xlarge.4 | 4 vCPU, 16 GB RAM |
| EVS (Elastic Volume Service) | 100 GB SSD | System- und Datenträger |
| EIP (Elastic IP) | — | Externer Zugriff |
| VPC | — | Isoliertes Netzwerk |

## Schritt-für-Schritt

### 1. OTC CLI installieren

```bash
pip install otcextensions
otc configure  # Access Key + Secret Key eingeben
```

### 2. Infrastruktur mit OpenTofu (Terraform)

Siehe [deployment/otc/](../../deployment/otc/) im Repository:

```bash
cd deployment/otc
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars anpassen (Netzwerk, Security Group, Repo-Ref, Images)
tofu init
tofu plan
tofu apply
```

Nutzbare Artefakte:
- `variables.tf` (parametrisierte Inputs)
- `outputs.tf` (Instance-ID, Name, Floating-IP)
- `terraform.tfvars.example` (Startpunkt fuer Umgebungen)
- `cloud-init.sh.tftpl` (parametrisierbarer Bootstrap)

Output anzeigen:

```bash
tofu output
```

### 3. Cloud-Init

Die Instanz wird per `cloud-init.sh` mit Docker und dem BioResearch Assistant vorbereitet. Repository-URL und Umgebungsvariablen ggf. in `cloud-init.sh` anpassen.

### 4. GAIA-X Self-Description registrieren

Nach dem Deployment:

```bash
curl https://YOUR_IP/api/v1/gaia-x/self-description
```

Diese URL im GAIA-X Federated Catalogue eintragen.

## Kosten (ca.)

| Ressource | Kosten |
|-----------|--------|
| s3.xlarge.4 | ~0,25 €/h ≈ 180 €/Monat |
| EVS 100 GB | ~10 €/Monat |
| EIP | ~5 €/Monat |
| **Gesamt** | **~195 €/Monat** |

## GitHub Actions Deployment

Siehe [Deploy to Open Telekom Cloud](../../.github/workflows/deploy-otc.yml). Secret `OTC_SSH_PRIVATE_KEY` in den Repository Secrets hinterlegen.

## Preflight vor Deployment

```bash
./scripts/deployment_preflight.sh --scenario bare-metal
# Fuer grosse Institut-Hardware:
./scripts/deployment_preflight.sh --scenario institute
```

## Update- und Bugfix-Delivery

Empfehlung fuer OTC-Produktivsysteme:
- Image-Tags in `terraform.tfvars` oder `.env` fest pinnen.
- Nach Update `docker compose -f docker-compose.prod.yml pull && up -d`.
- `tofu output` + Health-Endpoint als Abnahme dokumentieren.

Rollback:
- Vorherige Image-Tags wiederherstellen.
- Compose erneut ausrollen.
