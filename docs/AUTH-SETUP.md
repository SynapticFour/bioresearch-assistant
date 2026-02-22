# Authentifizierung einrichten

## Überblick
BioResearch Assistant unterstützt OpenID Connect (OIDC)
mit GA4GH Passport Spec v1.2.

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
   OIDC_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback
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
   ```

### 3. Google (für schnelle Tests)
1. https://console.cloud.google.com
2. OAuth2 Client erstellen
3. In .env:
   ```
   OIDC_ISSUER=https://accounts.google.com
   OIDC_CLIENT_ID=xxx.apps.googleusercontent.com
   OIDC_CLIENT_SECRET=dein-secret
   OIDC_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback
   ```

## Dev-Modus (kein Auth)
Ohne OIDC Konfiguration läuft das System im Dev-Modus —
kein Login nötig, alle Endpunkte offen.
Für Produktion immer Auth konfigurieren!

## GA4GH Passport Visas
Das System versteht folgende Visa-Typen:
- ResearcherStatus — Forscher-Verifikation
- AffiliationAndRole — Institutionszugehörigkeit
- ControlledAccessGrants — Zugang zu kontrollierten Daten
