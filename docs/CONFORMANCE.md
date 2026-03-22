# Conformance / QA (GA4GH & verwandte Endpunkte)

## Zweck
Diese Seite dokumentiert eine **entscheidungssichere** Qualitätssicherung für die in diesem Repo implementierten GA4GH-relevanten APIs. Ziel sind **automatisierte Contract-/Integrations-Tests** (keine formale GA4GH-Zertifizierung).

Hinweis: Diese Tests prüfen die **Implementierungsoberflächen** (Routing, erwartete Statuscodes, grundlegende Response-Struktur und zentrale Sicherheits-/Validierungsannahmen). Eine vollständige Spezifikations-Auditierung (z. B. über externe Conformance Suites) ist hier **nicht** abgebildet.

## GA4GH Funktionalität im Repo (Inventory)
In diesem Repo sind (mindestens) folgende GA4GH-relevanten Bereiche implementiert bzw. abgedeckt:

1. **GA4GH DRS v1 (Data Repository Service)**  
   - Basis-Path: `/ga4gh/drs/v1`
   - Implementiert in: `backend/app/api/v1/endpoints/drs.py`
   - Typische Operationen: `GET /service-info`, `GET/POST /objects`, `GET /objects/{object_id}/access/{access_id}`, `GET /objects/{object_id}/stream`

2. **GA4GH WES v1 (Workflow Execution Service)**  
   - Basis-Path: `/ga4gh/wes/v1`
   - Implementiert in: `backend/app/api/v1/endpoints/wes.py`
   - Typische Operationen: `GET /service-info`, `GET /runs`, `POST /runs`, `GET /runs/{run_id}/status`, `POST /runs/{run_id}/cancel`, `GET /runs/{run_id}`

3. **GA4GH Phenopackets v2 (Patienten-Phänotypen, Spec-kompatible Struktur)**  
   - Basis-Path: `/api/v1/phenopackets`
   - Implementiert in: `backend/app/api/v1/endpoints/phenopackets.py`
   - Abdeckung: HPO-Suche und Create/Validate/Export/CRUD für Phenopackets

4. **GA4GH Passport Claims (Auth-Expectation für geschützte Endpunkte)**  
   - Passport Claim-Quelle im JWT: `ga4gh_passport_v1` (plus Visas: `ga4gh_visa_v1`)
   - Implementiert in: `backend/app/services/auth_service.py` / `backend/app/core/auth.py`
   - Erwartung: Endpunkte mit `get_current_user` benötigen (in Production) einen Bearer Token mit passenden Claims.

## Was wird in CI getestet?
Die CI-Pipeline läuft bereits einen vollständigen Testlauf über `pytest tests/`. Zusätzlich gibt es hier einen expliziten **Conformance-Job**, der die GA4GH-relevanten Tests gezielt ausführt.

**Wann läuft CI?** (`.github/workflows/ci.yml`)
- **Push** auf `main`, `develop` sowie Branches `feat/**`, `fix/**`, `chore/**`, `release/**`
- **Pull requests** mit Zielbranch `main` oder `develop`
- **Manuell:** GitHub → Actions → Workflow „CI“ → „Run workflow“ (`workflow_dispatch`)

Ältere Konfigurationen haben nur `main`/`develop` getriggert — dann liefen Pushes auf reine Feature-Branches **ohne** sichtbare Pipeline.

### Mapping: CI Job / Befehl → GA4GH-Bereich
| CI Job / Schritt | Befehl | Abgedeckte GA4GH Bereiche |
|---|---|---|
| `test` (bestehender Job) | `pytest tests/ -v --cov=app --cov-report=xml --cov-report=term-missing --cov-fail-under=0` (im Repo `backend/` Working Directory) | DRS, WES, Phenopackets, Auth (Passport-Claims) sowie weitere nicht-GA4GH Komponenten |
| `conformance-ga4gh` (neuer Job) | `pytest tests/test_drs_*.py tests/test_wes_*.py tests/test_phenopackets.py tests/test_auth.py -v --cov=app --cov-fail-under=0` | DRS, WES, Phenopackets, Auth (Passport-Claims) |
| `helixtest-ga4gh` | Siehe Abschnitt **HelixTest CI** unten | Externe Suite: Profil `bioresearch-assistant` (WES, DRS, token-only Auth) |

## HelixTest CI (Profil `bioresearch-assistant`)

