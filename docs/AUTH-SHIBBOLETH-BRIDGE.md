# Keycloak als OIDC-Brücke zu Shibboleth

## Überblick

Viele Hochschulen und Kliniken betreiben **Shibboleth** (SAML 2.0) als Identity Provider. Der BioResearch Assistant spricht dagegen **OpenID Connect (OIDC)**. Mit **Keycloak** als Brücke können Nutzer sich per Shibboleth anmelden, während die Anwendung weiterhin nur OIDC konfigurieren muss.

**Authentifizierungsfluss:**

```
[Browser] → [BioResearch Assistant] → [Keycloak] → [Shibboleth IdP] → [LDAP/AD]
                (OIDC)                    (SAML 2.0)
```

- BioResearch leitet den Login an Keycloak weiter (OIDC).
- Keycloak leitet an den Shibboleth Identity Provider der Institution weiter (SAML).
- Nach erfolgreicher Anmeldung gibt Keycloak ein OIDC-Token an BioResearch zurück.

---

## Voraussetzungen

- **Keycloak** (selbst gehostet oder in der Institution), Version 21+ empfohlen.
- **Metadaten des Shibboleth IdP** der Institution:
  - Entweder eine **Metadata-URL** (z. B. `https://idp.uni-xyz.de/idp/shibboleth`),
  - oder eine **XML-Metadata-Datei** (von der IT der Institution).
- Optional: Absprache mit der IT für **Entity ID**, **ACS-URL** und **Attribut-Mapping**.

---

## 1. Keycloak starten

```bash
docker run -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=<sicheres-passwort> \
  quay.io/keycloak/keycloak:latest start-dev
```

