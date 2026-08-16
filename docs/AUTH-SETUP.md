# Authentifizierung einrichten

## Überblick
BioResearch Assistant unterstützt OpenID Connect (OIDC)
mit GA4GH Passport Spec v1.2.

**Datenisolation:** In Produktion ist `ISOLATION_MODE=user` oder `team` Pflicht (`open` wird beim Start abgelehnt). Siehe [ISOLATION-MODES.md](ISOLATION-MODES.md). Uniklinik-Checkliste: [deployment/UNIKLINIK.md](deployment/UNIKLINIK.md).

## Session (httpOnly Cookie)

Der OIDC-Callback tauscht den Authorization Code serverseitig und setzt das Cookie `bra_access_token` (httpOnly, SameSite=Lax, Secure außerhalb von Dev). Die SPA speichert **keine** Access Tokens in `localStorage`. Logout: `POST /api/v1/auth/logout`.

`OIDC_REDIRECT_URI` und `FRONTEND_BASE_URL` müssen **same-origin** zur SPA sein (Reverse-Proxy). Sonst speichert der Browser das Cookie nicht für die UI.

| Umgebung | Beispiel |
|----------|----------|
| Produktion | `OIDC_REDIRECT_URI=https://bra.uniklinik.example/api/v1/auth/callback` · `FRONTEND_BASE_URL=https://bra.uniklinik.example` |
| Lokales Vite | `OIDC_REDIRECT_URI=http://localhost:5173/api/v1/auth/callback` · `FRONTEND_BASE_URL=http://localhost:5173` (Vite-Proxy) |

## Unterstützte Provider

### 1. Keycloak (empfohlen für Institutionen)
Selbst gehostet, volle Kontrolle, GA4GH Passport Support.

```bash
docker run -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:latest start-dev
```

Dann:
1. Realm erstellen: bioresearch
2. Client erstellen: bioresearch-assistant
3. Client Secret kopieren
4. In .env eintragen:
   ```
   OIDC_ISSUER=http://localhost:8080/realms/bioresearch
   OIDC_CLIENT_ID=bioresearch-assistant
   OIDC_CLIENT_SECRET=dein-secret
   OIDC_REDIRECT_URI=http://localhost:5173/api/v1/auth/callback
   FRONTEND_BASE_URL=http://localhost:5173
   ```

### 2. ELIXIR AAI (für Forschungsinstitute)
ELIXIR ist die europäische Forschungsinfrastruktur.
GA4GH Passport nativ unterstützt.

1. Account auf https://aai.elixir-europe.org
2. Service registrieren
3. In .env:
   ```
   OIDC_ISSUER=https://login.elixir-czech.org/oidc
   OIDC_CLIENT_ID=dein-client-id
   OIDC_CLIENT_SECRET=dein-secret
   OIDC_REDIRECT_URI=https://deine-app/api/v1/auth/callback
   FRONTEND_BASE_URL=https://deine-app
   ```

### 3. Google (nicht für Uniklinik-Produktion)

US-IdP (Drittland). Nur Evaluation. Primärlogin in der UI ist institutionelles OIDC / Entra ID.
1. https://console.cloud.google.com
2. OAuth2 Client erstellen
3. In .env:
   ```
   OIDC_ISSUER=https://accounts.google.com
   OIDC_CLIENT_ID=xxx.apps.googleusercontent.com
   OIDC_CLIENT_SECRET=dein-secret
   OIDC_REDIRECT_URI=http://localhost:5173/api/v1/auth/callback
   FRONTEND_BASE_URL=http://localhost:5173
   ```

## De-Pseudonymisierung — Zugriffskontrolle

Wer darf De-Pseudonymisierung durchführen, wird über **DEPSEUDO_ACCESS** gesteuert:

| Wert   | Bedeutung |
|--------|-----------|
| `owner` | Nur der User, der pseudonymisiert hat (Standard) |
| `team`  | Alle Mitglieder desselben Teams |
| `admin` | Nur Nutzer mit Rolle `admin` |

Beispiel in `.env`:
```bash
DEPSEUDO_ACCESS=owner   # Standard
# DEPSEUDO_ACCESS=team
# DEPSEUDO_ACCESS=admin
```

Jeder De-Pseudonymisierungs-Zugriff wird im Audit Log protokolliert (operation_type=DEPSEUDONYMIZE).

## Dev-Modus (kein Auth)

Ohne `OIDC_ISSUER` + `OIDC_CLIENT_ID` und mit explizitem `DEPLOYMENT=local|development|test` gibt es einen Dev-User. **In Produktion startet der Prozess dann nicht** (`assert_runtime_hardened`). Leeres `DEPLOYMENT` gilt als Produktion (fail-closed).

