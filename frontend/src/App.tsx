import { useState, useCallback, useEffect } from 'react'
import type { AppPhase, ChatMessage, RepoSummary, FileNode, ArchLayer, ArchComponent } from './types'
import { SUGGESTED_QUESTIONS } from './mockData'
import { buildArchComponents } from './utils/archUtils'

import {
  fetchHealth,
  analyzeRepo,
  fetchSummary,
  fetchStructure,
  fetchAnalysis,
  streamChat,
} from './api/client'

import Header from './components/Header'
import RepoInput from './components/RepoInput'
import ProjectOverview from './components/ProjectOverview'
import TechFrameworks from './components/TechFrameworks'
import FileExplorer from './components/FileExplorer'
import ArchitectureView from './components/ArchitectureView'
import DependenciesPanel from './components/DependenciesPanel'
import ChatPanel from './components/ChatPanel'
import LoadingOverlay from './components/LoadingOverlay'
import ErrorBanner from './components/ErrorBanner'

export default function App() {
  // ── Backend health ────────────────────────────────────────────────────────
  const [backendStatus, setBackendStatus] = useState<'checking' | 'ok' | 'error'>('checking')
  const [backendVersion, setBackendVersion] = useState<string>('')

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setBackendStatus('ok')
        setBackendVersion(h.version)
      })
      .catch(() => setBackendStatus('error'))
  }, [])

  // ── App phase ─────────────────────────────────────────────────────────────
  const [phase, setPhase] = useState<AppPhase>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  // ── Repository data ───────────────────────────────────────────────────────
  const [repoId, setRepoId] = useState('')
  const [summary, setSummary] = useState<RepoSummary | null>(null)
  const [fileTree, setFileTree] = useState<FileNode | null>(null)
  const [archLayers, setArchLayers] = useState<ArchLayer[]>([])
  const [archComponents, setArchComponents] = useState<ArchComponent[]>([])

  // ── Chat ──────────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  // ── Handlers ─────────────────────────────────────────────────────────────

  async function handleAnalyze(url: string) {
    setPhase('analyzing')
    setErrorMessage('')
    setMessages([])
    setSummary(null)
    setFileTree(null)
    setArchLayers([])
    setArchComponents([])

    try {
      // Step 1: trigger ingestion
      const { repo_id } = await analyzeRepo({ repo_url: url })
      setRepoId(repo_id)

      // Step 2: fetch summary + file tree + analysis in parallel
      const [sum, tree, analysis] = await Promise.all([
        fetchSummary(repo_id),
        fetchStructure(repo_id),
        fetchAnalysis(repo_id).catch(() => null),   // analysis is best-effort
      ])

      setSummary(sum)
      setFileTree(tree)

      if (analysis && analysis.arch_layers.length > 0) {
        setArchLayers(analysis.arch_layers)
      }
      setArchComponents(buildArchComponents(sum))

      // Welcome message from the repo itself
      const repoName = sum.repo_name || url.replace('https://github.com/', '')
      setMessages([{
        id: Date.now().toString(),
        role: 'assistant',
        content: `Repository **${repoName}** analyzed! I can answer questions about the code, architecture, and dependencies.\n\nTry one of the suggested questions below, or ask anything about the codebase.`,
        sources: [],
      }])

      setPhase('ready')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Analysis failed.'
      setErrorMessage(msg)
      setPhase('error')
    }
  }

  const handleChat = useCallback((question: string) => {
    if (isStreaming || !repoId) return

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
    }
    const assistantId = (Date.now() + 1).toString()
    const assistantPlaceholder: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      sources: [],
    }

    setMessages((prev) => [...prev, userMsg, assistantPlaceholder])
    setIsStreaming(true)

    streamChat(repoId, question, {
      onToken(token) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + token } : m
          )
        )
      },
      onDone(sources) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, isStreaming: false, sources }
              : m
          )
        )
        setIsStreaming(false)
      },
      onError(detail) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: m.content || `⚠️ ${detail}`,
                  isStreaming: false,
                  sources: [],
                }
              : m
          )
        )
        setIsStreaming(false)
      },
    })
  }, [isStreaming, repoId])

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="h-screen bg-gray-950 text-gray-100 flex flex-col overflow-hidden relative selection:bg-blue-600/30 selection:text-white">
      {/* Background ambient radial gradients & grid pattern */}
      <div className="absolute inset-0 bg-grid-ambient pointer-events-none opacity-40 z-0" />
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none animate-pulse-glow" />
      <div className="absolute bottom-10 right-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none animate-pulse-glow" />

      {/* Main content */}
      <div className="relative z-10 flex flex-col h-full overflow-hidden">
        <Header backendStatus={backendStatus} backendVersion={backendVersion} />

        <RepoInput onAnalyze={handleAnalyze} isLoading={phase === 'analyzing'} />

        {/* Body */}
        {phase === 'idle' && <IdleState />}
        {phase === 'analyzing' && <LoadingOverlay />}
        {phase === 'error' && (
          <ErrorBanner
            message={errorMessage}
            onRetry={() => setPhase('idle')}
          />
        )}

        {phase === 'ready' && summary && fileTree && (
          <div className="flex-1 flex overflow-hidden animate-fade-in p-3 gap-3">
            {/* Sidebar — file explorer */}
            <aside className="w-64 xl:w-72 shrink-0 overflow-hidden flex flex-col">
              <FileExplorer root={fileTree} />
            </aside>

            {/* Main scroll area */}
            <main className="flex-1 overflow-y-auto pr-1">
              <div className="max-w-4xl mx-auto space-y-5 pb-6">
                <ProjectOverview summary={summary} />
                <TechFrameworks summary={summary} />
                <ArchitectureView
                  components={archComponents}
                  flowLayers={archLayers.length > 0 ? archLayers : undefined}
                />
                <DependenciesPanel dependencies={summary.dependencies} />

                {/* Chat — fixed height */}
                <div className="h-[520px]">
                  <ChatPanel
                    messages={messages}
                    onSend={handleChat}
                    isStreaming={isStreaming}
                    disabled={false}
                    suggestedQuestions={SUGGESTED_QUESTIONS}
                  />
                </div>
              </div>
            </main>
          </div>
        )}
      </div>
    </div>
  )
}

