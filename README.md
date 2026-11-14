# BioResearch Assistant

Research teams collect publications, protocols, and reports, and then need to ask questions of that collection. BioResearch Assistant is the working environment for that work. By default the language model runs on your own computer.

For research teams.

**Status: Early use.** Supported line 0.2.x. Registry: BRA-MATURITY-001. Early use is not a certification. A HelixTest run is a technical signal, not a GA4GH certification.

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL%201.1-blue.svg)](LICENSE)

GitHub may label this Other. The SPDX identifier is BUSL-1.1.

## What it does

- You enter a literature search. The program asks PubMed, a public literature database, and returns the hits. That call does not store them. Registry: BRA-FLOW-001.
- You save a hit in the library. The program stores the text and a vector, a numeric form of the text used to find similar papers. Registry: BRA-FLOW-001.
- You ask a question in ordinary language. The program looks for similar saved texts that already have vectors, and a language model writes an answer from them. The answer lists the papers it used. Registry: BRA-FLOW-001.
- A summary of one stored abstract uses the same model choice. With no usable cloud key, that call goes to the model on the same computer. Registry: BRA-USE-001, BRA-DATA-LOCATION-001.
- Further functions are in the code: a biological file registry with an upload limit of 500 MB, analysis workflows, BLAST (a program that compares biological sequences), notebooks, an upload to Zenodo (a public research archive), and an export for the Medical Informatics Initiative. Registry: BRA-MODULES-001.
- GA4GH is a set of shared interfaces for genomic and health data. The file interface (DRS) and the workflow interface (WES) under `/ga4gh/` are this program's own, until `FERRUM_DRS_URL` or `FERRUM_WES_URL` is set. Those calls are then proxied to [Ferrum](https://github.com/SynapticFour/Ferrum).

## Limits

- Early use, on the 0.2.x line. Tag `v0.2.2` is commit `003fbb1f4939df36e29dec3d837f04d5c716be6b`. The default branch this documentation was cut from is the next commit, `491879effd3b1cd167bc3cc2498ec8590d9ec0a3`. The version fields in `backend/pyproject.toml` and `frontend/package.json` say 0.2.2. That tag is not this commit. Registry: BRA-MATURITY-001.
- There is no Gaia-X certification and no GDPR certification. The API reports `gaia_x_ready: false`. Alignment notes are in [docs/GAIA-X-ALIGNMENT.md](docs/GAIA-X-ALIGNMENT.md) and [docs/COMPLIANCE.md](docs/COMPLIANCE.md). HelixTest CI is not a GA4GH certification. Registry: BRA-MATURITY-001.
- The literature flow is present in the code. This page does not record an end-to-end run from the search to the answer. A question needs saved texts that already have vectors. The source list on an answer is the papers placed in the context. It is not a check that every sentence comes from those papers. Read the sources. Registry: BRA-FLOW-001.
- It does not make a clinical decision. Registry: BRA-USE-001.
- In production, sign-in through the operator's sign-in system is required. By default each person sees only their own entries. A mode in which everyone sees everything does not start in production. The operator can share entries with a group. This program does not issue Passports. Registry: BRA-ACCESS-001.
- The getting-started guide, the install guide, and the operator handbook describe setup, including a computer without internet. They do not state support terms, and they do not say that Synaptic Four operates the system. Registry: BRA-HANDOVER-001.
- English is the base language of this repository. Some pages under `docs/` are in German. [docs/README.md](docs/README.md) says which.

> This README describes technical capabilities, not legal advice. See [docs/COMPLIANCE.md](docs/COMPLIANCE.md) and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## What stays on your computer and what goes outside

What is stored sits where the operator points it, and the language model runs on the same computer by default. A literature search goes outside on every use. A summary goes outside once a cloud key is set. The code has further paths. They are listed below. Registry: BRA-DATA-LOCATION-001.

**Stays with you**

- Saved texts sit in the database whose address the operator sets (`DATABASE_URL`). The table is `papers`, and the search vectors sit there with pgvector.
- Stored files sit in a directory whose path the operator sets. The setting the program reads is `DRS_STORAGE_PATH`. The code default is `/tmp/drs`. The name `DRS_DATA_DIR` in the example file is not that setting.
- With no usable cloud key, a summary calls a model through Ollama. The code default model is `mistral:7b`. The code default address is `http://localhost:11434`, read from `OLLAMA_URL`. The example file sets `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=mistral`.

**Goes outside**

- Every literature search sends the query to PubMed, at `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`. Fetching one paper by its PubMed id uses the same service.
- A DOI lookup, when someone asks for one, calls `https://api.crossref.org`.
- A summary goes to Anthropic when a usable cloud key is set. A usable key starts with `sk-ant-` and is longer than 20 characters. The code default for that model is `claude-haiku-4-5`. One request can choose the cloud model with the header `X-BRA-LLM` when that key is set.
- The code default for the provider is `auto`: a usable Anthropic key selects Claude, otherwise Ollama. The operator chooses the provider, the model, and the address. `OLLAMA_URL` can point away from this computer. A third provider, `openai_compatible`, calls the address in `OPENAI_BASE_URL`.

The production compose file sets `OLLAMA_BASE_URL`. The program reads `OLLAMA_URL`. That compose file also leaves the Ollama container behind the `ollama` profile, so `docker compose -f docker-compose.prod.yml up` does not start it. The operator handbook describes that profile.

**Only when the operator turns them on**

