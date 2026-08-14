# Release Checklist (10 Pflichtchecks)

Vor jedem Release/Hotfix in Produktivumgebungen:

1. [ ] Scope klar: Ticket/Change-ID, betroffene Komponenten, Zielumgebung.
2. [ ] Feste Image-Tags gesetzt (kein `latest` in Produktion).
3. [ ] `./scripts/docs_consistency_check.sh` erfolgreich.
4. [ ] `./scripts/deployment_preflight.sh --scenario <ziel>` erfolgreich.
5. [ ] Backup erstellt (DB + relevante Volumes + Konfiguration).
6. [ ] Secrets/`.env` geprüft: OIDC gesetzt, `ISOLATION_MODE` nicht `open`, DB-Passwort nicht `bioresearch`, `ENVIRONMENT=production`.
7. [ ] Rollout-Test in Staging/Testsystem erfolgreich.
8. [ ] Post-Deploy Smoke-Test definiert:
   - Health Endpoint
   - mind. 1 Kernfunktion
   - Auth-Flow (falls OIDC aktiv)
9. [ ] Rollback-Pfad vorbereitet:
   - vorheriger Image-Tag/Helm-Revision/Offline-Bundle dokumentiert
10. [ ] Freigabe + Kommunikationsfenster bestätigt (Owner/Stakeholder).

Empfehlung:
- Diese Liste zusammen mit `docs/deployment/UPDATE-SOP.md` verwenden.
