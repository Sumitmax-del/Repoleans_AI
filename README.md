# RepoLens

AI-powered repository understanding and developer onboarding tool.

Paste a public GitHub URL → get an instant breakdown of languages, frameworks,
dependencies, and architecture — then ask questions about the code with answers
cited to specific files and line numbers.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- `git` available on PATH

### 1. Backend

```bash
# (optional but recommended) create a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r backend/requirements.txt
```

Copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env   # then open .env and set GEMINI_API_KEY
```

Start the backend (runs on http://localhost:8000):

```bash
uvicorn backend.main:app --reload
```

Verify it is running:

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

The Vite dev server proxies all `/api` and `/health` requests to the backend
automatically — no CORS configuration needed during development.

---

## Project Structure

```
.
├── backend/
│   ├── main.py               # FastAPI application entry point
│   ├── requirements.txt
│   ├── routers/
│   │   └── health.py         # GET /health
│   ├── llm/
│   │   ├── provider.py       # LLM factory — reads LLM_PROVIDER env var
│   │   └── gemini_client.py  # Google Gemini 1.5 Flash client
│   ├── ingestion/            # Sub-Task 2: clone, scan, chunk, embed
│   └── rag/                  # Sub-Task 4: retriever, prompt builder
├── frontend/
│   ├── src/
│   │   ├── main.tsx          # React entry point
│   │   ├── App.tsx           # Root component / layout
│   │   └── api/
│   │       └── client.ts     # Typed fetch wrappers for backend endpoints
│   ├── vite.config.ts
│   └── tailwind.config.js
├── .env.example              # Copy to .env — fill in secrets
└── repolens-mvp-plan.md      # Full architecture plan and sub-task breakdown
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | No (default: `gemini`) | Which LLM backend to use |
| `GEMINI_API_KEY` | Yes (when `LLM_PROVIDER=gemini`) | Free key from [Google AI Studio](https://aistudio.google.com) |
| `VITE_API_BASE_URL` | No | Override backend URL for non-dev builds |

### Switching LLM providers

Add a new file `backend/llm/<provider>_client.py` that implements the
`stream_response(prompt: str) -> AsyncIterator[str]` interface, register it in
`backend/llm/provider.py`, then set `LLM_PROVIDER=<provider>` in `.env`.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/api/analyze` | Trigger repository ingestion *(Sub-Task 2)* |
| `GET` | `/api/summary/{repo_id}` | Detected languages, frameworks, deps *(Sub-Task 3)* |
| `GET` | `/api/structure/{repo_id}` | Nested file tree *(Sub-Task 3)* |
| `POST` | `/api/chat` | RAG chat with source citations *(Sub-Task 4)* |
