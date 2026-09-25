# RepoLens MVP — Architecture & Build Plan

## Overview

RepoLens is an AI-powered repository understanding tool built for a hackathon demo.
Users paste a public GitHub repository URL, the system clones and analyses the repo, then
serves a chat interface where questions are answered with citations to specific files and
line numbers.

### Scope
- Public GitHub repositories only
- Localhost deployment (no cloud infra required)
- Python (FastAPI) backend + React frontend
- LLM provider is configurable via environment variables (default: Google Gemini 1.5 Flash free tier)
- Local disk storage only — no database server required
- Chat answers with file + line-number citations; no inline code preview

### Non-Goals (MVP)
- Private repository support / OAuth
- Real-time collaboration
- Persistent multi-user accounts
- CI/CD pipelines or production hardening
- Inline file content preview panel

---

## Recommended Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | React + Vite + TailwindCSS | Fast scaffold, minimal boilerplate |
| Backend | Python 3.11 + FastAPI | Team comfort, async support, great DX |
| AI Provider | Google Gemini 1.5 Flash (default) | Generous free tier — 15 req/min, 1 M token context; swappable via `LLM_PROVIDER` env var |
| Embeddings | `sentence-transformers` (local) | Zero cost, runs on CPU, no API calls |
| Vector store | ChromaDB (in-process) | Zero-infra, persists to disk, Python-native |
| Repo cloning | `subprocess git clone` | Simple, no API rate limits |
| Code parsing | `pygments` + `ast` (Python files) | Language detection + symbol extraction |
| Dep detection | File-pattern matching | `package.json`, `requirements.txt`, `Cargo.toml`, etc. |

---

## Architecture Diagram

```
Browser (React)
    │  REST + SSE
    ▼
FastAPI Backend
    ├── POST /api/analyze   → Ingestion Pipeline
    │       ├── git clone (temp dir)
    │       ├── File scanner (languages, deps, config files)
    │       ├── Chunk + embed all code files
    │       └── Store chunks in ChromaDB collection keyed by repo URL
    │
    ├── GET  /api/structure  → Return file tree JSON
    ├── GET  /api/summary    → Return detected metadata (langs, frameworks, deps)
    └── POST /api/chat       → RAG Query
            ├── Embed user question
            ├── Top-K vector search in ChromaDB
            ├── Build prompt with retrieved chunks + citations
            └── Stream Gemini response back to browser
```

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffolding

**Status:** `[x] done`

**Intent**
Stand up the monorepo skeleton with a working dev server on both frontend and backend
so all subsequent sub-tasks have a clear place to land.

**Expected Outcomes**
- `backend/` directory with FastAPI app that returns `{"status": "ok"}` from `GET /health`
- `frontend/` directory with Vite + React + Tailwind that renders a placeholder page
- A single `README.md` documenting how to run both servers
- Dependencies pinned in `backend/requirements.txt` and `frontend/package.json`

**Todo List**
1. Create `backend/` with `main.py`, `requirements.txt`, and a `routers/` package
2. Pin dependencies: FastAPI, uvicorn, python-dotenv, chromadb, sentence-transformers, google-generativeai, pygments
3. Create `backend/llm/provider.py` — factory that reads `LLM_PROVIDER` env var and returns the correct client (initially only `gemini` implemented; designed for easy extension)
4. Create `frontend/` via `npm create vite@latest` with React + TypeScript template
5. Install Tailwind CSS and configure `tailwind.config.js`
6. Add root-level `README.md` with `Running locally` instructions including how to set `LLM_PROVIDER` and `GEMINI_API_KEY`
7. Verify `uvicorn backend.main:app --reload` and `npm run dev` both start cleanly

**Relevant Context**
- No existing code in workspace — greenfield
- Backend entry point: `backend/main.py`
- Frontend entry point: `frontend/src/main.tsx`

---

### Sub-Task 2 — Repository Ingestion Pipeline

