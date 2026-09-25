// ---------------------------------------------------------------------------
// Mock data used while the backend ingestion pipeline (Sub-Task 2) is not yet
// connected. Every shape here matches the real API types in types.ts so
// swapping mock → real data requires only changing the data source.
// ---------------------------------------------------------------------------

import type { RepoSummary, FileNode, ArchComponent, ChatMessage } from './types'

export const MOCK_SUMMARY: RepoSummary = {
  repo_name: 'fastapi / fastapi',
  repo_url: 'https://github.com/fastapi/fastapi',
  description:
    'FastAPI framework, high performance, easy to learn, fast to code, ready for production.',
  primary_language: 'Python',
  languages: ['Python', 'Markdown', 'Shell'],
  frameworks: ['FastAPI', 'Pydantic', 'Starlette'],
  file_count: 312,
  dependencies: {
    'pyproject.toml': [
      'starlette',
      'pydantic',
      'uvicorn',
      'httpx',
      'anyio',
      'orjson',
      'ujson',
      'email-validator',
      'itsdangerous',
      'jinja2',
      'python-multipart',
    ],
    'requirements.txt': ['fastapi', 'uvicorn[standard]'],
    '.github/workflows/test.yml': ['pytest', 'pytest-cov', 'mypy', 'ruff'],
  },
  config_files: [
    'pyproject.toml',
    '.github/workflows/test.yml',
    'Makefile',
    '.pre-commit-config.yaml',
    '.github/workflows/publish.yml',
    'codecov.yml',
  ],
  important_files: [
    'README.md',
    'fastapi/applications.py',
    'fastapi/routing.py',
    'fastapi/params.py',
    'docs/index.md',
  ],
}

export const MOCK_FILE_TREE: FileNode = {
  name: 'fastapi',
  path: '',
  type: 'directory',
  children: [
    {
      name: 'fastapi',
      path: 'fastapi',
      type: 'directory',
      children: [
        { name: 'applications.py', path: 'fastapi/applications.py', type: 'file', language: 'Python' },
        { name: 'routing.py',      path: 'fastapi/routing.py',      type: 'file', language: 'Python' },
        { name: 'params.py',       path: 'fastapi/params.py',       type: 'file', language: 'Python' },
        { name: 'exceptions.py',   path: 'fastapi/exceptions.py',   type: 'file', language: 'Python' },
        { name: 'security',        path: 'fastapi/security',        type: 'directory', children: [
          { name: 'oauth2.py',  path: 'fastapi/security/oauth2.py',  type: 'file', language: 'Python' },
          { name: 'http.py',    path: 'fastapi/security/http.py',    type: 'file', language: 'Python' },
          { name: 'api_key.py', path: 'fastapi/security/api_key.py', type: 'file', language: 'Python' },
        ]},
        { name: 'middleware', path: 'fastapi/middleware', type: 'directory', children: [
          { name: 'cors.py', path: 'fastapi/middleware/cors.py', type: 'file', language: 'Python' },
          { name: 'gzip.py', path: 'fastapi/middleware/gzip.py', type: 'file', language: 'Python' },
        ]},
      ],
    },
    {
      name: 'tests',
      path: 'tests',
      type: 'directory',
      children: [
        { name: 'test_application.py',  path: 'tests/test_application.py',  type: 'file', language: 'Python' },
        { name: 'test_router.py',       path: 'tests/test_router.py',       type: 'file', language: 'Python' },
        { name: 'test_security.py',     path: 'tests/test_security.py',     type: 'file', language: 'Python' },
        { name: 'test_middleware.py',   path: 'tests/test_middleware.py',   type: 'file', language: 'Python' },
      ],
    },
    {
      name: 'docs',
      path: 'docs',
      type: 'directory',
      children: [
        { name: 'index.md',      path: 'docs/index.md',      type: 'file', language: 'Markdown' },
        { name: 'tutorial',      path: 'docs/tutorial',      type: 'directory', children: [
          { name: 'first-steps.md', path: 'docs/tutorial/first-steps.md', type: 'file', language: 'Markdown' },
          { name: 'routing.md',     path: 'docs/tutorial/routing.md',     type: 'file', language: 'Markdown' },
        ]},
      ],
    },
    { name: 'README.md',        path: 'README.md',        type: 'file', language: 'Markdown' },
    { name: 'pyproject.toml',   path: 'pyproject.toml',   type: 'file' },
    { name: 'requirements.txt', path: 'requirements.txt', type: 'file' },
    { name: 'Makefile',         path: 'Makefile',         type: 'file' },
  ],
}

