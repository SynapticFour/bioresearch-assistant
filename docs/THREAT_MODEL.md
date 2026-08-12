# BioResearch Assistant — Threat Model

**Status:** Living · customer-shareable
**Version:** 1.0 · 2026-08-12
**Audience:** Security reviewers, operators, procurement
**Related:** product README · Showcase [co-custody.md](https://github.com/SynapticFour/SynapticFour-Showcase/blob/main/docs/for-customers/co-custody.md) · [key-custody.md](https://github.com/SynapticFour/SynapticFour-Showcase/blob/main/docs/for-customers/key-custody.md) · Solum subject bridge docs

This document states **what BioResearch Assistant (BRA) protects, from whom, and what is out of scope**. It is not a penetration-test report and not a certification.

---

## 1. Product in one line

BRA is a **customer-operated on-premise research platform** (literature mining, pseudonymisation, MII/FHIR-oriented export, optional Locus RAG, Phenopacket paths). Synaptic Four does not hold customer production PHI/genomic payloads in the default model.

---

## 2. Assets

| Asset | Sensitivity | Notes |
|-------|-------------|-------|
| Literature / corpus indexes | Low–Medium | Often public or licensed content; still IP-sensitive |
| Study / patient-linked research records | High | Special-category when health-related |
| Pseudonym / subject identifiers | High | Linkage risk across systems |
| `solum_subject_id` / Phenopacket bridge fields | High | Join key into clinical plane |
| Export bundles (MII/FHIR/Phenopacket) | High | Leave the BRA boundary |
| Optional RAG prompts / retrieved chunks | Medium–High | May echo study context |
| Operator credentials / DB / object store | Critical | Full system compromise |

---

## 3. Trust boundaries

```text
┌──────────────────────────────────────────────────────┐
│ Operator organisation                                │
│  ┌────────────┐   ┌────────────┐   ┌──────────────┐ │
│  │ BRA app    │───│ DB / files │   │ Optional LLM │ │
│  │ + APIs     │   │            │   │ (Locus/local)│ │
│  └─────┬──────┘   └────────────┘   └──────────────┘ │
│        │ optional subject link                       │
│        ▼                                             │
│  ┌────────────┐                                      │
│  │ Solum /    │  clinical compliance plane           │
│  │ Ferrum     │  (separate perimeter)                │
│  └────────────┘                                      │
└──────────────────────────────────────────────────────┘
```

| Boundary | Inside | Outside |
|----------|--------|---------|
| Process | BRA services | Clients, browsers, partner EHRs |
| Clinical plane | Optional link IDs only | Solum policy/audit enforcement |
| Genomic plane | Optional Ferrum DRS/WES use | Ferrum gateway trust model |
| LLM | Operator-chosen local/on-prem path | Public cloud LLM (if enabled — out of default trust) |

---

## 4. Adversaries (assumptions)

| Actor | Goal | Assumption |
|-------|------|------------|
| External network attacker | RCE / data theft | Operator patches OS; BRA not internet-exposed without auth |
| Malicious insider (researcher) | Exfiltrate study data | RBAC + audit on exports; least privilege |
| Confused deputy / weak export | Over-broad MII/Phenopacket dump | Consent checks + validation reports are advisory evidence, not legal clearance |
| Supply-chain | Malicious dependency | SBOM + audit CI (org C8); pin releases |

**Out of scope for this model:** physical theft of operator laptops; nation-state against operator IdP; certification of EHDS/MDR compliance.

---

## 5. Controls (as designed)

- Customer-hosted deployment; no Synaptic Four production custody by default
- Pseudonymisation and export validation reports as **technical evidence**
- Optional Solum subject link (`solum_subject_id`) documented; fails closed when misconfigured
- Optional Locus RAG intended for operator-controlled models/indexes
- Support / IR: founder-scale; see Showcase support-tiers and company IR pointers

---

## 6. Residual risks (honest)

1. **Export oversharing** — validated structure ≠ authorized purpose; governance stays with the operator.
2. **Subject-link misuse** — a wrong `solum_subject_id` joins the wrong clinical identity; operators own join discipline.
3. **LLM leakage** — if a cloud LLM is configured, prompts may leave the trust boundary; default guidance is local.
4. **Not a medical device** — no diagnosis/therapy claims.

---

## 7. Review cadence

Revisit when: new export formats ship; Solum bridge semantics change; a paying pilot changes hosting model; after any security incident involving BRA.