**Status:** `[ ] pending`

**Intent**
Build the backend pipeline that accepts a GitHub URL, clones the repo to a temporary
directory, scans every file, and stores structured metadata (language map, dependency
files, config files, important files, file tree) plus embedded code chunks in ChromaDB.

**Expected Outcomes**
- `POST /api/analyze` accepts `{ "repo_url": "https://github.com/owner/repo" }` and returns a `repo_id` (SHA of the URL)
- Cloned repo is deleted from disk after embedding is complete (temp dir cleanup)
- ChromaDB collection named by `repo_id` persists to `./chroma_store/`
- Metadata document stored in ChromaDB with detected languages, frameworks, deps, config files
- File tree stored as a JSON artifact in `./repo_store/{repo_id}/tree.json`

**Todo List**
1. Create `backend/routers/analyze.py` with the `POST /api/analyze` endpoint
2. Create `backend/ingestion/cloner.py` — wraps `git clone --depth 1` into a temp directory; returns path
3. Create `backend/ingestion/scanner.py` — walks directory tree, skips `.git/`, `node_modules/`, `__pycache__/`, binary files; returns file tree dict and categorised file lists
4. Create `backend/ingestion/detector.py` — maps file extensions to languages; detects framework signals (e.g., `next.config.js` → Next.js, `manage.py` → Django); lists all dependency manifests found
5. Create `backend/ingestion/chunker.py` — reads each text file, splits into overlapping chunks of ~400 tokens, attaches metadata `{repo_id, file_path, start_line, end_line, language}`
6. Create `backend/ingestion/embedder.py` — loads `all-MiniLM-L6-v2` from sentence-transformers, embeds chunks in batches, upserts into ChromaDB collection
7. Wire all steps into an `ingest(repo_url)` orchestrator function called by the endpoint
8. Persist `tree.json` and a `meta.json` (detected summary) to `./repo_store/{repo_id}/`
9. Clean up the cloned temp directory after all embedding is done

**Relevant Context**
- Files to skip: `.git`, `node_modules`, `vendor`, `__pycache__`, `.venv`, build output dirs
- Binary detection: skip files where `open(f, 'rb').read(512)` contains null bytes
- Chunk overlap: 50 tokens to preserve context across boundaries
- `all-MiniLM-L6-v2` model is ~80 MB, downloads once and caches automatically

---

### Sub-Task 3 — Analysis & Structure API Endpoints

**Status:** `[ ] pending`

**Intent**
Expose the stored metadata (file tree, language/framework summary, dependency list,
notable files) through REST endpoints so the frontend can display them without
re-running analysis.

**Expected Outcomes**
- `GET /api/structure/{repo_id}` returns the full nested file tree JSON
- `GET /api/summary/{repo_id}` returns detected languages, frameworks, dependencies, config files, and a list of "important" files (README, entry points, CI files)
- Both endpoints return a 404 with a clear error message if `repo_id` is unknown
- Responses are JSON and can be consumed directly by the React frontend

**Todo List**
1. Create `backend/routers/repo.py` with both GET endpoints
2. Load `tree.json` and `meta.json` from `./repo_store/{repo_id}/` for each response
3. Define Pydantic response models for `StructureResponse` and `SummaryResponse`
4. Register the router in `main.py` with prefix `/api`
5. Enable CORS in `main.py` for `http://localhost:5173` (Vite dev server)

**Relevant Context**
- `repo_id` = `hashlib.sha256(repo_url.encode()).hexdigest()[:16]`
- `meta.json` schema: `{ languages: [], frameworks: [], dependencies: {}, config_files: [], important_files: [] }`

---

### Sub-Task 4 — RAG Chat Endpoint

**Status:** `[ ] pending`

**Intent**
Build the `/api/chat` endpoint that takes a user question, retrieves the most relevant
code chunks from ChromaDB, constructs a grounded prompt, calls the configured LLM provider,
and streams the answer back to the browser with file/line citations.

