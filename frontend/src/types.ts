// ---------------------------------------------------------------------------
// Shared domain types for the RepoLens frontend.
// These mirror the shapes returned by the backend API (Sub-Tasks 2–4).
// ---------------------------------------------------------------------------

/** Shape returned by GET /health */
export interface HealthResponse {
  status: string
  version: string
}

/** Shape returned by POST /api/analyze */
export interface AnalyzeResponse {
  repo_id: string
  status: string
}

/** Shape returned by GET /api/summary/:repo_id */
export interface RepoSummary {
  repo_name: string
  repo_url: string
  description: string
  primary_language: string
  languages: string[]
  frameworks: string[]
  file_count: number
  dependencies: Record<string, string[]>   // manifest filename → list of dep names
  config_files: string[]
  important_files: string[]
}

/** A node in the file tree returned by GET /api/structure/:repo_id */
export interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  language?: string
  children?: FileNode[]
}

/** A detected architectural component (derived from summary data) */
export interface ArchComponent {
  name: string
  role: string                             // e.g. "Web Framework", "ORM", "Test Runner"
  files: string[]                          // notable files associated with this component
}

/** A single chat message in the AI chat panel */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: CitationSource[]
  isStreaming?: boolean
}

/** A source-file citation attached to an assistant answer */
export interface CitationSource {
  file_path: string
  start_line: number
  end_line: number
}

// ---------------------------------------------------------------------------
// Analysis result (from GET /api/analysis/:repo_id)
// ---------------------------------------------------------------------------

/** A node within an architecture layer */
export interface ArchNode {
  name: string
  file: string
  description: string
}

/** One layer in the architecture flow diagram */
export interface ArchLayer {
  id: string
  label: string
  color: string   // "blue" | "sky" | "purple" | "orange" | "green" | "gray" | "red" | "cyan"
  nodes: ArchNode[]
}

/** Full static analysis result from the backend */
export interface AnalysisResult {
  repo_id: string
  entry_points: { file: string; kind: string; confidence: string; reason: string }[]
  source_directories: { path: string; role: string; language: string; file_count: number }[]
  routes: { method: string; path: string; file: string; line: number; handler: string; framework: string }[]
  arch_layers: ArchLayer[]
  summary_text: string
  route_count: number
}

// ---------------------------------------------------------------------------
// App-level state machine
// ---------------------------------------------------------------------------

export type AppPhase =
  | 'idle'        // no repo entered yet
  | 'analyzing'   // POST /api/analyze in flight
  | 'ready'       // analysis done, data loaded
  | 'error'       // analysis or fetch failed
