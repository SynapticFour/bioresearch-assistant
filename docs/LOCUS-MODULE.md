# Locus — On-Premise RAG module (BioResearch Assistant)

**Locus** is the optional **Retrieval-Augmented Generation (RAG)** deployment path inside **BioResearch Assistant**: same product philosophy (on-premise first, no substitute for clinical judgment), extended with a packaged LLM+RAG stack for **German clinical bioinformatics** contexts.

This document is **technical positioning**, not legal advice or a medical-device claim.

---

## Relationship to BioResearch Assistant

- Locus is **not** a separate commercial website SKU; it is documented as a **module** of BioResearch Assistant (BUSL-1.1 aligned with the rest of the codebase).
- Like the rest of the platform, it is a **research and documentation assistant** — **not** a medical device, **not** for automated diagnosis, **not** a replacement for qualified clinical review.

---

## Evidence (landscape, not a product warranty)

Published and pilot work in **German healthcare settings** has explored **on-premise LLMs** for physician-facing writing assistance with explicit reference to **GDPR** and **state hospital law** (e.g. Baden-Württemberg) as part of the legal framing. Separate work reports **strong F1 scores** for **oncology attribute extraction** from **German pathology reports** using **on-premise** models (e.g. Llama-class and Mistral-class) with a **RAG pipeline**.

These results illustrate **feasibility** of local deployment; your institution must still validate fit, governance, and documentation.

---

## Market gap (why a domain-specific stack)

- Open models that can run **on-premise** are needed to reduce off-site data flows.
- Medical LLM weights (e.g. Meditron-class lines) often **do not target German clinical bioinformatics** workflows end-to-end.
- Generic private-LLM enterprise vendors may lack **bioinformatics + GA4GH + MII** context.
- US-centric clinical NLP suites are often **expensive** and **not** focused on **German-language** clinical bioinformatics operations.

---

## What Locus provides (architecture intent)

| Area | Intent |
|------|--------|
| **Core runtime** | **Ollama**-style local deployment (e.g. Llama 3.x or Mistral-class), **no** routine data exchange with external inference APIs. |
| **Compliance docs** | GDPR-oriented **documentation packs** can ship with engagements (technical materials; **not** legal advice). |
| **Special indexes** | Curated vector stores, e.g. PubMed abstracts (genomics/oncology filters), guideline corpora (e.g. S3, ESMO, NCCN), **MII KDS** documentation, **GA4GH** specifications — **updated on a subscription** cadence. |
| **Use cases** | Grant literature mining, pathology report summarisation, **MTB** preparation support, plain-language explainers for variant classification terms (e.g. VUS, pathogenic) for colleagues — **assistive only**. |

---

## Licensing and services

- **Code / product**: **BUSL-1.1** (same family as BioResearch Assistant / Ferrum policy — see repository `LICENSE` and [BUSINESS-MODEL.md](BUSINESS-MODEL.md)): permissible **non-commercial research** use; **commercial** use and support under contract.
- **Indexes**: optional **subscription** (monthly or yearly) for curated index updates.

---

## Operational disclaimer

Locus **does not** make clinical decisions, **does not** output diagnoses, and **does not** replace PACS/LIS workflows or qualified review. Treat outputs as **drafts** for human verification in your governance model.