**Expected Outcomes**
- `POST /api/chat` accepts `{ "repo_id": "...", "question": "..." }` and streams a response
- Each streamed response includes the answer text and a `sources` array of `{ file_path, start_line, end_line }` objects
- Answers are grounded in retrieved code chunks — the prompt instructs the model not to speculate beyond the provided context
- The LLM call is routed through `backend/llm/provider.py` so the provider can be swapped by changing `LLM_PROVIDER` in `.env`
- Default provider is Gemini 1.5 Flash with a prompt that includes up to 5 retrieved chunks

**Todo List**
1. Create `backend/routers/chat.py` with `POST /api/chat`
2. Create `backend/rag/retriever.py` — embeds the question, queries ChromaDB top-5 by cosine similarity, returns chunks with their metadata
3. Create `backend/rag/prompt_builder.py` — assembles system prompt + context block with each chunk labelled by `file_path:start_line-end_line`, then appends the user question
4. Create `backend/llm/gemini_client.py` — thin wrapper around `google.generativeai.GenerativeModel("gemini-1.5-flash")` with streaming enabled
5. Update `backend/llm/provider.py` to wire the Gemini client and expose a single `stream_response(prompt: str)` interface
6. Stream the LLM response back as `text/event-stream` (SSE); attach deduplicated `sources` in the final SSE event
7. Store all secrets in `.env` (`LLM_PROVIDER`, `GEMINI_API_KEY`); load via `python-dotenv`; add `.env` to `.gitignore`

**Relevant Context**
- Gemini 1.5 Flash free tier: 15 requests/minute, 1 M tokens/request — sufficient for a hackathon demo; no API key needed to start (obtain free from Google AI Studio)
- `LLM_PROVIDER` env var controls which client `provider.py` instantiates; only `gemini` is implemented for the MVP
- System prompt must contain: "Answer only using the code context provided. Cite the file and line range for each claim."
- ChromaDB query: `collection.query(query_embeddings=[...], n_results=5, include=["documents","metadatas"])`

---

### Sub-Task 5 — Frontend: Repository Input & Analysis View

**Status:** `[ ] pending`

**Intent**
Build the main frontend page where users enter a GitHub URL, trigger analysis, and
see the repository summary (languages, frameworks, dependencies) and file tree once
analysis is complete.

**Expected Outcomes**
- A single-page app with a URL input field and an "Analyze" button
- While analysis is running, a loading indicator is shown
- After analysis, the page shows: detected languages (badges), frameworks, dependency files found, and a collapsible file tree
- State is managed with React hooks (no Redux or Zustand needed for MVP)

**Todo List**
1. Create `frontend/src/components/RepoInput.tsx` — controlled input + submit button
2. Create `frontend/src/api/client.ts` — typed fetch wrappers for all backend endpoints
3. Create `frontend/src/components/SummaryPanel.tsx` — displays language badges, framework tags, dependency manifest names
4. Create `frontend/src/components/FileTree.tsx` — recursive component rendering the nested tree JSON; each node is collapsible
5. Create `frontend/src/App.tsx` — orchestrates state: `idle → analyzing → ready`; renders all panels
6. Add basic Tailwind layout: sidebar for file tree, main area for summary + chat

**Relevant Context**
- Backend base URL: `http://localhost:8000`
- Analysis is triggered by `POST /api/analyze`; then `GET /api/summary/{repo_id}` and `GET /api/structure/{repo_id}` are called once the repo_id is returned

---

### Sub-Task 6 — Frontend: AI Chat Interface

**Status:** `[ ] pending`

**Intent**
Add the chat panel to the frontend that streams AI answers about the repository and
displays cited source files with line numbers users can reference.

