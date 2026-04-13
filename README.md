# IntelliMath AI (Sphinx-SCA)

Multi-page Vite frontend + FastAPI backend for an AI-powered math solver.

## Quick start (local development)

### 1) Configure environment variables

- Copy `.env.example` to `.env`
- Fill in at minimum:
  - **Frontend**: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
  - **Backend**: `GROQ_API_KEY`
  - Optional: `SCOUT_API_KEY` (enables image understanding)

### 2) Run backend (FastAPI)

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Backend health check: `GET /health`

### 3) Run frontend (Vite)

```bash
npm install
npm run dev
```

The frontend uses the dev proxy in `vite.config.js` for:
- `/solve_stream`
- `/ocr`
- `/api`

So in local dev you can leave `VITE_API_URL` empty.

## Production build

```bash
npm run build
npm run preview
```

## Deployment

### Render (recommended, already configured)

The repository includes `render.yaml` defining:
- **math-backend**: Python web service
- **math-frontend**: Static site built from Vite `dist/`

Set the required env vars in Render:
- **Backend**: `GROQ_API_KEY` (required), `SCOUT_API_KEY` (optional), `ALLOWED_ORIGINS` (recommended)
- **Frontend**: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

`VITE_API_URL` is automatically wired in `render.yaml` from the backend external URL.

## Notes

- Do not commit `.env` files. Use `.env.example` as the template.
- `dist/` is build output and should not be committed.

## Developer docs

- Mathematical output + agent best practices: `docs/AGENT_AND_OUTPUT_GUIDE.md`

