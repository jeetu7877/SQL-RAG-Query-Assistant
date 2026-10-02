# PostgreSQL Text-to-SQL AI Assistant

Connect **any** PostgreSQL database with a connection URL, inspect its schema, and ask questions in plain
English. The app generates PostgreSQL with **Vanna + Google Gemini**, validates it with **SQLGlot**, runs it
**read-only**, and shows the answer, the SQL, and the result table.

PostgreSQL only. No MongoDB/MySQL/SQLite, no LangGraph, no hand-rolled RAG pipeline.

## Features

- Dynamic connection from a `postgresql://` URL (passwords never returned to the browser or sent to Gemini)
- Dynamic schema inspection: tables, columns, types, nullability, defaults, PKs, FKs, relationships, indexes
- Dedicated Schema page with search, expand/collapse, relationships list, loading/empty/error states
- Natural language to SQL (one Gemini call per question), SQL syntax highlighting and copy button
- Read-only enforcement in three layers (see Security), row limit, query timeout
- Deterministic answer formatter (no second Gemini call, saves quota)
- Dark dashboard UI with orange accent, responsive

## Architecture

```
User question
   -> FastAPI  (X-Connection-ID header)
   -> Connection Manager   (engine looked up server-side)
   -> Schema Inspector     (cached; DDL only, no row data)
   -> Vanna (per-schema ChromaDB store) + Gemini  -> PostgreSQL SQL
   -> SQLGlot validator    (AST, single read-only statement, LIMIT applied)
   -> PostgreSQL           (READ ONLY transaction + statement_timeout)
   -> Answer formatter
   -> React UI
```

## Tech stack

| Layer    | Tools |
|----------|-------|
| Frontend | React 18, Vite, Tailwind CSS 3, Lucide React, Axios, React Router |
| Backend  | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, psycopg 3 |
| AI       | Vanna **0.7.9** (legacy API), ChromaDB 0.6.3, Google Gemini (`google-genai`) |
| Security | SQLGlot (PostgreSQL dialect) |

## Project structure

```
pg-text2sql/
├── backend/
│   ├── app/
│   │   ├── api/        chat.py, database.py, health.py, deps.py
│   │   ├── ai/         vanna_service.py, answer_service.py
│   │   ├── database/   connection_manager.py, schema_inspector.py, query_executor.py
│   │   ├── security/   sql_validator.py
│   │   ├── models/     database.py, chat.py
│   │   ├── core/       config.py
│   │   └── main.py
│   ├── tests/          validator, connection manager, schema, read-only, chat, Vanna, answers
│   ├── requirements.txt / requirements-dev.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   └── src/ components/ pages/ services/ context/ App.jsx main.jsx index.css
├── docker/init.sql         sample company_db data
├── docker-compose.yml      optional sample PostgreSQL
└── README.md
```

## Installation

Requirements: Python 3.11+, Node 18+, and a Google AI Studio API key.

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env

# Frontend
cd ../frontend
npm install
cp .env.example .env               # optional; defaults to http://localhost:8000
```

## Environment variables

Backend `.env`:

```
GOOGLE_API_KEY=            # required, from https://aistudio.google.com/apikey
GEMINI_MODEL=gemini-2.0-flash   # set to any Gemini model your key supports
FRONTEND_URL=http://localhost:5173
MAX_RESULT_ROWS=100
QUERY_TIMEOUT_SECONDS=10
```

Frontend `.env`: `VITE_API_URL=http://localhost:8000`

> If Gemini returns "model not found", change `GEMINI_MODEL` to a model listed for your key.

## Running

```bash
# Backend (from backend/)
uvicorn app.main:app --reload --port 8000

# Frontend (from frontend/)
npm run dev        # http://localhost:5173
```

**First question note:** ChromaDB's default embedding model (ONNX MiniLM, ~80 MB) downloads once on first use,
so the first question after a fresh install needs internet access and takes a bit longer.

## Optional sample database (Docker)

```bash
docker compose up -d       # PostgreSQL 16 with company_db
docker compose down -v     # stop and delete data
```

Tables: `customers`, `orders`, `order_items`, `products`, `employees` with realistic foreign keys.
The app does not depend on it; connect any PostgreSQL database you like.

## Connecting PostgreSQL

Example URL for the sample database:

```
postgresql://postgres:password123@localhost:5432/company_db
```

Open http://localhost:5173, paste the URL, click **Connect database**. For real data, create a read-only role:

```sql
CREATE ROLE assistant_ro LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE mydb TO assistant_ro;
GRANT USAGE ON SCHEMA public TO assistant_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO assistant_ro;
```