**Expected Outcomes**
- A chat panel with a message history, a text input, and a send button
- User messages appear immediately; AI response streams in token-by-token
- Each AI message shows a collapsible "Sources" section listing `file_path:start_line-end_line`
- Chat history persists in component state for the session (no backend persistence needed for MVP)

**Todo List**
1. Create `frontend/src/components/ChatPanel.tsx` — message list + input area
2. Create `frontend/src/components/ChatMessage.tsx` — renders a single message; if role is `assistant`, renders markdown and a collapsible sources block
3. Add SSE streaming consumer in `client.ts` using the browser `EventSource` API or `fetch` with `ReadableStream`
4. Wire `ChatPanel` into `App.tsx` alongside the summary and file tree panels
5. Test end-to-end: ask "What does this repo do?", verify streamed answer with citations

**Relevant Context**
- Backend streams as `text/event-stream`; final event contains `{ "sources": [...] }`
- Use a simple markdown renderer (`react-markdown`) to format code blocks in answers

---

## API Endpoint Reference

| Method | Path | Request Body | Response |
|---|---|---|---|
| POST | `/api/analyze` | `{ repo_url }` | `{ repo_id, status }` |
| GET | `/api/structure/{repo_id}` | — | File tree JSON |
| GET | `/api/summary/{repo_id}` | — | Languages, frameworks, deps |
| POST | `/api/chat` | `{ repo_id, question }` | SSE stream |
| GET | `/health` | — | `{ status: "ok" }` |

---

## Data & Storage

```
./chroma_store/         ← ChromaDB vector collections (one per repo_id)
./repo_store/
    {repo_id}/
        tree.json       ← file tree
        meta.json       ← detected summary
.env                    ← LLM_PROVIDER, GEMINI_API_KEY (never committed)
.gitignore              ← must include .env, chroma_store/, repo_store/
```

No database server required. Everything persists to local directories.
Chat history is session-only (React component state); nothing is written to disk for conversations.

---

## Security Considerations (MVP / Localhost)

| Risk | Mitigation |
|---|---|
| Arbitrary `git clone` of attacker-controlled URL | Validate URL matches `github.com` pattern before cloning; reject other hosts |
| Cloned repo containing malicious scripts | Never execute any file from the cloned repo; read-only file access only |
| API key exposure | Store in `.env`, add `.env` to `.gitignore` immediately |
| Runaway large repos consuming disk | Set a file count cap (e.g. 5000 files) and repo size cap (e.g. 100 MB) during scanning |
| Path traversal in file tree | Resolve all paths relative to the clone root; reject any `..` components |

---

## Development Sequence

Build sub-tasks in this order — each produces a testable vertical slice:

1. **Scaffolding** — both servers run, health endpoint responds
2. **Ingestion Pipeline** — `POST /api/analyze` clones, scans, embeds a real repo
3. **Structure & Summary APIs** — verify stored data is retrievable via HTTP
4. **RAG Chat Endpoint** — test with `curl`; verify citations appear in response
5. **Frontend Analysis View** — connect to working backend, see real repo metadata
6. **Frontend Chat** — end-to-end demo flow is complete

---

## Open Decisions / Notes

- **API key**: Gemini 1.5 Flash is the default LLM. Obtain a free key from [Google AI Studio](https://aistudio.google.com). Set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=<your-key>` in `.env`.
- **Switching LLM providers**: To use a different provider later, implement a new client in `backend/llm/` with the same `stream_response(prompt: str)` interface and update `LLM_PROVIDER` in `.env`. No other code changes are required.
- **Chunk size**: 400 tokens is a starting point; tune down if context quality is poor.
- **Model warming**: `all-MiniLM-L6-v2` downloads on first run (~80 MB, ~10 s); subsequent runs use the local cache automatically.
- **Large repos**: A `max_files=500` guard in the scanner keeps demo analysis fast for very large monorepos.
- **No inline code preview**: File content browsing is out of scope for MVP. Citations in chat answers (file path + line range) are the only code-navigation affordance.
