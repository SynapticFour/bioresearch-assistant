# Architecture Overview

This document explains the system at a level that helps contributors reason about change impact.

## Goals

- Keep behavior predictable and testable.
- Keep security and operational concerns explicit.
- Keep extension points clear for new features.

## High-level structure

- **Web UI + API**: FastAPI backend, React/TypeScript frontend (see repository layout).
- **BioResearch Assistant core**: literature workflows, pseudonymisation, GA4GH-oriented services, MII export paths, notebooks, etc.
- **Locus (RAG module)**: optional on-premise RAG stack (Ollama-class local inference, curated indexes for domain retrieval — PubMed/guidelines/MII/GA4GH-oriented corpora as productized subscriptions). **Not** a medical device; assistive research/documentation only. See [docs/LOCUS-MODULE.md](docs/LOCUS-MODULE.md).

## Data and control flows

Describe how requests/events flow through the system and where validation, authorization, and persistence happen.

## Reliability and security boundaries

Describe trust boundaries, secret handling, and failure modes that contributors should keep in mind.

## Key extension points

List where new integrations, endpoints, or jobs should be added.
