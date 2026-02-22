# Deployment auf DFN-Cloud

## Warum DFN-Cloud?

DFN (Deutsches Forschungsnetz) verbindet alle deutschen Universitäten und Forschungsinstitute. On-premise im deutschen Forschungsnetz — ideal für die Zielgruppe.

## Voraussetzungen

- DFN-Cloud Account (über Heimateinrichtung beantragen)
- OpenStack CLI: `pip install python-openstackclient`
- OpenTofu (open source Terraform): `brew install opentofu`

## Schritt-für-Schritt Anleitung

### 1. OpenStack Credentials

DFN-Cloud Dashboard → API Access → Download OpenStack RC File

```bash
source bioresearch-openstack.rc
```

### 2. SSH Key hinterlegen

```bash
openstack keypair create --public-key ~/.ssh/id_rsa.pub bioresearch-key
```

### 3. Security Group

```bash
openstack security group create bioresearch-sg
openstack security group rule create --proto tcp --dst-port 22 bioresearch-sg
openstack security group rule create --proto tcp --dst-port 80 bioresearch-sg
openstack security group rule create --proto tcp --dst-port 443 bioresearch-sg
openstack security group rule create --proto tcp --dst-port 8000 bioresearch-sg
```

### 4. Instanz erstellen

Empfohlen: m1.large (4 vCPU, 8GB RAM) für Ollama

```bash
openstack server create \
  --flavor m1.large \
  --image "Ubuntu 22.04" \
  --key-name bioresearch-key \
  --security-group bioresearch-sg \
  bioresearch-server
```

### 5. Floating IP zuweisen

```bash
openstack floating ip create public
openstack server add floating ip bioresearch-server <FLOATING_IP>
```

### 6. Server einrichten

```bash
ssh ubuntu@<FLOATING_IP>
curl -fsSL https://get.docker.com | sh
sudo apt install docker-compose-plugin -y
sudo usermod -aG docker ubuntu
```

### 7. BioResearch Assistant deployen

```bash
git clone https://github.com/SynapticFour/bioresearch-assistant.git
cd bioresearch-assistant
cp .env.example .env
nano .env  # Werte eintragen (GITHUB_REPO=synapticfour/bioresearch-assistant, DB_*, PSEUDONYMIZATION_ENCRYPTION_KEY, etc.)
```

Ollama Modell vorladen (einmalig, ~4GB):

```bash
docker run --rm -v ollama_data:/root/.ollama ollama/ollama pull mistral
```

Starten:

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 8. SSL mit Let's Encrypt

```bash
sudo apt install certbot -y
sudo certbot certonly --standalone -d deine-domain.dfn.de
```

## Kosten (ca.)

| Ressource   | Kosten        |
|------------|----------------|
| m1.large   | ~0,15 €/h ≈ 110 €/Monat |
| Storage 50GB | ~5 €/Monat   |
| **Gesamt** | **~115 €/Monat** |

## Authentifizierung mit DFN-AAI

Das Deutsche Forschungsnetz betreibt **DFN-AAI** — den föderativen Identitätsdienst für deutsche Hochschulen und Forschungseinrichtungen.

BioResearch Assistant integriert sich nativ:

```
OIDC_ISSUER=https://www.aai.dfn.de/oidc
OIDC_CLIENT_ID=dein-client-id
OIDC_CLIENT_SECRET=dein-secret
OIDC_REDIRECT_URI=https://deine-app.dfn.de/api/v1/auth/callback
```

**Registrierung:** https://www.dfn.de/dienste/dfn-aai/

Alle deutschen Universitäten sind bereits Mitglied.

## GitHub Actions Deployment

Siehe [Deploy to DFN-Cloud](../../.github/workflows/deploy-dfn.yml). Secret `DFN_SSH_PRIVATE_KEY` (privater SSH-Key für den Server) in den Repository Secrets hinterlegen.
