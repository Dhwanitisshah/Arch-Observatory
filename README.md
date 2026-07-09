# arch-observatory

Static code-analysis tool. FARM stack (FastAPI, React, MongoDB) monorepo skeleton.

## Structure

- `backend/` — FastAPI app, async MongoDB via motor
- `frontend/` — Vite + React SPA
- `docker-compose.yml` — MongoDB service

## Running

### 1. Start MongoDB

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
cp .env.example .env
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000. Check http://localhost:8000/health.

### 3. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend runs at http://localhost:5173.