## GA4GH Passport Visas

BRA **consumes** `ga4gh_passport_v1` / `ga4gh_visa_v1` from the JWKS-verified OIDC ID token. It does **not** decode or verify nested visa JWTs (that is Ferrum when `FERRUM_DRS_URL` / `FERRUM_WES_URL` are set, plus the AAI broker). `AffiliationAndRole` dicts in `ga4gh_visa_v1` may set team isolation. Passport-gated **bytes** are Ferrum’s job: BRA forwards `Authorization` unless `FERRUM_BEARER_TOKEN` overrides it.

Claim types you may see (not independently re-verified here):

- ResearcherStatus — researcher assertion from the broker
- AffiliationAndRole — institutional affiliation (team isolation)
- ControlledAccessGrants — dataset grants — **enforced on DRS/WES by Ferrum**, not by BRA

---

## Beispiel: Universitätsklinikum Heidelberg

Das Universitätsklinikum Heidelberg (UKHD) nutzt typischerweise **Microsoft Azure Active Directory (Azure AD)** als Identity Provider — wie die meisten deutschen Universitätskliniken.

### Integration mit Azure AD / Microsoft Entra ID

1. **Im Azure Portal:**
   portal.azure.com → Azure Active Directory → App-Registrierungen → Neue Registrierung

   - **Name:** BioResearch Assistant
   - **Unterstützte Kontotypen:** „Nur Konten in diesem Organisationsverzeichnis“
   - **Umleitungs-URI:** `https://bioresearch.ukhd.de/api/v1/auth/callback`

2. **Nach der Registrierung:**
   - Application (client) ID kopieren → `OIDC_CLIENT_ID`
   - Zertifikate & Geheimnisse → Neuer geheimer Clientschlüssel → Wert kopieren → `OIDC_CLIENT_SECRET`

3. **OIDC Issuer für UKHD:**
   `OIDC_ISSUER=https://login.microsoftonline.com/{UKHD-TENANT-ID}/v2.0`
   Tenant ID: Azure AD → Übersicht → Mandanten-ID

4. **In .env eintragen:**
   ```
   OIDC_ISSUER=https://login.microsoftonline.com/TENANT-ID/v2.0
   OIDC_CLIENT_ID=APPLICATION-ID
   OIDC_CLIENT_SECRET=CLIENT-SECRET
   OIDC_REDIRECT_URI=https://bioresearch.ukhd.de/api/v1/auth/callback
   FRONTEND_BASE_URL=https://bioresearch.ukhd.de
   MICROSOFT_TENANT_ID=TENANT-ID
   ```

5. **API-Berechtigungen:**
   Azure AD → App-Registrierungen → BioResearch Assistant → API-Berechtigungen → Berechtigung hinzufügen → Microsoft Graph → openid, email, profile

### Andere häufige Systeme an deutschen Unikliniken

| Institution | Typischer Provider | Konfiguration |
|-------------|--------------------|---------------|
| Uniklinik Heidelberg | Azure AD | Wie oben |
| Uniklinik München (LMU) | Shibboleth / DFN-AAI | [DFN-AAI Anleitung](deployment/DFN-CLOUD.md#authentifizierung-mit-dfn-aai) |
| Charité Berlin | Azure AD | Wie oben |
| Uniklinik Hamburg | Shibboleth | Keycloak + Shibboleth Bridge |
| Deutsches Krebsforschungszentrum | ELIXIR AAI | [ELIXIR Anleitung](#2-elixir-aai-für-forschungsinstitute) |

### Shibboleth (ältere Institutionen)

Manche Institutionen nutzen noch Shibboleth. Lösung: **Keycloak als OIDC-Brücke** vor Shibboleth:

```
[Browser] → [BioResearch] → [Keycloak] → [Shibboleth] → [LDAP]
```

Keycloak kann als SAML-zu-OIDC Bridge fungieren.
Anleitung: [AUTH-SHIBBOLETH-BRIDGE.md](AUTH-SHIBBOLETH-BRIDGE.md)

### GA4GH Passports an Unikliniken

Für kontrollierte Datensätze (DKFZ, EGA, …) stellt der **AAI-Broker** (ga4gh-infra oder ELIXIR) die Visas aus. BRA liest die Claims aus dem ID-Token. Die **Durchsetzung** auf DRS/WES liegt bei Ferrum, wenn BRA als Client (`FERRUM_DRS_URL` / `FERRUM_WES_URL`) den Bearer weiterreicht. Nested Visa-JWTs prüft BRA nicht selbst.