function IdleState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-6 py-16 animate-fade-in relative z-10">
      {/* Floating hero icon with glowing backdrop */}
      <div className="relative mb-6 flex items-center justify-center group cursor-default">
        <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-2xl animate-pulse-glow" />
        <div className="relative w-20 h-20 rounded-2xl bg-gray-900/80 border border-white/[0.1] flex items-center justify-center shadow-2xl backdrop-blur-xl transition-all duration-300 group-hover:scale-105 group-hover:border-blue-400/40">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" className="text-blue-400 drop-shadow-[0_0_15px_rgba(96,165,250,0.5)]">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
            <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="11" cy="11" r="3" fill="currentColor" opacity="0.3" />
          </svg>
        </div>
      </div>

      <h2 className="text-2xl font-bold bg-gradient-to-r from-white via-gray-100 to-gray-400 bg-clip-text text-transparent mb-2.5 tracking-tight">
        Understand any repository instantly
      </h2>
      <p className="text-sm text-gray-400 max-w-md leading-relaxed">
        Paste a public GitHub URL above. RepoLens will analyze the code, detect
        languages and frameworks, map the architecture, and let you ask questions
        with answers cited to specific files and lines.
      </p>

      {/* Feature cards */}
      <div className="mt-9 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl w-full">
        {[
          { icon: '🔍', label: 'Language & framework detection' },
          { icon: '🗂️', label: 'File tree exploration' },
          { icon: '💬', label: 'AI chat with source citations' },
        ].map((f) => (
          <div
            key={f.label}
            className="glass-card rounded-2xl px-5 py-4 text-sm text-gray-300 shadow-lg cursor-default group"
          >
            <span className="block text-2xl mb-2 transition-transform duration-200 group-hover:scale-110">{f.icon}</span>
            <span className="font-medium text-gray-300 group-hover:text-white transition-colors">{f.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
