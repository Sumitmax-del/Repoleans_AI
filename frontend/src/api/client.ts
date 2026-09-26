/**
 * Typed fetch wrappers for all RepoLens backend endpoints.
 * Base URL is intentionally empty — Vite's proxy forwards /api and /health
 * to http://localhost:8000 during development.
 * In production, set VITE_API_BASE_URL in .env.
 */

import type {
  RepoSummary,
  FileNode,
  AnalysisResult,
  CitationSource,
} from '../types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

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
// Analyze
// ---------------------------------------------------------------------------

export interface AnalyzeRequest {
  repo_url: string
}

export interface AnalyzeResponse {
  repo_id: string
  status: string
}

/** POST /api/analyze — trigger repository ingestion */
export async function analyzeRepo(body: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail ?? res.statusText).catch(() => res.statusText)
    throw new Error(String(detail))
  }
  return res.json() as Promise<AnalyzeResponse>
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

/** GET /api/summary/:repoId */
export async function fetchSummary(repoId: string): Promise<RepoSummary> {
  const res = await fetch(`${BASE}/api/summary/${encodeURIComponent(repoId)}`)
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail ?? res.statusText).catch(() => res.statusText)
    throw new Error(String(detail))
  }
  return res.json() as Promise<RepoSummary>
}

// ---------------------------------------------------------------------------
// Structure
// ---------------------------------------------------------------------------

/** GET /api/structure/:repoId */
export async function fetchStructure(repoId: string): Promise<FileNode> {
  const res = await fetch(`${BASE}/api/structure/${encodeURIComponent(repoId)}`)
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail ?? res.statusText).catch(() => res.statusText)
    throw new Error(String(detail))
  }
  return res.json() as Promise<FileNode>
}

// ---------------------------------------------------------------------------
// Analysis (architecture layers, routes, entry points)
// ---------------------------------------------------------------------------

/** GET /api/analysis/:repoId */
export async function fetchAnalysis(repoId: string): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/api/analysis/${encodeURIComponent(repoId)}`)
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail ?? res.statusText).catch(() => res.statusText)
    throw new Error(String(detail))
  }
  return res.json() as Promise<AnalysisResult>
}

// ---------------------------------------------------------------------------
// Chat — SSE streaming
// ---------------------------------------------------------------------------

export interface ChatStreamCallbacks {
  onToken: (token: string) => void
  onDone: (sources: CitationSource[]) => void
  onError: (message: string) => void
}

/**
 * POST /api/chat — streams an SSE response.
 *
 * Calls onToken for each partial text chunk, onDone when streaming completes
 * (with the deduplicated citation list), and onError on any failure.
 *
 * Returns an AbortController so the caller can cancel mid-stream.
 */
export function streamChat(
  repoId: string,
  question: string,
  callbacks: ChatStreamCallbacks,
): AbortController {
  const controller = new AbortController()

  ;(async () => {
    let res: Response
    try {
      res = await fetch(`${BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_id: repoId, question }),
        signal: controller.signal,
      })
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        callbacks.onError('Could not reach the backend. Is the server running?')
      }
      return
    }

    if (!res.ok) {
      const detail = await res.json().then((d) => d.detail ?? res.statusText).catch(() => res.statusText)
      callbacks.onError(String(detail))
      return
    }

    const reader = res.body?.getReader()
    if (!reader) {
      callbacks.onError('No response body from server.')
      return
    }

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE lines end with \n\n; process complete events from the buffer
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''   // keep the incomplete trailing part

        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue
            let event: { type: string; text?: string; sources?: CitationSource[]; detail?: string }
            try {
              event = JSON.parse(line.slice(6))
            } catch {
              continue
            }

            if (event.type === 'token' && event.text != null) {
              callbacks.onToken(event.text)
            } else if (event.type === 'done') {
              callbacks.onDone(event.sources ?? [])
            } else if (event.type === 'error') {
              callbacks.onError(event.detail ?? 'Unknown error from server.')
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        callbacks.onError('Stream interrupted unexpectedly.')
      }
    } finally {
      reader.releaseLock()
    }
  })()

  return controller
}
