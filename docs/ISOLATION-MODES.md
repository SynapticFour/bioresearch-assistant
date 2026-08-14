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

1. GA4GH Passport AffiliationAndRole Visa
2. OIDC organization claim (Azure AD, Keycloak)
3. Email-Domain: alle `@ukhd.de` = ein Team

Beispiel: Alle `@dkfz.de` Forscher teilen eine gemeinsame Paper-Bibliothek.

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

Falls die automatische Email-Domain-Erkennung nicht ausreicht, können Teams explizit über Keycloak oder Azure AD Groups konfiguriert werden.

**Keycloak:**

- Gruppe z. B. `bioresearch-team-a` erstellen
- Nutzer zuweisen
- Group Claim im Token aktivieren: Mappers → Group Membership → `groups`

In `backend/app/core/isolation.py` in `_extract_team_id()` kann ergänzt werden:

```python
# Keycloak Groups
if groups := current_user.get("groups"):
    return f"group:{groups[0]}"
```

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
