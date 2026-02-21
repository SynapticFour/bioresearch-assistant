# BioResearch Assistant — Installation

Schritt-für-Schritt Anleitung für lokale Installation (macOS, Ubuntu, Windows).

---

## Voraussetzungen

- **Python 3.11** (explizit — **nicht** 3.12, 3.13 oder 3.14; spaCy/Abhängigkeiten)
- **Node.js 20+**
- **Docker Desktop** oder **Colima** (für PostgreSQL)
- **git**

### Colima starten (falls kein Docker Desktop)

```bash
colima start
```

### Python 3.11

- **macOS:** `brew install python@3.11`
- **Ubuntu:** `sudo apt install python3.11 python3.11-venv`
- **Windows:** [python.org](https://www.python.org/downloads/) — Version 3.11, „Add to PATH“ aktivieren

---

## 1. Repository klonen

```bash
git clone https://github.com/SynapticFour/bioresearch-assistant.git
cd bioresearch-assistant
```

---

## 2. Backend Setup

**Venv im Projektroot anlegen (nicht in `backend/`):**

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

**.env im Root anlegen** (mit allen Pflichtfeldern):

```bash
cp .env.example .env
# Mindestens: DATABASE_URL, PSEUDONYMIZATION_ENCRYPTION_KEY (64 Hex: openssl rand -hex 32)
```

**PostgreSQL starten (Bindestrich: `docker-compose`):**

```bash
docker-compose up -d postgres
```

**Migrationen:**

```bash
cd backend && alembic upgrade head && cd ..
```

**Backend starten:**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API: **http://localhost:8000** — Docs: **http://localhost:8000/docs**

---

## 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

**Optional:** `frontend/.env` anlegen:

```env
VITE_API_URL=http://localhost:8000
```

Frontend: **http://localhost:5173** (oder angezeigter Port).

---

## 4. Self-Test Befehle (korrekte Endpunkte)

**Health**

```bash
curl -s http://localhost:8000/api/v1/health
# Erwartung: {"status":"ok","service":"BioResearch Assistant API"}
```

**Literature Search**

```bash
curl -s -X POST http://localhost:8000/api/v1/literature/search \
  -H "Content-Type: application/json" \
  -d '{"query": "BRCA1", "max_results": 5, "language": "de"}'
```

**Pseudonymize (DE)**

```bash
curl -s -X POST http://localhost:8000/api/v1/pseudonymize \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient Max Mustermann, ID: P-12345", "language": "de"}'
```

**Pseudonymize (EN)**

```bash
curl -s -X POST http://localhost:8000/api/v1/pseudonymize \
  -H "Content-Type: application/json" \
  -d '{"text": "Patient John Doe, DOB: 01/01/1980", "language": "en"}'
```

**WES Service Info**

```bash
curl -s http://localhost:8000/ga4gh/wes/v1/service-info
```

**DRS Service Info**

```bash
curl -s http://localhost:8000/ga4gh/drs/v1/service-info
```

---

## 5. Häufige Probleme

- **Python 3.14 / 3.12:** Nutze **Python 3.11** (spaCy/thinc-Kompatibilität).
- **`docker compose` vs `docker-compose`:** In der Anleitung wird der **Bindestrich** verwendet (`docker-compose`); je nach System auch `docker compose` (ohne Bindestrich) möglich.
- **`.env` im Root:** Die Datei `.env` liegt im **Projektroot**, nicht in `backend/`. Backend liest sie von dort (pydantic-settings).
- **Colima:** Wenn kein Docker Desktop installiert ist: `colima start` ausführen, danach `docker-compose up -d postgres`.
- **ModuleNotFoundError (app):** Immer aus dem Verzeichnis `backend` starten (`cd backend && uvicorn app.main:app ...`) oder `PYTHONPATH` setzen.
- **PSEUDONYMIZATION_ENCRYPTION_KEY:** Muss exakt 64 Hex-Zeichen sein: `openssl rand -hex 32`.

---

## Optional: Backend mit Docker Compose

```bash
docker-compose up -d
# Backend: http://localhost:8000
# Mit Ollama: docker-compose --profile ollama up -d
```

Frontend weiterhin lokal: `cd frontend && npm run dev`.
