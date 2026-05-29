# Velora

Ask questions about your database in plain English. Velora connects to PostgreSQL or MongoDB, learns your schema, and answers with real SQL — no hallucinated tables or fake numbers.

```
You:  "What is the revenue per aircraft model?"
Velora: runs the query → shows a table + the SQL used
```

---

## What's in this repo

| Folder | What it is |
|--------|------------|
| **`querymind/`** | Backend (FastAPI) + UI (React). This is the app. |
| **`querymind/sample-data/`** | Demo Emirates airline database — Docker + seed SQL for testing |

All setup and docs live in **`querymind/README.md`**.

---

## Quick start (5 minutes)

You need **Docker**, **Python 3.11+**, **Node.js**, and an [NVIDIA API key](https://build.nvidia.com/models).

### 1. Platform database (Velora's own storage)

```bash
cd querymind
docker compose up -d
```

Runs Postgres + pgvector on **port 5432**.

### 2. Sample tenant database (optional — for testing chat)

```bash
cd querymind/sample-data
docker compose up -d
docker exec -i emirates-db psql -U emirates -d emirates < emirates_seed.sql
```

Runs the Emirates demo DB on **port 5435**. See [sample-data guide](querymind/sample-data/add-data.md) for DBeaver steps.

### 3. Backend

```bash
cd querymind
cp .env.example .env
# Edit .env — add NVIDIA_API_KEY and generate ENCRYPTION_KEY
pip install -r requirements.txt
./dev
```

API: http://127.0.0.1:8000

### 4. UI

```bash
cd querymind/ui-app
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

---

## Connect the sample DB in Velora

After signing up in the UI, connect this connection string:

```
postgresql://emirates:emirates123@localhost:5435/emirates
```

Then run onboarding and start chatting. Try: *"Show me all Platinum tier passengers"*.

---

## Tech stack

FastAPI · Deep Agents · NVIDIA NIM (Llama 3.3 70B) · pgvector · React · Axiom logging

---

## Full documentation

→ **[querymind/README.md](querymind/README.md)** — env vars, API flow, logging, models, troubleshooting
