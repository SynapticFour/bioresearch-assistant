# GAIA-X Alignment — BioResearch Assistant

## Was ist GAIA-X?

GAIA-X ist die europäische Initiative für souveräne, vertrauenswürdige Dateninfrastruktur. Kern-Prinzipien: Datensouveränität, Transparenz, Interoperabilität, Portabilität.

## BioResearch Assistant GAIA-X Prinzipien

| GAIA-X Prinzip   | Status | Implementierung                                                                 |
|-----------------|--------|----------------------------------------------------------------------------------|
| Datensouveränität | ✅     | On-Premise (Ollama) = volle Souveränität; Anthropic API = partiell (siehe README) |
| DSGVO-Konformität | ✅     | Presidio Pseudonymisierung + Audit Logging                                       |
| Offene Standards  | ✅     | GA4GH DRS, WES, Phenopackets v2                                                  |
| Transparenz       | ✅     | Open Source, vollständige API-Dokumentation                                      |
| Portabilität      | ✅     | Docker-basiert, läuft auf jeder Infrastruktur                                   |
| Interoperabilität | ✅     | REST APIs, GA4GH Standards, JSON-LD                                              |
| Föderierbarkeit   | 🔄     | Vorbereitet — multi-tenant Architektur geplant                                   |
| Self-Description  | 🔄     | GAIA-X Self-Description in Vorbereitung                                          |

## Was bedeutet "GAIA-X Ready by Design"?

"GAIA-X Ready by Design" ist **keine offizielle Zertifizierung** der GAIA-X Association. Es beschreibt, dass die Architektur des BioResearch Assistant von Grund auf nach GAIA-X Prinzipien gestaltet wurde: Datensouveränität im On-Premise-Modus (Ollama), DSGVO durch technische und organisatorische Maßnahmen, offene Standards und Transparenz durch Self-Description und Open Source.

## Authentifizierung & Identität

| Aspekt | Implementierung |
|--------|------------------|
| **Föderierte Identität via OIDC** | Anbindung an GAIA-X Identity & Trust — Unterstützung für Keycloak, DFN-AAI, ELIXIR AAI, Azure AD, Google |
| **GA4GH Passports** | Nutzeridentität und Berechtigungen — Visa-Typen ResearcherStatus, AffiliationAndRole, ControlledAccessGrants |

## Multi-Tenancy und GAIA-X Föderierbarkeit

### Was wir implementiert haben

BioResearch Assistant unterstützt ein konfigurierbares Isolation-System (`ISOLATION_MODE=user` / `team` / `open`). Das erfüllt:

- ✅ Datenisolation innerhalb einer Instanz
- ✅ Team-basierte Datentrennung
- ✅ User-Level Zugriffskontrolle
- ✅ Audit Trail pro User/Team

### Was GAIA-X Föderierbarkeit bedeutet

GAIA-X Föderierbarkeit hat zwei Ebenen:

**Ebene 1 — Intra-Instanz Isolation (✅ implementiert):**  
Mehrere Nutzer/Teams teilen eine Installation mit strikter Datentrennung.  
→ Unser `ISOLATION_MODE`-System.

**Ebene 2 — Inter-Instanz Föderation (⏳ geplant):**  
Mehrere separate Installationen (z. B. UKHD + DKFZ) können Daten kontrolliert austauschen mit:

- Gegenseitiger Authentifizierung via DFN-AAI
- Einverständnis-basiertem Datenaustausch
- GA4GH ControlledAccessGrants Visa
- Gemeinsamen Ontologien (HPO, OMIM)

### Aktueller Status

- **Ebene 1:** ✅ Vollständig implementiert
- **Ebene 2:** ⏳ Vorbereitet durch:
  - GA4GH Passport Support
  - DRS für dateibasierte Föderierung
  - OpenID Connect mit DFN-AAI  
  Vollständige Implementierung in Roadmap.

## Roadmap zur offiziellen Zertifizierung

- [ ] GAIA-X Self-Description erstellen
- [ ] GAIA-X Association Mitgliedschaft prüfen
- [ ] Federated Catalogue Eintrag
