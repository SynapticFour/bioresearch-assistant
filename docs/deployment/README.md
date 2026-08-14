# Deployment Scenarios

Diese Seite ist der Einstiegspunkt fuer alle Installationswege.

## Schnellwahl nach Szenario

| Szenario | Empfohlener Weg | Internet noetig waehrend Install? | Hauptdokument |
|---|---|---|---|
| Laptop / lokale Tests | Interaktiver Installer | Ja | `docs/INSTALL.md` |
| Bare Metal / VM (online) | Docker Compose (`docker-compose.prod.yml`) | Ja | `docs/deployment/DFN-CLOUD.md`, `docs/deployment/OPEN-TELEKOM-CLOUD.md` |
| Voll isoliertes Rechenzentrum (air-gapped) | Offline Bundle Export/Import + Compose | Nein (auf Zielsystem) | `docs/deployment/OFFLINE-AIRGAP.md` |
| Azure Einstieg | ACI + Managed PostgreSQL | Ja | `docs/deployment/AZURE.md` |
| Kubernetes (Institute) | AKS/On-Prem K8s + Helm | Ja | `docs/deployment/AZURE.md` |

## Kundenszenarien (typisch)

- Klinik/Institut ohne externe API-Nutzung: lokales Ollama, `ISOLATION_MODE=user|team`, Checkliste [UNIKLINIK.md](UNIKLINIK.md).
- Forschungsgruppe mit GPU-Server (z. B. A100, >=100 GB RAM): groessere Ollama Modelle (`gpt-oss:120b`, `deepseek-r1:70b`) und Compose/K8s.
- Schnelle Pilotphase: Azure ACI oder DFN/OTC VM mit `docker-compose.prod.yml`.
- Datenschutzkritische Umgebung: Offline Bundle Pipeline und interne Artefakt-Freigabe.

## Artefakte pro Deployment-Weg

- **Compose online:** `docker-compose.prod.yml` (Passwort Pflicht, kein Default `bioresearch`), `.env`, GHCR Images. Docker-Socket nicht gemountet.
- **Nextflow DiD (nicht Klinik-Default):** `docker-compose.nextflow-dind.yml` nur nach Freigabe.
- **Offline/Air-gapped:** exportiertes Bundle (`docker save` + optional Ollama Modelle) und Importskript.
- **Cloud IaC:** `deployment/otc/` (OpenTofu).
- **Kubernetes:** `deployment/azure/helm/` (Chart mit Backend/Frontend/Ollama/Postgres).

## Hinweise zur Plattform

- `docker-compose.prod.yml` nutzt `DOCKER_PLATFORM` (Default `linux/amd64`).
- Fuer ARM-Systeme (z. B. bestimmte Edge-Setups): `DOCKER_PLATFORM=linux/arm64`.
- Image Overrides:
  - `BACKEND_IMAGE`
  - `FRONTEND_IMAGE`

## Preflight (vor jedem Rollout empfohlen)

Szenario-basierte Deployment-Checks:

```bash
./scripts/deployment_preflight.sh --scenario laptop
./scripts/deployment_preflight.sh --scenario workstation
./scripts/deployment_preflight.sh --scenario institute
./scripts/deployment_preflight.sh --scenario bare-metal
./scripts/deployment_preflight.sh --scenario kubernetes
./scripts/deployment_preflight.sh --scenario offline
```

## Update- und Bugfix-Strategie

Empfohlene Release-Politik:
- **Stable Channel:** produktive Kundensysteme, nur getestete Releases.
- **Fast Channel:** Pilotprojekte/Testsysteme, schnellere Feature-Adoption.
- **Patch Channel:** Sicherheits- und Bugfix-Only (keine Feature-Spruenge).

### Delivery je Installationspfad

| Pfad | Empfohlener Delivery-Weg | Rollback-Strategie | Frequenz |
|---|---|---|---|
| Laptop / lokale Tests | `git pull` + Installer/Compose neu starten | Zurueck auf vorherigen Git-Tag/Commit | nach Bedarf |
| Bare Metal / VM (online) | Image-Tag pinnen (`BACKEND_IMAGE`, `FRONTEND_IMAGE`) + `docker compose pull && up -d` | vorherigen Image-Tag re-deployen | monatlich + Hotfix |
| Air-gapped | Neues Offline-Bundle exportieren/importieren (versioniert, signiert, geprueft) | vorheriges Bundle erneut importieren | quartalsweise + Security-Fixes |
| Azure ACI | Neues ACR/GHCR Image deployen, env unveraendert | letzter stabiler ACR-Tag | monatlich + Hotfix |
| Kubernetes (AKS/on-prem) | Helm values mit festen Image-Tags, `helm upgrade` | `helm rollback` auf vorige Revision | monatlich + Hotfix |

### Operative Mindeststandards

- Immer **feste Image-Tags** statt `latest` in Produktion.
- Vor jedem Update: `./scripts/deployment_preflight.sh --scenario ...`
- Nach jedem Update:
  - Health prüfen: `GET /api/v1/health`
  - Kernfunktionstest (z. B. Literatursuche + RAG)
  - Auth-Flow testen (falls OIDC aktiv)
- Change-Dokumentation: eingesetzter Release-Tag, Datum, Verantwortliche, Rollback-Tag.

SOP-Vorlage fuer Teams: `docs/deployment/UPDATE-SOP.md`.
Release-Checkliste: `docs/deployment/RELEASE-CHECKLIST.md`.
