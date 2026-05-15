# SHL Conversational Assessment Recommender

Production-style conversational recommender for the SHL Labs AI Internship assignment. The backend exposes only:

- `GET /health`
- `POST /chat`

`POST /chat` is stateless. Every call receives the full conversation history and returns the exact evaluator schema:

```json
{
  "reply": "string",
  "recommendations": [
    {
      "name": "string",
      "url": "string",
      "test_type": "string"
    }
  ],
  "end_of_conversation": false
}
```

## Architecture

- `backend/`: FastAPI service, catalog scraper, retrieval, Gemini orchestration, validation, tests.
- `frontend/`: Next.js 15 recruiter console with Tailwind, shadcn-style components, Framer Motion, dark/light mode.
- `shared/`: API contract artifact.
- `docs/`: concise approach and deployment notes.

The system retrieves catalog rows first, validates every recommendation against scraped SHL Individual Test Solutions, then optionally asks Gemini to write the conversational reply. Gemini never creates the recommendation objects.

## Backend Quick Start

```powershell
cd backend
python -m pip install --user -r requirements.txt
copy .env.example .env
# edit GEMINI_API_KEY in .env if you want Gemini wording
python -m pytest
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Refresh catalog data:

```powershell
python scripts\scrape_catalog.py --list-only
python scripts\scrape_catalog.py --workers 6
```

Build the semantic index after installing embedding dependencies:

```powershell
python scripts\build_index.py
```

## Frontend Quick Start

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

Open `http://localhost:3000`.

## Deployment

The backend is ready for Render with `backend/render.yaml` and `backend/Dockerfile`. Set `GEMINI_API_KEY`, keep `/health` as the health check, and run the API on the platform-provided `PORT`.

For local containers:

```powershell
copy backend\.env.example backend\.env
docker compose up --build
```
