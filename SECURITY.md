# Sicherheitsrichtlinie — BioResearch Assistant

## Unterstützte Versionen

| Version | Support |
|---------|---------|
| 1.3.x   | ✅ Aktiv |
| 1.2.x   | ⚠️ Sicherheits-Fixes only |
| < 1.2   | ❌ Kein Support |

## Sicherheitslücken melden

**Bitte keine öffentlichen GitHub Issues für Sicherheitslücken!**

### Kontakt
E-Mail: security@synapticfour.de

### Was wir brauchen
- Beschreibung der Lücke
- Schritte zur Reproduktion
- Mögliche Auswirkungen
- Betroffene Versionen

### Was du erwarten kannst
- Bestätigung innerhalb 48 Stunden
- Status-Update innerhalb 7 Tagen
- Fix innerhalb 90 Tagen (je nach Schwere)
- Erwähnung im CHANGELOG (wenn gewünscht)

## Sicherheits-Architektur

### Authentifizierung
- OpenID Connect / OAuth2
- JWT Token Verifikation via JWKS
- GA4GH Passport v1.2

### Datenschutz
- Microsoft Presidio Pseudonymisierung
- Audit Trail für alle De-Pseudonymisierungen
- Konfigurierbare Datenisolation (user/team/open)
- Vollständige Datensouveränität mit Ollama

### Netzwerk
- Rate Limiting auf alle sensitiven Endpunkte
- CORS mit eingeschränkten Origins/Methods
- HTTPS in Produktion erforderlich

### Datenbank
- Parameterisierte Queries (SQLAlchemy ORM)
- Kein dynamisches SQL
- Verschlüsselte Pseudonymisierungs-Keys (Fernet)

## Bekannte Einschränkungen

- Embeddings auf Railway nicht verfügbar (kein pgvector)
- Demo-Modus (ISOLATION_MODE=open) nicht für Produktion
- Anthropic API überträgt Texte nach USA
