# Uniklinik-Betrieb — Checkliste

**Audience:** Forschungs-IT, ISB, Datenschutzbeauftragte, Einkauf
**Kein Rechtsrat, keine Zertifizierung, kein Medizinprodukt.**

Diese Seite beschreibt, was BioResearch Assistant **technisch erzwingt** und was die Klinik **selbst** klären muss, bevor Produktionsdaten (auch nur pseudonymisiert) verarbeitet werden.

---

## 1. Was der Prozess beim Start in Produktion ablehnt

`ENVIRONMENT=production` (oder `DEPLOYMENT` in `production|prod|azure|otc|dfn|k8s`) ruft `assert_runtime_hardened()` auf. Der Dienst **startet nicht**, wenn:

| Bedingung | Grund |
|-----------|--------|
| `DEPLOYMENT=local` / `development` / `test` | Unauthentifizierter Dev-User |
| `ISOLATION_MODE=open` | Alle sehen alle Datensätze |
| `CORS_ORIGINS` enthält `*` | Cookie-Diebstahl / CSRF-Klasse |
| `OIDC_ISSUER` oder `OIDC_CLIENT_ID` leer | Kein institutioneller Login |
| Datenbank-URL mit Passwort `bioresearch` | Default-Secret |

Zusätzlich: OpenAPI `/docs` ist in Produktion aus; Security-Header (CSP, HSTS) sind aktiv.

---

## 2. Pflichtkonfiguration (Mindestbar)

```bash
ENVIRONMENT=production
DEPLOYMENT=dfn          # oder azure / otc / k8s / production
ISOLATION_MODE=user     # oder team (Forschungsgruppe)
DEPSEUDO_ACCESS=owner

OIDC_ISSUER=https://idp.uniklinik.example/realms/hospital
OIDC_CLIENT_ID=bioresearch
OIDC_CLIENT_SECRET=...
# Same-origin wie die SPA (Reverse-Proxy), sonst setzt der Browser das Session-Cookie nicht.
OIDC_REDIRECT_URI=https://bra.uniklinik.example/api/v1/auth/callback
FRONTEND_BASE_URL=https://bra.uniklinik.example

DATABASE_URL=postgresql+asyncpg://bra:<einzigartiges-passwort>@db:5432/bra
POSTGRES_PASSWORD=<einzigartiges-passwort>   # nicht "bioresearch"

LLM_PROVIDER=ollama
# ANTHROPIC_API_KEY nicht setzen, wenn keine Drittlandübertragung gewollt ist
```

Compose-Produktion: `docker-compose.prod.yml` (Passwort per `${DB_PASSWORD:?...}`).
Helm: `helm install ... --set postgres.auth.password='...'` — leer oder `bioresearch` wird abgelehnt.

Details Auth: [AUTH-SETUP.md](../AUTH-SETUP.md). Isolation: [ISOLATION-MODES.md](../ISOLATION-MODES.md).

---

## 3. Session und Frontend

Nach OIDC setzt das Backend ein **httpOnly**-Cookie (`bra_access_token`, SameSite=Lax). Tokens liegen nicht in `localStorage`. Die SPA prüft die Sitzung und leitet ohne Cookie auf `/login`. Logout: `POST /api/v1/auth/logout`.

Markdown in Notebook/RAG wird vor dem Rendern mit DOMPurify bereinigt.

---

## 4. Was nicht im Default-Stack liegt

| Thema | Haltung |
|-------|---------|
| Docker-Socket für Nextflow | Nicht in `docker-compose.full.yml`. Nur Overlay `docker-compose.nextflow-dind.yml` nach Threat-Model-Freigabe (Host-Escape). |
| HelixTest-TRS-Stubs | Nur `WES_HELIXTEST_STUBS=1` in Conformance-CI, nicht in Klinik-Produktion. |
| BLAST `-db` | Allowlist (z. B. `nt`, `swissprot`); keine freien Pfade. |
| FAIR-Score / GAIA-X | Heuristik bzw. Design-Alignment. API: `gaia_x_ready: false`, `gaia_x_certified: false`. |
| DRS at-rest | Anwendungsseitig unverschlüsselt; Volume-Verschlüsselung ist Betreiberpflicht. |
| Nextflow-Image | Gepinnt (Release-Tag), nicht `curl \| bash`. |
| sentence-transformers / transformers 4.x | Residual-CVEs ohne 5.x-Upgrade; gepinntes öffentliches Embedding-Modell. Siehe [SBOM.md](../SBOM.md). |

---

## 5. Organisatorisch (nicht durch Software ersetzbar)

1. AVV / TOM / VVT mit dem Verantwortlichen und ggf. Auftragsverarbeitern.
2. DPIA, wenn besondere Kategorien (Art. 9) verarbeitet werden.
3. Institutioneller IdP (Keycloak, DFN-AAI, Entra ID) — kein Google als Primärlogin.
4. Unabhängiger Pentest vor klinischem Pilot.
5. Einordnung als **kein** automatisches Medizinprodukt (MDR) ohne eigenes Konformitätsverfahren.
6. Backup, Incident, Patch (`pip-audit` / `npm audit` in CI; Dependabot is disabled so majors are not auto-opened).

Kunden-Einseiter: [customer/SECURITY.md](../customer/SECURITY.md). Threat Model: [THREAT_MODEL.md](../THREAT_MODEL.md).