Only the `public` schema is inspected.

## Example questions

- How many customers are there?
- Show the top 5 customers by total order value.
- How many orders were placed last month?
- Which product category generates the most revenue?
- List employees hired after 2020 ordered by salary.

Example result:

```
Question:  How many customers are there?
SQL:       SELECT COUNT(*) AS customer_count FROM customers
Answer:    There are 60 customers.
```

## Security

1. **SQLGlot validation** (`security/sql_validator.py`): parsed with the PostgreSQL dialect; exactly one
   statement; root must be SELECT/UNION (CTEs allowed); AST walk rejects INSERT/UPDATE/DELETE/MERGE, DDL, COPY,
   GRANT/REVOKE, CALL/DO, transaction commands, `SELECT INTO`, `FOR UPDATE`, and dangerous functions
   (`pg_sleep`, `pg_read_file`, `dblink`, `set_config`, ...). Data-modifying CTEs are caught too.
2. **Read-only transaction + timeout**: every query runs in `BEGIN READ ONLY` with `statement_timeout`,
   so PostgreSQL itself refuses writes even if validation were bypassed (tested).
3. **Result cap**: `LIMIT` is added or lowered to `MAX_RESULT_ROWS`; single-row aggregates are untouched.
4. **Secrets**: DB URL/password stay server-side, are never logged, never returned, never sent to Gemini.
   Gemini only receives the question and table DDL. The browser keeps only a session ID in `sessionStorage`.
5. **Sanitized errors**: no stack traces, credentials or connection details in responses.
6. **Isolation**: one Vanna/Chroma store per schema fingerprint; different databases never share embeddings.
7. **CORS**: restricted to `FRONTEND_URL` (+ localhost:5173 for dev), no wildcard.
8. Sessions expire after 60 minutes of inactivity and engines are disposed on disconnect/expiry.

Known limits: sessions are in memory (single worker; restart = reconnect), and there is no user login.
Add authentication and HTTPS before exposing this to the internet.

## Deployment

- Backend: `docker build -t pg-text2sql-api backend && docker run -p 8000:8000 --env-file backend/.env pg-text2sql-api`
  (run a single worker; mount a volume at `/srv/.vanna_data` to keep the embedding cache)
- Frontend: `VITE_API_URL=https://api.example.com npm run build`, then serve `frontend/dist` from any static host.
- Set `FRONTEND_URL` on the backend to the exact frontend origin. Serve both over HTTPS.

## API documentation

Interactive docs at http://localhost:8000/docs.

| Method | Path | Notes |
|--------|------|-------|
| GET  | `/api/health` | `{"status":"ok"}` |
| POST | `/api/database/connect` | body `{"database_url": "postgresql://..."}` -> `connection_id`, `database_name`, `host`, `status` |
| POST | `/api/database/disconnect` | header `X-Connection-ID` |
| GET  | `/api/database/schema` | header `X-Connection-ID`; optional `?refresh=true` |
| POST | `/api/chat` | header `X-Connection-ID`; body `{"question": "..."}` |

Chat response:

```json
{
  "answer": "There are 60 customers.",
  "sql": "SELECT\n  COUNT(*) AS customer_count\nFROM customers",
  "columns": ["customer_count"],
  "rows": [[60]],
  "row_count": 1,
  "truncated": false,
  "execution_time_ms": 1.8
}
```

Status codes: 400 bad connection/execution, 401 missing/expired session, 422 SQL failed validation,
429 Gemini quota exceeded, 503 AI service unavailable.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest                                   # DB-free tests only (DB tests are skipped)
TEST_DATABASE_URL=postgresql://postgres:password123@localhost:5432/company_db pytest   # all tests
```

Use the sample database for `TEST_DATABASE_URL`; the DB tests expect its tables and data.

## Version and compatibility notes

- **Vanna 0.7.9 (legacy `VannaBase` API) is used throughout.** Vanna 2.x is a different, agent-based API and
  is not mixed in.
- Vanna's bundled `GoogleGeminiChat` lives in a package that imports the Vertex AI SDK at import time, and it
  uses the deprecated `google-generativeai`. This project ships a ~20 line Gemini adapter on the current
  `google-genai` SDK instead.
- Vanna's ChromaDB store uses fixed collection names, so isolation is done with one Chroma folder per schema
  fingerprint rather than shared collections.
- psycopg 3 is forced via `postgresql+psycopg://`. Queries run through the raw cursor so `%` and `:` inside
  generated SQL are never treated as bind parameters.
