# Datenisolation — Konfiguration

## Überblick

BioResearch Assistant unterstützt drei Isolations-Modi, die über eine einzige Environment-Variable konfiguriert werden:

- `ISOLATION_MODE=user` — Standard: persönliche Daten
- `ISOLATION_MODE=team` — Forschungsgruppen
- `ISOLATION_MODE=open` — Nur Demo/Dev

## Modus-Vergleich

| Aspekt           | user | team | open |
|------------------|------|------|------|
| Papers sichtbar  | Nur eigene | Ganze Institution | Alle |
| Phenopackets     | Nur eigene | Ganze Institution | Alle |
| DRS Dateien      | Nur eigene | Ganze Institution | Alle |
| Audit Log        | Nur eigener | Ganzes Team | Global |
| Empfohlen für    | Klinik | Forschungsgruppe | Demo |

## Wann welchen Modus?

### User-Modus (`ISOLATION_MODE=user`)

Empfohlen für:

- Klinisches Setting mit strikter Datentrennung
- Verschiedene Ärzte/Forscher einer Institution
- Wenn Patientendaten pro Person isoliert sein müssen

Beispiel: Zwei Ärzte am UKHD sehen jeweils nur ihre eigenen pseudonymisierten Patienten.

### Team-Modus (`ISOLATION_MODE=team`)

Empfohlen für:

- Forschungsgruppen, die gemeinsam arbeiten
- Laborgruppen mit geteilter Paper-Bibliothek
- Wenn ein Team gemeinsam Daten analysiert

**Team-Erkennung (automatisch, Priorität):**

1. GA4GH Passport AffiliationAndRole Visa (konsumiert, nicht von BRA ausgestellt)
2. IdP-Gruppen aus dem Operator-Claims-Map (`OIDC_PROFILE`: Keycloak `groups`, Entra `groups`, LS Login `eduperson_entitlement`)
3. OIDC organization claim (Azure AD `tid`, Keycloak `organization`)
4. Email-Domain: alle `@ukhd.de` = ein Team
5. Fallback: `user:<sub>`

Beispiel: Entra-Gruppe `UKHD-Forschung` → `team_id=group:UKHD-Forschung`. Alle `@dkfz.de` ohne Gruppen-Claim teilen `domain:dkfz.de`.

### Open-Modus (`ISOLATION_MODE=open`)

Nur Demo und lokale Entwicklung. **Produktionsstart (`ENVIRONMENT=production`) verweigert diesen Modus.**

Nur für:

- Demo-Installationen (Railway, Vercel)
- Lokale Entwicklung

⚠️ **Niemals für Produktionsbetrieb mit echten Daten!**

## Konfiguration pro Deployment

### Lokal / Docker

In `.env`:

```bash
ISOLATION_MODE=user
```

### DFN-Cloud (Forschungsinstitut)

In `.env`:

```bash
ISOLATION_MODE=team
# Teams automatisch via DFN-AAI Email-Domain erkannt
```

### Azure / Uniklinik (z. B. UKHD)

In `.env`:

```bash
ISOLATION_MODE=team
# Teams via Azure AD organization claim
```

### Railway / Vercel Demo

```bash
ISOLATION_MODE=open
```

## Team-Erkennung anpassen

Gruppen kommen aus dem IdP-Token, gemappt in `backend/app/core/claims_map.py`. Kein Passport-Minting aus Gruppen.

**Keycloak:** Gruppe z. B. `bioresearch-team-a` anlegen, Nutzer zuweisen, Mapper „Group Membership“ → Claim `groups`. `OIDC_PROFILE=keycloak` (oder `auto`).

**Microsoft Entra:** Gruppentoken in der App-Registrierung aktivieren (optional Security Groups). `OIDC_PROFILE=entra`. Claim `groups` (GUIDs oder Namen je nach Token-Konfiguration).

**LS Login / ELIXIR:** `OIDC_PROFILE=ls-login` mappt `eduperson_entitlement`.

In `ISOLATION_MODE=team` wird die erste Gruppe zu `team_id` (`group:<name>`). Passport-Affiliation sticht Gruppen.

## Migration bestehender Daten

Falls du von `open` zu `user`/`team` wechselst:

```bash
python backend/scripts/migrate_isolation.py \
  --mode user \
  --assign-to contact@synapticfour.com
```

(Skript bei Bedarf anlegen.)

## Aktuellen Modus prüfen

`GET /api/v1/auth/me` gibt zurück:

```json
{
  "sub": "user-123",
  "email": "forscher@ukhd.de",
  "isolation_mode": "team",
  "team_id": "domain:ukhd.de",
  "scope": {"team_id": "domain:ukhd.de"}
}
```
