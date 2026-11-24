# PharmaRCA AI

AI-assisted pharmaceutical API manufacturing root-cause analysis. The project includes a React/Vite client and a FastAPI service with a LangGraph-compatible analysis pipeline, Groq support, PDF extraction, persistence, and a local demo mode.

## Quick start

1. Copy `backend/.env.example` to `backend/.env`. The default `DATABASE_URL` uses SQLite so the demo starts immediately. Use a MySQL 8 URL for production, for example `mysql+pymysql://pharmarca:password@localhost/pharmarca`.
2. In one terminal run `cd backend; python -m venv .venv; .venv\\Scripts\\activate; pip install -r requirements.txt; uvicorn app.main:app --reload --port 8000`.
3. In another terminal run `cd frontend; npm install; npm run dev`.
4. Open the address Vite prints (normally `http://localhost:5173`). Use **qa@pharmarca.local / demo123** for the preloaded QA user.

Set `GROQ_API_KEY` to enable Groq extraction. Without it, the application labels responses **Demo mode** and uses deterministic, reviewable extraction rules; no fabricated facts are added.

## API and validation

Interactive API documentation is available at `http://localhost:8000/docs`. Run backend tests with `cd backend; pytest` and frontend checks with `cd frontend; npm run build`.

## Database migrations

`alembic upgrade head` applies the initial schema when using MySQL. The app also creates the tables on startup for the out-of-box demo database.