Die Pipeline führt **[SynapticFour/HelixTest](https://github.com/SynapticFour/HelixTest.git)**
mit dem Profil **`bioresearch-assistant`** aus — kompatibel mit der Dokumentation in
`helixtest/profiles/bioresearch-assistant.toml` und
`helixtest/docs/subset-profiles.md`.

**Befehl (analog zur HelixTest-README):**

```bash
cargo run -p helixtest-cli --bin helixtest -- \
  --all \
  --profile bioresearch-assistant \
  --mode generic \
  --report json \
  --fail-level 1
```

**Setup in CI (Kurzfassung):**

1. **API** auf Port **8080** (wie Profil-Defaults), SQLite-Datei + `alembic upgrade head`.
2. **DRS:** Datei `test-object-1` unter `DRS_STORAGE_PATH` (Inhalt beliebig, z. B. eine Textzeile).
3. **OIDC-Stubs:** `backend/scripts/ci_oidc_for_helixtest.py` liefert Discovery + JWKS; die App nutzt
   `OIDC_ISSUER` / `OIDC_CLIENT_ID` passend zum Skript.
4. **Tokens:** `TEST_BEARER` und `HELIXTEST_DEFAULT_BEARER` müssen **identisch** sein (gültiges RS256-JWT).
   Dafür wird ein kleiner Patch auf Helixtest angewendet: `scripts/helixtest-patches/0001-default-bearer-for-confidential-drs-wes.patch`
   (siehe `scripts/helixtest-patches/README.md`). Ziel: DRS/WES Contract-Calls authentifizieren, während
   reine Auth-Negativtests weiterhin ohne Default-Bearer laufen.

**WES / HelixTest:** Das Backend implementiert die in HelixTest verwendeten **`trs://...`-Stubs** (Echo / Fail / CWL-Echo / Invalid)
in-process, inkl. Timing für den Robustness-Poll-Test (mindestens ~2 s bis zum Terminal-Complete beim Echo).

**DRS / Range:** `GET …/stream` unterstützt `Range: bytes=…` mit **206** und `Content-Range` (HelixTest Level 2).

## HelixTest: Machbar oder nicht? (Historisch)
**Früher** war HelixTest hier **nicht** als vollständiger GA4GH Conformance Run vorgesehen, weil:
| Grund | Auswirkung |
|---|---|
| Das Repo implementiert GA4GH **primär für DRS und WES** (Phenopackets ist vorhanden, aber nicht unter `/ga4gh/*` prefixiert) | HelixTest-Gesamtsuiten erfordern typischerweise mehr Services/Endpoints (z. B. TRS/TES/Beacon/Auth-Pfade) als in dieser Codebasis abgedeckt sind |
| Kein HelixTest Runner/HelixTest-Setup ist in CI/Docs vorhanden | Es gibt keine garantierte, reproduzierbare externe Conformance Ausführung wie in Ferrum Mode |

Die **Subset-Lösung** mit Profil `bioresearch-assistant` + CI-Job **`helixtest-ga4gh`** adressiert den Kern (WES+DRS+Auth-Token-Checks) ohne TES/TRS/Beacon/htsget.

### Konsequenz (Alternativen)
Weiterhin sinnvoll: **automatisierte Smoke-/Contract-Conformance** via `pytest`:
- **DRS**: Response-Struktur, `object_id`-Pfadlogik (mehrsegmentige IDs), Zugriff/Stream-Routing.
- **WES**: Routing (`/runs/.../status`, `/runs/.../cancel`), `POST /runs` Medien-Typen (`application/json` vs. multipart), Workflow-URL Validierung (Allowlist/SSRF-Schutz als implementierte Security-Grenze).
- **Phenopackets**: Minimaler GA4GH-ähnlicher Workflow (List/Create) und Pseudonym-ID Annahme.
- **Passport Claims**: extrahierte Token-Claims in `get_current_user` Contract.

## Bekannte Limitationen / Was wir bewusst nicht testen
Diese Liste definiert die Grenzen für Entscheidungsträger:

1. **Keine formale GA4GH-Zertifizierung**: Die Tests sind technische Contract-/Integrations-Checks, keine offizielle Conformance-Bestätigung.
2. **Keine externe HelixTest-Suite**: Externe Conformance Coverage (z. B. vollständige Schema/Edge-Case Matrizen über alle GA4GH Services) ist nicht integriert.
3. **Implementierungsvereinfachungen**:  
   - DRS nutzt Datei-basierte Storage-Logik; exakte Spezifikationsdetails zu Storage-Backends (z. B. s3-presigned Varianten, komplexe Access Headers) werden hier nur soweit über die API-Contract-Tests abgedeckt.
   - WES führt in der Testumgebung keine echten Nextflow-Workflows aus; Prozess-/Subprocess-Interaktionen werden gemockt und prüfen damit Contract + Zustandsübergänge.
4. **Auth-Realismus im Testkontext**:  
   In CI/Test-Läufen wird `get_current_user` typischerweise über Dependency Overrides ersetzt. Das prüft Token-/Passport-Extraktion separat über die Auth-Tests, ersetzt aber keinen echten OIDC-Flow.

## Wie du es reproduzieren kannst (clean checkout)
### Voraussetzungen
- Das Repo unterstützt Python **3.11** (siehe `INSTALLATION.md`)
- Docker ist für die hier beschriebenen Testläufe **nicht erforderlich**, da Tests in-memory DB nutzen.

### Schritt 1: Setup
```bash
cd /Users/alexandersenf/devel/SynapticFour/bioresearch-assistant

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Schritt 2: (Optional) Backend starten
Für reine Testausführung nicht zwingend, hilft aber für manuelle Smoke-Checks:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Schritt 3: Conformance-Smoke ausführen
Wichtig: Für Subset-Tests kann Coverage-Schwellenwert greifen. Nutze daher explizit `--cov-fail-under=0`.

```bash
cd backend

pytest \
  tests/test_drs_endpoints.py \
  tests/test_drs_endpoint_extended.py \
  tests/test_drs_service.py \
  tests/test_wes_api.py \
  tests/test_wes_service.py \
  tests/test_wes_service_extended.py \
  tests/test_wes_service_workflows.py \
  tests/test_phenopackets.py \
  tests/test_auth.py \
  -v \
  --cov=app \
  --cov-fail-under=0
```

### Auth Hinweis (manuell vs. CI)
- **CI/Test-Kontext**: Auth-Dependency wird gemockt/über Overrides ersetzt; die Tests konzentrieren sich auf Contract/Response.
- **Manuelle Tests gegen eine laufende Instanz**:  
  - Dev-Modus: Wenn OIDC nicht konfiguriert ist (`auth_enabled: false`), ist kein Token nötig. (Siehe `docs/DEVELOPER-GUIDE.md`)
  - Produktion: Geschützte Endpunkte erwarten `Authorization: Bearer <token>`. Token muss GA4GH Passport Claims enthalten (siehe `SECURITY.md` und `docs/AUTH-SETUP.md`).

## CI: Empfohlener lokaler Manual-Command (Exit-Code)
Alle Commands in dieser Seite folgen dem Standard:
- Exit-Code `0`: Conformance-Smoke ist erfolgreich
- Exit-Code `!= 0`: Mindestens ein GA4GH Test ist fehlgeschlagen oder Setup fehlerhaft

## Ferrum ([SynapticFour/Ferrum](https://github.com/SynapticFour/Ferrum)) — übernommene Patterns (ohne Crypt4GH)

Die Rust-Referenzimplementierung liefert einige **betriebsreife** Ideen, die hier **teilweise** nachgebildet sind (Crypt4GH bleibt bewusst außen vor):

### DRS
| Thema | Umsetzung im BioResearch Assistant |
|--------|--------------------------------------|
| **Chunk-Streaming + Read-Timeout** | `GET …/stream` liefert Bytes über `iter_object_bytes()` (64 KiB-Chunks, `asyncio.to_thread`, Timeout pro Read) statt großer Range-Reads im RAM. |
| **Strukturierte Access-Logs** | INFO-Logs mit `extra={drs_event, object_id, client_ip}` bei `get_object`, `get_access`, `stream_*` (kein Dateiinhalt). |
| **`drs://`-Auflösung** | `resolve_object_identifier()` in `drs_service`: gleicher Host wie `drs_base_url` → interne Objekt-ID. |
| **`access_url`-Normalisierung** | Modul `drs_access_url.py`: String vs. `{"url":…}` für künftige DB-/Import-Pfade (wie Ferrum `access_url.rs`). |

### WES
| Thema | Umsetzung |
|--------|-----------|
| **Workflow-Typ-Aliase** | `NFL` / `NXF` / `nextflow` → gespeichert als `NEXTFLOW` (analog Ferrum `RunManager::executor_for_type`). |
| **Subprocess-Timeout (optional)** | `wes_subprocess_timeout_seconds` in Settings: `asyncio.wait_for(process.communicate(), …)`; `None` = unbegrenzt (Standard für lange Pipelines). |
| **`GET /runs?state=`** | Optionaler Filter nach `State` (Ferrum-Liste mit `state`-Query). |