export const MOCK_ARCH_COMPONENTS: ArchComponent[] = [
  {
    name: 'FastAPI',
    role: 'Web Framework',
    files: ['fastapi/applications.py', 'fastapi/routing.py'],
  },
  {
    name: 'Pydantic',
    role: 'Data Validation',
    files: ['fastapi/params.py'],
  },
  {
    name: 'Starlette',
    role: 'ASGI Foundation',
    files: ['fastapi/middleware/cors.py'],
  },
  {
    name: 'Pytest',
    role: 'Test Runner',
    files: ['tests/test_application.py', 'tests/test_router.py'],
  },
]

// ---------------------------------------------------------------------------
// Architecture flow layers for the enhanced project-flow view
// ---------------------------------------------------------------------------

export interface FlowLayer {
  id: string
  label: string        // e.g. "Entry Point"
  color: 'blue' | 'purple' | 'sky' | 'green' | 'orange' | 'gray'
  nodes: FlowNode[]
}

export interface FlowNode {
  name: string
  file: string
  description: string
}

export const MOCK_FLOW_LAYERS: FlowLayer[] = [
  {
    id: 'entry',
    label: 'Entry Point',
    color: 'blue',
    nodes: [
      { name: 'uvicorn', file: 'requirements.txt', description: 'ASGI server boots the app' },
    ],
  },
  {
    id: 'app',
    label: 'Application',
    color: 'sky',
    nodes: [
      { name: 'FastAPI()', file: 'fastapi/applications.py', description: 'Root app instance; mounts routers & middleware' },
    ],
  },
  {
    id: 'routing',
    label: 'Routing',
    color: 'purple',
    nodes: [
      { name: 'APIRouter', file: 'fastapi/routing.py', description: 'Registers path operations and dependencies' },
      { name: 'Path / Query', file: 'fastapi/params.py', description: 'Declares parameter types via Pydantic' },
    ],
  },
  {
    id: 'middleware',
    label: 'Middleware',
    color: 'orange',
    nodes: [
      { name: 'CORSMiddleware', file: 'fastapi/middleware/cors.py', description: 'Cross-origin request handling' },
      { name: 'GZipMiddleware', file: 'fastapi/middleware/gzip.py', description: 'Response compression' },
    ],
  },
  {
    id: 'validation',
    label: 'Validation',
    color: 'green',
    nodes: [
      { name: 'Pydantic models', file: 'fastapi/params.py', description: 'Request / response schema validation' },
    ],
  },
]

// ---------------------------------------------------------------------------
// Suggested starter questions shown in the chat empty state
// ---------------------------------------------------------------------------

export const SUGGESTED_QUESTIONS = [
  'What does the main application entry point do?',
  'How is routing structured in this project?',
  'What authentication mechanisms are supported?',
  'How does middleware work here?',
  'Which files handle request validation?',
  'What are the main dependencies and why?',
]

// ---------------------------------------------------------------------------
// Mock AI responses keyed by question keywords
// ---------------------------------------------------------------------------

interface MockResponse {
  content: string
  sources: { file_path: string; start_line: number; end_line: number }[]
}

