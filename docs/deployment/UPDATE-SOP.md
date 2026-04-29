# Update SOP Template

Diese Vorlage ist fuer kontrollierte Updates und Bugfix-Rollouts gedacht
(Klinik, Institut, Cloud oder Offline).

## 1) Change-Metadaten

- Change-ID:
- Datum/Uhrzeit:
- Verantwortlich:
- Umgebung: (laptop/workstation/institute/bare-metal/kubernetes/offline)
- Release-Tag(s):
  - Backend:
  - Frontend:
  - Weitere (z. B. Helm Chart):
- Change-Typ: (Security Fix / Bugfix / Minor / Major)

## 2) Risiko- und Scope-Einschaetzung

- Betroffene Komponenten:
- Erwartete Auswirkungen:
- Downtime-Fenster:
- Rollback-Zielversion:
- Abbruchkriterien:

## 3) Vorabpruefungen (Go/No-Go)

- [ ] `./scripts/deployment_preflight.sh --scenario <scenario>` erfolgreich
- [ ] Backup erstellt (DB / wichtige Volumes / Konfiguration)
- [ ] `.env`/Secrets geprueft (keine ungewollten Aenderungen)
- [ ] Ziel-Tags sind fest gepinnt (kein `latest` in Produktion)
- [ ] Stakeholder/Fachbereich informiert

## 4) Rollout-Schritte

- [ ] Update gestartet (Zeitstempel):
- [ ] Deployment ausgefuehrt:
  - Compose: `docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d`
  - oder Helm: `helm upgrade ...`
  - oder Offline-Bundle Import
- [ ] Logs geprueft (Backend/DB/Ollama/Ingress)

## 5) Abnahmetests (Smoke + Fachlich)

- [ ] Health Endpoint: `GET /api/v1/health`
- [ ] Kernfunktion 1 (z. B. Literatursuche)
- [ ] Kernfunktion 2 (z. B. RAG Antwort)
- [ ] Auth/OIDC Login (falls aktiviert)
- [ ] Optional: DRS/WES/PhenoFlow Kernpfad

## 6) Ergebnis

- Status: (Erfolgreich / Teilweise / Fehlgeschlagen)
- Beobachtungen:
- Offene Punkte:

## 7) Rollback (falls noetig)

- [ ] Rollback ausgeloest
- [ ] Vorgehen:
  - Compose: vorherige Image-Tags wieder setzen und `up -d`
  - Helm: `helm rollback <release> <revision>`
  - Offline: vorheriges Bundle erneut importieren
- [ ] Health nach Rollback wieder gruen

## 8) Nachbereitung

- [ ] Change-Log/Runbook aktualisiert
- [ ] Ticket/Incident verlinkt
- [ ] Lessons Learned dokumentiert

