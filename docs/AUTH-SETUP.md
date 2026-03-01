# Authentifizierung einrichten

## Überblick
BioResearch Assistant unterstützt OpenID Connect (OIDC)
mit GA4GH Passport Spec v1.2.

**Datenisolation:** Mit OIDC kann zusätzlich `ISOLATION_MODE=user` oder `team` gesetzt werden, damit Daten pro Nutzer oder pro Team (z. B. E-Mail-Domain) getrennt sind. Siehe [ISOLATION-MODES.md](ISOLATION-MODES.md).

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
Ohne OIDC Konfiguration läuft das System im Dev-Modus —
kein Login nötig, alle Endpunkte offen.
Für Produktion immer Auth konfigurieren!

## GA4GH Passport Visas
Das System versteht folgende Visa-Typen:
- ResearcherStatus — Forscher-Verifikation
- AffiliationAndRole — Institutionszugehörigkeit
- ControlledAccessGrants — Zugang zu kontrollierten Daten

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

Für Zugang zu kontrollierten Datensätzen (z.B. DKFZ-Daten, EGA-Daten) prüft das System automatisch **GA4GH Passport Visas**:

- **ResearcherStatus** → verifizierter Forscher  
- **AffiliationAndRole** → UKHD-Mitarbeiter  
- **ControlledAccessGrants** → Zugang zu spezifischen Daten  
