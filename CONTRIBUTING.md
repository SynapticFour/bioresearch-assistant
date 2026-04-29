# Beitragen — BioResearch Assistant

Danke für dein Interesse! Wir freuen uns über jeden Beitrag — Bug Reports, Feature-Ideen oder Code.

**Synaptic Four:** [www.synapticfour.com](https://www.synapticfour.com) · contact@synapticfour.com

## Verhaltenskodex

Wir folgen dem [Contributor Covenant](https://www.contributor-covenant.org/de/). Respektvoller, konstruktiver Umgang ist Pflicht.

## Wie kann ich beitragen?

### Bug Reports
1. Prüfe ob der Bug bereits gemeldet ist
2. Erstelle ein GitHub Issue mit:
   - Klarer Beschreibung
   - Schritten zur Reproduktion
   - Erwartetes vs. tatsächliches Verhalten
   - Logs (aus ./logs.sh)
   - Version (aus GET /api/v1/health)

### Feature Requests
GitHub Issue mit Label "enhancement". Bitte erkläre den Use Case — nicht nur das Feature.

### Code Beiträge

#### Setup
```bash
git clone https://github.com/SynapticFour/bioresearch-assistant.git
cd bioresearch-assistant
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

Install-/Deployment-Varianten: `docs/INSTALL.md` und `docs/deployment/README.md`.

#### Entwicklung
```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Tests
cd backend && pytest --cov=app
cd frontend && npm run type-check
```

#### Pull Request Checkliste
- [ ] Tests für neue Funktionen vorhanden
- [ ] Alle Tests grün: pytest
- [ ] TypeScript Fehler: npx tsc --noEmit
- [ ] Linting: ruff check app/
- [ ] CHANGELOG.md aktualisiert
- [ ] Dokumentation aktualisiert
- [ ] Keine Secrets im Code
- [ ] Neue Endpunkte haben Auth + Rate Limit

#### Branch Naming
- feat/beschreibung — neue Features
- fix/beschreibung — Bug Fixes
- docs/beschreibung — Dokumentation
- chore/beschreibung — Wartung

## Lizenz

Mit deinem Beitrag stimmst du zu, dass dein Code unter BUSL 1.1 lizenziert wird.
