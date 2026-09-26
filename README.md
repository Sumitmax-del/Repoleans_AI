# RepoLens

AI-powered repository understanding and developer onboarding tool.

Paste a public GitHub URL → get an instant breakdown of languages, frameworks,
dependencies, and architecture — then ask questions about the code with answers
cited to specific files and line numbers.

---

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| `git` | any recent version, available on `PATH` |

### 1. Clone and configure

```bash
git clone <this-repo>
cd repolens

# Copy the example env file and fill in your values
cp .env.example .env
```

Open `.env` and set at minimum:

```
LLM_PROVIDER=echo          # works with no API key (good for first run)
# or
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your-key>  # free at https://aistudio.google.com
```

### 2. Backend

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r backend/requirements.txt
```

Start the API server (runs on http://localhost:8000):

```bash
uvicorn backend.main:app --reload
```

Verify it is running:

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

The Vite dev server automatically proxies all `/api` and `/health` requests to
the backend — no extra CORS or networking configuration needed during development.

---

## Usage

1. Paste any public GitHub repository URL (e.g. `https://github.com/tiangolo/fastapi`) into the input bar and click **Analyze**.
2. Wait for ingestion to complete — the overview, file tree, and architecture diagram populate automatically.
3. Type a question in the **Ask the Repository** panel and press **Send** (or pick a suggestion).
4. The assistant streams an answer grounded in the actual source files, with clickable file/line citations.

---

## Project Structure

```
.
├── backend/
│   ├── main.py                  # FastAPI app entry point — mounts all routers
│   ├── requirements.txt         # Pinned Python dependencies
│   ├── routers/
│   │   ├── health.py            # GET /health
│   │   ├── analyze.py           # POST /api/analyze  GET /api/summary  GET /api/structure  GET /api/analysis
│   │   └── chat.py              # POST /api/chat  (SSE streaming)
│   ├── ingestion/               # Clone → scan → metadata → pipeline orchestrator
│   │   ├── cloner.py
│   │   ├── scanner.py
│   │   ├── metadata.py
│   │   ├── validator.py
│   │   ├── pipeline.py
│   │   └── models.py            # Shared Pydantic models
│   ├── analysis/                # Static analysis — entry points, routes, arch layers
│   │   ├── engine.py
│   │   ├── entrypoints.py
│   │   ├── routes.py
│   │   ├── directories.py
│   │   └── architecture.py
│   ├── rag/                     # Retrieval-Augmented Generation layer
│   │   ├── chunker.py           # Symbol-boundary source-file chunker
│   │   ├── embedder.py          # TF-IDF (default) or sentence-transformers
│   │   ├── index.py             # Build + persist vector index
│   │   ├── retriever.py         # Semantic search → ranked RetrievalResult list
│   │   ├── prompt_builder.py    # Assemble grounded prompt + citation list
│   │   └── models.py            # Chunk, RetrievalResult, IndexMeta
│   ├── llm/
│   │   ├── provider.py          # Factory — reads LLM_PROVIDER env var
│   │   ├── echo_client.py       # Zero-dep echo provider (default, no key needed)
│   │   └── gemini_client.py     # Google Gemini 1.5 Flash streaming client
│   └── tests/
│       ├── test_ingestion.py
│       ├── test_analysis.py
│       ├── test_rag.py          # 29 RAG layer tests
│       └── test_chat.py         # 20 LLM/chat endpoint tests
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Root component — full API-connected flow
│   │   ├── types.ts             # Shared TypeScript interfaces
│   │   ├── api/
│   │   │   └── client.ts        # Typed fetch wrappers + SSE chat streaming
│   │   ├── components/          # Header, RepoInput, ChatPanel, FileExplorer, …
│   │   └── utils/
│   │       └── archUtils.ts     # Derives ArchComponent list from RepoSummary
│   ├── vite.config.ts           # Dev proxy: /api → localhost:8000
│   └── package.json
├── .env.example                 # Copy to .env — never commit .env
├── bob_sessions/                # Session screenshots from each build task
└── repolens-mvp-plan.md         # Original architecture and task breakdown
```

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | No | `echo` | LLM backend: `echo` (no key, for testing) or `gemini` |
| `GEMINI_API_KEY` | When `gemini` | — | Free key from [Google AI Studio](https://aistudio.google.com) |
| `EMBED_PROVIDER` | No | `tfidf` | Embedding backend: `tfidf` (built-in) or `sentence-transformers` |
| `EMBED_MODEL` | No | `all-MiniLM-L6-v2` | Model name when `EMBED_PROVIDER=sentence-transformers` |
| `REPOLENS_WORK_DIR` | No | system temp | Directory for cloned repos and RAG index files |
| `VITE_API_BASE_URL` | No | `""` (Vite proxy) | Override backend URL for non-dev/production builds |

### LLM providers

| Value | Package needed | Notes |
|---|---|---|
| `echo` | none | Returns a structured summary of retrieved context — great for testing the full pipeline without an API key |
| `gemini` | `google-generativeai` (see `requirements.txt`) | Gemini 1.5 Flash — free tier (15 req/min) at [aistudio.google.com](https://aistudio.google.com) |

To add a new provider: create `backend/llm/<name>_client.py` implementing `stream_response(prompt: str) -> AsyncIterator[str]`, register it in [`backend/llm/provider.py`](backend/llm/provider.py), and set `LLM_PROVIDER=<name>`.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check → `{"status":"ok","version":"0.1.0"}` |
| `POST` | `/api/analyze` | Trigger ingestion: clone → scan → embed → return `repo_id` |
| `GET` | `/api/summary/{repo_id}` | Languages, frameworks, dependencies, key files |
| `GET` | `/api/structure/{repo_id}` | Full nested file tree |
| `GET` | `/api/analysis/{repo_id}` | Architecture layers, routes, entry points |
| `POST` | `/api/chat` | SSE-streamed RAG answer with file/line citations |

### Chat SSE event format

Each `data:` line in the `/api/chat` stream is a JSON object with one of three shapes:

```jsonc
{"type": "token",  "text": "…"}          // partial LLM output
{"type": "done",   "sources": […]}        // stream complete; sources = [{file_path, start_line, end_line}]
{"type": "error",  "detail": "…"}         // recoverable error; stream closed
```

---

## Running Tests

Backend tests are short, terminating, and require no running server or network access:

```bash
# RAG layer (29 tests)
python backend/tests/test_rag.py

# LLM / chat endpoint (20 tests)
python backend/tests/test_chat.py

# Ingestion pipeline
python backend/tests/test_ingestion.py

# Static analysis
python backend/tests/test_analysis.py
```

Frontend type-check and production build:

```bash
cd frontend
npm install        # first time only
npm run build      # tsc + vite build → dist/
```

---

## Using Gemini (optional)

1. Get a free API key at https://aistudio.google.com
2. In `.env` set:
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=<your-key>
   ```
3. Install the client library:
   ```bash
   pip install google-generativeai==0.8.3
   ```

The `echo` provider works out of the box with no key and validates the entire pipeline end-to-end.
