# GA4GH API Implementations

This directory contains GA4GH-compliant API implementations for the BioResearch Assistant.

Endpoint exposure (actual runtime paths):
- **DRS** and **WES** are exposed under the **`/ga4gh/`** prefix by the backend.
- **Phenopackets** are exposed under **`/api/v1/phenopackets`** (GA4GH Phenopackets v2-compatible structure, but not mounted under `/ga4gh/`).
