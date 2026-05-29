# Velora

Multi-tenant AI chat-over-data platform. Connect a PostgreSQL or MongoDB database and ask questions in natural language.

## Quick start (local)

1. `cp .env.example .env`
   - Fill in your `NVIDIA_API_KEY`
   - Generate `ENCRYPTION_KEY`:
     ```bash
     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
     ```

2. `docker-compose up -d`
   - Starts Postgres + pgvector on localhost:5432

3. `pip install -r requirements.txt`

4. `./dev` (or `python3 -m app.dev`)
   - Dev server config lives in `pyproject.toml` under `[tool.uvicorn]`
   - Auto-reloads on `.py`, `.env`, and prompt `.txt` changes
   - App reads `DATABASE_URL` from `.env` automatically

## UI app

```bash
cd ui-app
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies API calls to `http://127.0.0.1:8000`.

Run the backend first: `./dev` or `python3 -m app.dev`

## Switch to production database

Change `DATABASE_URL` in `.env` to your production Postgres URL.
Restart the app. Zero code changes needed.

## API flow — in order

1. `POST /tenants` — create account (name, email, password) → get `api_key`
2. `POST /auth/login` — sign in (email, password) → get fresh `api_key`
3. `POST /connections/{tenant_id}` — connect Postgres or MongoDB
4. `POST /onboard/{tenant_id}` — start schema indexing
5. `GET /onboard/{tenant_id}/status` — poll until `status = "active"`
6. `POST /chat/{tenant_id}` — start chatting

All endpoints except `POST /tenants` and `POST /auth/login` require the `X-API-Key` header.

## Supported databases

- PostgreSQL (any version with public schema)
- MongoDB (connection string must include database name)

## Tech stack

- **Backend:** FastAPI (Python 3.11+)
- **Agent:** Deep Agents SDK (`deepagents`)
- **LLM & Embeddings:** NVIDIA NIM via `langchain-nvidia-ai-endpoints`
- **Vector DB:** pgvector on platform Postgres
- **Logging:** Structured JSON logs via `structlog`, shipped to [Axiom](https://axiom.co) when configured

## Logging (Axiom)

All requests, API steps, agent tool calls, and onboarding stages emit structured JSON logs.

Add to `.env`:

```env
AXIOM_TOKEN=xaat-your-token-here
AXIOM_DATASET=velora
APP_ENV=production
LOG_LEVEL=INFO
```

Create the `velora` dataset in your Axiom account before starting the app. If `AXIOM_TOKEN` is unset, logs still print to stdout as JSON.

Every log includes `service`, `environment`, and (when available) `request_id` and `tenant_id`. HTTP responses include an `X-Request-ID` header for correlation.