const MOCK_RESPONSES: MockResponse[] = [
  {
    content: `## Entry Point

The main application is instantiated in \`fastapi/applications.py\`. The \`FastAPI\` class extends Starlette's \`Starlette\` class, adding automatic OpenAPI schema generation, dependency injection, and Pydantic-powered request/response validation.

\`\`\`python
app = FastAPI(
    title="My App",
    version="1.0.0",
)
\`\`\`

When uvicorn starts, it calls the ASGI callable returned by \`FastAPI.__call__\`, which delegates to Starlette's routing internals.`,
    sources: [
      { file_path: 'fastapi/applications.py', start_line: 42, end_line: 78 },
      { file_path: 'requirements.txt', start_line: 1, end_line: 2 },
    ],
  },
  {
    content: `## Routing Architecture

Routes are registered via \`APIRouter\` in \`fastapi/routing.py\`. Each router collects **path operation functions** decorated with \`@router.get\`, \`@router.post\`, etc.

The router builds a list of \`APIRoute\` objects, each holding:
- The path pattern (e.g. \`/items/{item_id}\`)
- The response model (Pydantic class)
- The dependency graph for that endpoint

Routers are included into the main app:

\`\`\`python
app.include_router(items_router, prefix="/items", tags=["items"])
\`\`\``,
    sources: [
      { file_path: 'fastapi/routing.py', start_line: 112, end_line: 165 },
      { file_path: 'fastapi/applications.py', start_line: 210, end_line: 228 },
    ],
  },
  {
    content: `## Authentication

FastAPI supports three built-in security schemes defined in \`fastapi/security/\`:

| Scheme | Class | File |
|--------|-------|------|
| OAuth2 Password Bearer | \`OAuth2PasswordBearer\` | \`security/oauth2.py\` |
| HTTP Basic / Bearer | \`HTTPBasic\`, \`HTTPBearer\` | \`security/http.py\` |
| API Key (header/cookie/query) | \`APIKeyHeader\` | \`security/api_key.py\` |

Each scheme is a **FastAPI dependency** — you declare it in a path operation's parameter list and it automatically appears in the OpenAPI security definitions.`,
    sources: [
      { file_path: 'fastapi/security/oauth2.py', start_line: 1, end_line: 45 },
      { file_path: 'fastapi/security/http.py', start_line: 1, end_line: 38 },
      { file_path: 'fastapi/security/api_key.py', start_line: 1, end_line: 30 },
    ],
  },
  {
    content: `## Middleware

Middleware is applied via \`app.add_middleware()\` or directly in the \`FastAPI\` constructor. Each middleware wraps the ASGI \`call\` chain.

**CORSMiddleware** (\`fastapi/middleware/cors.py\`) delegates to Starlette's implementation and adds:
- \`Access-Control-Allow-Origin\` headers
- Pre-flight \`OPTIONS\` handling

**GZipMiddleware** (\`fastapi/middleware/gzip.py\`) transparently compresses responses when the client sends \`Accept-Encoding: gzip\` and the response body exceeds the configured minimum size.`,
    sources: [
      { file_path: 'fastapi/middleware/cors.py', start_line: 1, end_line: 22 },
      { file_path: 'fastapi/middleware/gzip.py', start_line: 1, end_line: 18 },
    ],
  },
  {
    content: `## Request Validation

All request parameter validation flows through \`fastapi/params.py\`. Path, query, header, cookie, body, and form parameters are modelled as Pydantic \`FieldInfo\` subclasses.

When a request arrives, FastAPI:
1. Extracts raw values from the ASGI scope / body
2. Passes them through \`pydantic.validate_call\` (or a model's \`model_validate\`)
3. Raises \`RequestValidationError\` on failure, which is caught by the default exception handler and serialised as a \`422 Unprocessable Entity\` JSON response

\`\`\`python
@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = Query(default=None)):
    ...
\`\`\``,
    sources: [
      { file_path: 'fastapi/params.py', start_line: 18, end_line: 92 },
      { file_path: 'fastapi/exceptions.py', start_line: 1, end_line: 35 },
    ],
  },
  {
    content: `## Key Dependencies

| Package | Role | Source |
|---------|------|--------|
| \`starlette\` | ASGI foundation, routing, middleware | \`pyproject.toml\` |
| \`pydantic\` | Data validation and serialisation | \`pyproject.toml\` |
| \`uvicorn\` | Production ASGI server | \`requirements.txt\` |
| \`httpx\` | Async HTTP client (used in tests) | \`pyproject.toml\` |
| \`anyio\` | Async backend abstraction | \`pyproject.toml\` |

FastAPI deliberately keeps its own dependency surface minimal, relying on Starlette for all HTTP primitives and Pydantic for all data contracts.`,
    sources: [
      { file_path: 'pyproject.toml', start_line: 12, end_line: 30 },
      { file_path: 'requirements.txt', start_line: 1, end_line: 2 },
    ],
  },
]

// Round-robin index so each new question gets a different canned answer
let _responseIndex = 0

export function pickMockResponse(question: string): MockResponse {
  const q = question.toLowerCase()
  // Try keyword matching first
  if (q.includes('entry') || q.includes('main') || q.includes('application'))
    return MOCK_RESPONSES[0]
  if (q.includes('rout'))
    return MOCK_RESPONSES[1]
  if (q.includes('auth') || q.includes('oauth') || q.includes('security'))
    return MOCK_RESPONSES[2]
  if (q.includes('middleware'))
    return MOCK_RESPONSES[3]
  if (q.includes('valid') || q.includes('param') || q.includes('schema'))
    return MOCK_RESPONSES[4]
  if (q.includes('depend') || q.includes('package') || q.includes('librar'))
    return MOCK_RESPONSES[5]
  // Fallback: round-robin
  const r = MOCK_RESPONSES[_responseIndex % MOCK_RESPONSES.length]
  _responseIndex++
  return r
}

export const MOCK_INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: '1',
    role: 'assistant',
    content:
      'Repository **fastapi/fastapi** analyzed! I can answer questions about the code, architecture, and dependencies.\n\nTry one of the suggested questions below, or ask anything about the codebase.',
    sources: [],
  },
]
