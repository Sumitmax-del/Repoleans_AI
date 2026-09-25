import { useState, useCallback } from 'react'
import type { AppPhase, ChatMessage } from './types'
import {
  MOCK_SUMMARY,
  MOCK_FILE_TREE,
  MOCK_ARCH_COMPONENTS,
  MOCK_FLOW_LAYERS,
  MOCK_INITIAL_MESSAGES,
  SUGGESTED_QUESTIONS,
  pickMockResponse,
} from './mockData'

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
  // ── App phase ─────────────────────────────────────────────────────────────
  const [phase, setPhase] = useState<AppPhase>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  // ── Chat ──────────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  // ── Handlers ─────────────────────────────────────────────────────────────

  function handleAnalyze(url: string) {
    setPhase('analyzing')
    setErrorMessage('')
    setMessages([])

    setTimeout(() => {
      try {
        const parsed = new URL(url)
        if (parsed.hostname !== 'github.com') throw new Error('Only github.com is supported.')
      } catch (e) {
        setErrorMessage(e instanceof Error ? e.message : 'Invalid URL')
        setPhase('error')
        return
      }

      setMessages(MOCK_INITIAL_MESSAGES)
      setPhase('ready')
    }, 1800)
  }

  // Simulated streaming: adds the user message immediately, then types out
  // the assistant response word-by-word with a short delay between tokens.
  const handleChat = useCallback((question: string) => {
    if (isStreaming) return

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

    const { content, sources } = pickMockResponse(question)
    // Split by word boundaries, preserving spaces so re-join looks right
    const tokens = content.match(/\S+\s*/g) ?? [content]

    let accumulated = ''
    let i = 0

    function tick() {
      if (i >= tokens.length) {
        // Done — finalise the message with sources and stop streaming
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: accumulated, isStreaming: false, sources }
              : m
          )
        )
        setIsStreaming(false)
        return
      }

      accumulated += tokens[i]
      i++

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: accumulated } : m
        )
      )

      // Vary the interval slightly to feel more natural
      const delay = 18 + Math.random() * 22
      setTimeout(tick, delay)
    }

    // Small initial delay before "typing" starts
    setTimeout(tick, 320)
  }, [isStreaming])

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="h-screen bg-gray-950 text-gray-100 flex flex-col overflow-hidden">
      <Header backendStatus="ok" backendVersion="mock" />

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

      {phase === 'ready' && (
        <div className="flex-1 flex overflow-hidden">
          {/* Sidebar — file explorer */}
          <aside className="w-64 xl:w-72 shrink-0 border-r border-gray-800 overflow-hidden flex flex-col">
            <FileExplorer root={MOCK_FILE_TREE} />
          </aside>

          {/* Main scroll area */}
          <main className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">
              <ProjectOverview summary={MOCK_SUMMARY} />
              <TechFrameworks summary={MOCK_SUMMARY} />
              <ArchitectureView
                components={MOCK_ARCH_COMPONENTS}
                flowLayers={MOCK_FLOW_LAYERS}
              />
              <DependenciesPanel dependencies={MOCK_SUMMARY.dependencies} />

              {/* Chat — fixed height so it doesn't push everything out */}
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
  )
}

function IdleState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-6 py-16">
      {/* Hero icon */}
      <svg width="56" height="56" viewBox="0 0 24 24" fill="none" className="text-gray-700 mb-6">
        <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.5" />
        <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="11" cy="11" r="3" fill="currentColor" opacity="0.25" />
      </svg>
      <h2 className="text-xl font-semibold text-gray-300 mb-2">
        Understand any repository instantly
      </h2>
      <p className="text-sm text-gray-500 max-w-sm leading-relaxed">
        Paste a public GitHub URL above. RepoLens will analyze the code, detect
        languages and frameworks, map the architecture, and let you ask questions
        with answers cited to specific files and lines.
      </p>
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-lg w-full">
        {[
          { icon: '🔍', label: 'Language & framework detection' },
          { icon: '🗂️', label: 'File tree exploration' },
          { icon: '💬', label: 'AI chat with source citations' },
        ].map((f) => (
          <div
            key={f.label}
            className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-400"
          >
            <span className="block text-xl mb-1">{f.icon}</span>
            {f.label}
          </div>
        ))}
      </div>
    </div>
  )
}
