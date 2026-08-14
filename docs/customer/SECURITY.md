# BioResearch Assistant — Security one-pager (customer-facing)

**Audience:** IT security, data protection, and clinical pilot evaluators
**Not legal advice / not a certification claim.** Operators remain responsible for local risk acceptance, contracts, and regulatory classification.

---

## What this product provides

BioResearch Assistant is an on-premise-capable research platform (literature, GA4GH DRS/WES, Phenopackets, optional local RAG). It implements technical controls that *support* privacy-preserving operation. It does **not** declare legal compliance or medical-device certification for your site.

---

## Residual risks you must plan for

### 1. DRS objects — at-rest encryption limits

GA4GH **DRS** stores research files on the operator-controlled filesystem path (`DRS_STORAGE_PATH`).

| Control | Current state |
|---------|----------------|
| Auth on DRS list/get/stream | Required |
| Path traversal protections | Implemented |
| **Encryption of DRS file contents at rest** | **Not provided by the application today** |

Disk / volume encryption (LUKS, cloud provider volume encryption, etc.) is an **operator responsibility**. Application-level DRS file encryption is on the product roadmap (see internal audit notes). Treat unencrypted DRS blobs as an accepted residual risk until that lands or you encrypt the volume.

### 2. US-LLM transfer risk (cloud AI providers)

If you enable a US-hosted LLM API (for example Anthropic), **prompt and abstract content leave your environment** and are processed in a third country.

| Path | Data location | Recommendation |
|------|---------------|----------------|
| **Ollama (local)** | Stays on your infrastructure | Preferred for sensitive / clinical-adjacent data |
| Cloud LLM API | Third country (e.g. USA) | Only with legal basis, SCCs/AVV as applicable, and preferably pseudonymized inputs only |
| No LLM | No model transfer | Maximum control |

The UI surfaces a warning when a cloud LLM path is active. Pseudonymization of inputs reduces exposure but does not by itself legalize a transfer.

### 3. Clinical pilots — Ollama + pen-test path

For **clinical pilots involving patient-related data**, Synaptic Four’s posture is:

1. **Require local LLM (Ollama)** — do not send clinical or identifiable content to US cloud LLMs.
2. **Commission a penetration test** (or equivalent independent security assessment) before production clinical use.
3. Complete site-specific validation (DPIA, role model, encryption at rest for DB/volumes, backup/incident process) with your DPO / ISB.

### 4. Session cookies and isolation

OIDC sets an **httpOnly** session cookie. The SPA does not store access tokens in `localStorage`. Production refuses `ISOLATION_MODE=open`, unauthenticated local auth, CORS `*`, and the default database password. Operator checklist: [UNIKLINIK.md](../deployment/UNIKLINIK.md).

### 5. Docker socket / Nextflow

The default compose files do **not** mount `/var/run/docker.sock`. An optional overlay exists for lab/HPC only (`docker-compose.nextflow-dind.yml`) and is a host-escape path.

BioResearch Assistant is **not recommended as a medical device** (FDA/MDR) without a separate regulatory programme.

---

## Related documents

| Document | Purpose |
|----------|---------|
| [COMPLIANCE.md](../COMPLIANCE.md) | Technical alignment with DSGVO, GA4GH, GAIA-X design (no certificates) |
| [AUDIT-REPORT.md](../AUDIT-REPORT.md) | Internal technical assessment / residual risks |
| [SECURITY.md](../../SECURITY.md) | Vulnerability reporting and engineering controls |
| [THREAT_MODEL.md](../THREAT_MODEL.md) | Assets, adversaries, residual risks |
| [UNIKLINIK.md](../deployment/UNIKLINIK.md) | Production start guards and clinic checklist |
| [deployment/README.md](../deployment/README.md) | Deployment matrix (online / offline / air-gap) |

**Security contact:** contact@synapticfour.com (no public GitHub issues for vulnerabilities)