- An upload to Zenodo, when `ZENODO_TOKEN` is set. The code posts to `zenodo.org`, and it also allows `sandbox.zenodo.org`.
- A Ferrum proxy for the file and workflow surfaces, when `FERRUM_DRS_URL` or `FERRUM_WES_URL` is set.
- A fetch of a remote workflow, when `WES_ALLOW_REMOTE_WORKFLOWS` is set. The code default is off.
- An extra corpus named Locus, off by default (`LOCUS_ENABLED`). Its rows are shared and are not tied to one person.
- A subject link to [Solum](https://github.com/SynapticFour/Solum), when the Solum address and token are set. See [docs/SOLUM-SUBJECT-BRIDGE.md](docs/SOLUM-SUBJECT-BRIDGE.md).

A notebook run in the browser loads Pyodide from `https://cdn.jsdelivr.net/pyodide/v0.27.5/full/` unless `VITE_PYODIDE_INDEX_URL` is set.

Text search loads `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` in the program on the first embedding. The weight files are not in this repository. Whether they are already on the computer is not shown here. This repository has no recording of the network traffic for every setting.

## What you need

- Docker, and Python 3.11 or newer. `backend/pyproject.toml` allows Python from 3.11 up to, and not including, 3.13. The install guide recommends 3.12, and it names Docker Desktop 24.x as the minimum it was written for.
- The install guide names at least 8 GB of RAM and 10 GB of disk, and recommends 16 GB and 30 GB. It labels the 16 GB cell as a Compose limit, not a measurement. `docker-compose.prod.yml` limits the Ollama service to 16 GB, the backend to 4 GB, and the frontend to 512 MB. The operator handbook estimates about 24 GB when Ollama and the backend run together, and it calls that an estimate. The 10 GB and 30 GB figures are in the install guide. They are not disk limits in the Compose files read for this page.
- The model classes follow the size of the machine. The install guide names small models for 8 to 16 GB, medium models for 24 to 64 GB, and large models for an institute server with a graphics processor. A graphics processor is optional. It is not required to start. Registry: BRA-REQUIREMENTS-001.

## Quick start

Prerequisites: Docker, and Python 3.11 or newer (3.12 recommended). The lock-file install runs in this repository alone.

```bash
pip install --require-hashes --no-deps --extra-index-url https://download.pytorch.org/whl/cpu -r backend/requirements.lock
make prove
```

`make prove` runs the backend tests without Docker and without the coverage gate. You should see the tests pass, and then the line `BRA prove OK. Live stack: make up`.

```bash
make up
```

This repository contains `docker-compose.full.yml`, so `make up` runs `python3 install.py start`. [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) names the frontend at `http://localhost:3000` and the API at `http://localhost:8000` after a start. Stop: `make down`. Remove volumes: `make destroy`.

A longer path that needs another repository: set `FERRUM_DRS_URL` and `FERRUM_WES_URL`, including the `/ga4gh/drs/v1` and `/ga4gh/wes/v1` prefixes, to proxy those calls to [Ferrum](https://github.com/SynapticFour/Ferrum). Leave them unset to use the local surfaces in this repository.

## Documentation

English is the base language. Every file under `docs/` is listed in [docs/README.md](docs/README.md). The groups are a tutorial, how-to guides, reference, and explanation.

### Tutorial

- [Getting started](docs/GETTING-STARTED.md)

### How-to guides

- [Install](docs/INSTALL.md) — Docker, Python, RAM, disk, and model classes
- [Operator handbook](docs/customer-runbook.md) — setup and update, including a computer without internet
- [Deployment matrix](docs/deployment/README.md) — which install path fits which machine
- [User guide](docs/USER-GUIDE.md)
- Further task pages are in the [index](docs/README.md#how-to-guides)

### Reference

- [For evaluators](docs/FOR-EVALUATORS.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- Further reference pages are in the [index](docs/README.md#reference)

### Explanation

- [Architecture](docs/ARCHITECTURE.md)
- [Who it is for, beside Ferrum and Solum](docs/IDENTITY.md)
- [Architecture decisions](docs/adr/README.md)
- [Commercial licence](docs/COMMERCIAL.md) — how to ask for one; the page is not a signed grant

## Licence

The BioResearch Assistant is licensed under the Business Source License 1.1. Each version becomes Apache-2.0 four years after its release date. Non-commercial academic research, personal evaluation and contributing to the source are permitted. Production use needs a commercial licence. Ferrum and Solum are licensed separately. Registry: BRA-LICENSE-001. The file is shorter than the full Business Source License text. Not legal advice. The file is [LICENSE](LICENSE).

## Cite

Use [CITATION.cff](CITATION.cff). Prefer that file over a hand-copied line.

## Website

- Product page: [https://synapticfour.com/en/bioresearch-assistant/](https://synapticfour.com/en/bioresearch-assistant/)
- Technical profile: [https://synapticfour.com/en/technical/bioresearch-assistant/](https://synapticfour.com/en/technical/bioresearch-assistant/)

The same pages exist in German (`/de/bioresearch-assistant/`, `/de/technik/bioresearch-assistant/`) and in French (`/fr/bioresearch-assistant/`, `/fr/technique/bioresearch-assistant/`).

The map of repositories: [profile/README.md](https://github.com/SynapticFour/.github/blob/main/profile/README.md).

Contact: [contact@synapticfour.com](mailto:contact@synapticfour.com)
