/**
 * Typed fetch wrappers for all RepoLens backend endpoints.
 * Base URL is intentionally empty — Vite's proxy forwards /api and /health
 * to http://localhost:8000 during development.
 * In production, set VITE_API_BASE_URL in .env.
 */

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export interface HealthResponse {
  status: string
  version: string
}

/** GET /health — liveness check */
export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json() as Promise<HealthResponse>
}

// ---------------------------------------------------------------------------
// Placeholders — implemented in Sub-Tasks 2–4
// ---------------------------------------------------------------------------

export interface AnalyzeRequest {
  repo_url: string
}

export interface AnalyzeResponse {
  repo_id: string
  status: string
}

/** POST /api/analyze — trigger repository ingestion */
export async function analyzeRepo(_body: AnalyzeRequest): Promise<AnalyzeResponse> {
  throw new Error('Not implemented yet — available after Sub-Task 2')
}

/** GET /api/summary/:repoId */
export async function fetchSummary(_repoId: string): Promise<unknown> {
  throw new Error('Not implemented yet — available after Sub-Task 3')
}

/** GET /api/structure/:repoId */
export async function fetchStructure(_repoId: string): Promise<unknown> {
  throw new Error('Not implemented yet — available after Sub-Task 3')
}
