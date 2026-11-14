# BioResearch Assistant documentation

Every document under `docs/`, grouped as a tutorial, how-to guides, reference, and explanation. One line each.

English is the base language of this repository. A page marked German is written in German.

## Tutorial

| Document | What it is |
|----------|------------|
| [GETTING-STARTED.md](GETTING-STARTED.md) | The lock-file install, `make prove`, and `make up`, with the two localhost ports. |

## How-to guides

| Document | What it is |
|----------|------------|
| [INSTALL.md](INSTALL.md) | German. Docker, Python, RAM, disk, and which model class fits which machine. |
| [USER-GUIDE.md](USER-GUIDE.md) | German. The screens: literature, files, workflows, BLAST, notebooks, and Zenodo. |
| [TOOLS-SETUP.md](TOOLS-SETUP.md) | German. A BLAST database, a workflows directory, and a local inference server. |
| [DEVELOPER-GUIDE.md](DEVELOPER-GUIDE.md) | German. How to call the API, and the environment variables. |
| [customer-runbook.md](customer-runbook.md) | German and English. Install and update, including a computer without internet. |
| [deployment/README.md](deployment/README.md) | German. Which install path fits a laptop, a server, a cloud, or a machine without internet. |
| [deployment/OFFLINE-AIRGAP.md](deployment/OFFLINE-AIRGAP.md) | German. Build a bundle on a connected machine and import it on one without internet. |
| [deployment/UPDATE-SOP.md](deployment/UPDATE-SOP.md) | German. A template for a controlled update. |
| [deployment/RELEASE-CHECKLIST.md](deployment/RELEASE-CHECKLIST.md) | German. The checks before a production release. |
| [deployment/UNIKLINIK.md](deployment/UNIKLINIK.md) | German. A checklist for running at a university hospital. |
| [deployment/AZURE.md](deployment/AZURE.md) | German. Deploy on Microsoft Azure. |
| [deployment/DFN-CLOUD.md](deployment/DFN-CLOUD.md) | German. Deploy on DFN-Cloud. |
| [deployment/OPEN-TELEKOM-CLOUD.md](deployment/OPEN-TELEKOM-CLOUD.md) | German. Deploy on Open Telekom Cloud. |
| [deployment/RAILWAY.md](deployment/RAILWAY.md) | German. A demonstration deploy on Railway. |
| [deployment/DOCKER-HUB-SETUP.md](deployment/DOCKER-HUB-SETUP.md) | German. Optional Docker Hub setup. |
| [AUTH-SETUP.md](AUTH-SETUP.md) | German. Set up sign-in with OpenID Connect. |
| [AUTH-SHIBBOLETH-BRIDGE.md](AUTH-SHIBBOLETH-BRIDGE.md) | German. Use Keycloak as a bridge to Shibboleth. |
| [DATA-INTEGRATION.md](DATA-INTEGRATION.md) | German. Which screen calls which endpoint. |
| [MII-EXPORT.md](MII-EXPORT.md) | Export a bundle for the Medical Informatics Initiative. Not a legal opinion. |
| [PHENOFLOW.md](PHENOFLOW.md) | Connect stored Phenopackets to a workflow through the file and workflow surfaces. |
| [CI.md](CI.md) | Which workflows run on a push, and which are started by hand. |
| [RELEASING.md](RELEASING.md) | How the offline bundle is built. A tag does not attach that archive. |

## Reference

| Document | What it is |
|----------|------------|
| [FOR-EVALUATORS.md](FOR-EVALUATORS.md) | What this tree tests, and what it does not claim. |
| [THREAT_MODEL.md](THREAT_MODEL.md) | What the program protects, from whom, and what is out of scope. |
| [customer/SECURITY.md](customer/SECURITY.md) | A one-page security note for an operator. Not a certificate. |
| [COMPLIANCE.md](COMPLIANCE.md) | German. Technical measures. Not legal advice and not a certification. |
| [COMPLIANCE-SUMMARY.md](COMPLIANCE-SUMMARY.md) | German. A short form of that note. |
| [GAIA-X-ALIGNMENT.md](GAIA-X-ALIGNMENT.md) | German. How the design lines up with Gaia-X principles. Not a label. |
| [gaia-x-self-description.json](gaia-x-self-description.json) | A prepared self-description. The licence field is BUSL-1.1, the same as the licence file. Literature search sends the query to PubMed. The API reports `gaia_x_ready` false. |
| [CONFORMANCE.md](CONFORMANCE.md) | German. Contract tests for the GA4GH surfaces. Not a GA4GH certification. |
| [ISOLATION-MODES.md](ISOLATION-MODES.md) | German. Per person, per group, and the open mode that production refuses. |
| [API-VERSIONING.md](API-VERSIONING.md) | German. The `/api/v1` and `/ga4gh/` paths, and how a version changes. |
| [VERSIONING.md](VERSIONING.md) | The published tags, including the mistaken `v1.0.0`, and where `v0.2.2` points. |
| [SBOM.md](SBOM.md) | A human-readable list of dependencies. A machine-readable bill is generated at release. |
| [PRODUCT-CORRECTIONS.md](PRODUCT-CORRECTIONS.md) | German. Statements that product sheets must not make. |

Files outside `docs/` that the same reading needs: [CHANGELOG.md](../CHANGELOG.md), [SECURITY.md](../SECURITY.md), [CONTRIBUTING.md](../CONTRIBUTING.md) (German), [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md), [RELEASING.md](../RELEASING.md), [INSTALLATION.md](../INSTALLATION.md) (German; a pointer to the install guide), [ARCHITECTURE.md](../ARCHITECTURE.md), [DECISIONS.md](../DECISIONS.md), [LICENSE](../LICENSE), [CITATION.cff](../CITATION.cff).

`docs/.gitkeep` keeps this directory. It has no text.

## Explanation

| Document | What it is |
|----------|------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | The UI, the API, the database, and when the file and workflow surfaces stay local. |
| [IDENTITY.md](IDENTITY.md) | A workbench that runs without Ferrum, and what it refuses to be. |
| [LOCUS-MODULE.md](LOCUS-MODULE.md) | The optional shared corpus. It is off by default, and it is not a clinical decision. |
| [SOLUM-SUBJECT-BRIDGE.md](SOLUM-SUBJECT-BRIDGE.md) | An optional link from a Phenopacket id to a Solum subject. |
| [COMMERCIAL.md](COMMERCIAL.md) | How to ask for a commercial licence. The page is not a signed grant. |
| [BUSINESS-MODEL.md](BUSINESS-MODEL.md) | Which uses the licence file permits, and which need a written agreement. |
| [adr/README.md](adr/README.md) | Index of the decision records in `DECISIONS.md`. |
| [README.md](README.md) | This index. |