Für Produktion: [Keycloak Server Installation](https://www.keycloak.org/server/configuration) nutzen (z. B. Hostname, HTTPS, Datenbank).

---

## 2. Realm und Client für BioResearch anlegen

1. **Realm erstellen:** Administration Console → Create realm → z. B. `bioresearch`.
2. **Client für den BioResearch Assistant:**
   - Clients → Create client
   - **Client ID:** `bioresearch-assistant`
   - **Client authentication:** On
   - **Valid redirect URIs:** z. B. `https://bioresearch.ihre-institution.de/api/v1/auth/callback`
   - **Valid post logout redirect URIs:** optional, z. B. `https://bioresearch.ihre-institution.de`
   - Client Secret kopieren → für `OIDC_CLIENT_SECRET` in der `.env` des BioResearch Assistant.

---

## 3. Shibboleth als Identity Provider in Keycloak einbinden

1. **Identity Providers:** Realm `bioresearch` → Identity providers → Add provider.
2. **Provider:** **SAML 2.0** wählen.
3. **Alias:** z. B. `shibboleth` (wird in der Login-URL verwendet).
4. **Konfiguration:**

   | Einstellung        | typischer Wert / Hinweis |
   |--------------------|---------------------------|
   | **Single Sign-On Service URL** | Von der IT: z. B. `https://idp.uni-xyz.de/idp/profile/SAML2/Redirect/SSO` |
   | **Single Logout Service URL**  | Optional, z. B. `https://idp.uni-xyz.de/idp/profile/SAML2/Redirect/SLO` |
   | **Entity ID des IdP**           | Von der IT: z. B. `https://idp.uni-xyz.de/idp/shibboleth` |
   | **Metadata**                    | Entweder **Metadata URL** (z. B. `https://idp.uni-xyz.de/idp/shibboleth`) oder **Metadata XML** (Inhalt der IdP-Metadata-Datei) einfügen. |

5. **Speichern** → Keycloak zeigt die **Keycloak IdP Metadata** bzw. eine **Assertion Consumer Service (ACS) URL** an. Diese **ACS-URL** und die **Entity ID** von Keycloak müssen bei der Shibboleth-IT der Institution als SP registriert werden (falls die Institution das verlangt).

---

## 4. Attribut-Mapping (SAML → OIDC)

Damit BioResearch Assistant E-Mail, Name und ggf. Gruppen erhält, die SAML-Attribute des Shibboleth IdP auf OIDC-Claims mappen:

1. Beim Identity Provider **Shibboleth** → **Mappers**.
2. Mapper anlegen (oder vordefinierte prüfen):

   | Mapper Type | SAML Attribute Name (IdP-seitig) | Token Claim Name (OIDC) |
   |-------------|-----------------------------------|--------------------------|
   | Attribute Importer | `email` oder `mail` | `email` |
   | Attribute Importer | `displayName` oder `cn` | `name` oder `preferred_username` |
   | Attribute Importer | `uid` oder `eppn` | `preferred_username` (falls kein name) |
   | Group Importer (optional) | `entitlement` / `isMemberOf` | `groups` |

Die genauen **SAML-Attributnamen** liefert die IT der Institution (oft in der IdP-Metadata oder in der Attribut-Release-Policy dokumentiert).

---

## 5. First Login Flow (IdP-Auswahl)

Damit Nutzer direkt zu Shibboleth geleitet werden:

1. **Authentication** → **Flows** → **First broker login** prüfen (Standard: IdP-Auswahl oder direkte Weiterleitung).
2. Optional: **Identity provider redirector** so konfigurieren, dass bei nur einem IdP automatisch zu Shibboleth umgeleitet wird (Realm → Identity provider → Shibboleth → **First Login Flow** = First broker login).

---

## 6. BioResearch Assistant konfigurieren

In der `.env` des BioResearch Assistant nur **Keycloak** (OIDC) eintragen; Shibboleth ist für die App unsichtbar:

```bash
OIDC_ISSUER=https://keycloak.ihre-institution.de/realms/bioresearch
OIDC_CLIENT_ID=bioresearch-assistant
OIDC_CLIENT_SECRET=<client-secret-aus-keycloak>
OIDC_REDIRECT_URI=https://bioresearch.ihre-institution.de/api/v1/auth/callback
```

- **OIDC_ISSUER:** Keycloak Realm-URL (mit `/realms/<realm-name>`).
- **OIDC_REDIRECT_URI:** muss exakt mit der in Keycloak eingetragenen Redirect-URI übereinstimmen.

Damit ist die Anleitung aus [AUTH-SETUP.md](AUTH-SETUP.md) (Keycloak) gültig; der eigentliche Login läuft über Shibboleth.

---

## 7. DFN-AAI vs. institutions-eigener Shibboleth

- **DFN-AAI:** Das Deutsche Forschungsnetz bietet unter [aai.dfn.de](https://www.aai.dfn.de) einen **OIDC-Zugang** an. Wenn Ihre Institution bei DFN-AAI ist, können Sie ggf. **ohne** Keycloak-Brücke mit `OIDC_ISSUER=https://www.aai.dfn.de/oidc` arbeiten — siehe [DFN-CLOUD.md](deployment/DFN-CLOUD.md#authentifizierung-mit-dfn-aai).
- **Eigener Shibboleth der Institution:** Wenn die IT nur SAML/Shibboleth anbietet (ohne DFN-AAI-OIDC), ist die Keycloak-Shibboleth-Brücke wie oben die passende Lösung.

---

## 8. Kurz-Checkliste

- [ ] Keycloak-Realm und Client `bioresearch-assistant` angelegt
- [ ] Identity Provider „SAML 2.0“ mit Shibboleth-Metadaten (URL oder XML) konfiguriert
- [ ] ACS-URL / Entity ID bei der Shibboleth-IT der Institution registriert (falls nötig)
- [ ] SAML-Attribute (email, name, ggf. groups) auf OIDC-Claims gemappt
- [ ] `.env` mit Keycloak-OIDC-Werten (OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI)
- [ ] Login im Browser getestet: Weiterleitung Keycloak → Shibboleth → zurück zu BioResearch

---

## Referenzen

- [Keycloak: Identity Brokering](https://www.keycloak.org/docs/latest/server_admin/#_identity_broker)
- [Keycloak: SAML Identity Provider](https://www.keycloak.org/docs/latest/server_admin/#_saml_identity_provider)
- [Shibboleth Consortium](https://www.shibboleth.net/)
- [DFN-AAI](https://www.dfn.de/dienste/dfn-aai/)
