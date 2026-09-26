import { useState, useRef, useEffect, type FormEvent } from 'react'
import type { ChatMessage as ChatMessageType } from '../types'
import ChatMessageComponent from './ChatMessage'

interface Props {
  messages: ChatMessageType[]
  onSend: (question: string) => void
  isStreaming: boolean
  disabled: boolean
  suggestedQuestions?: string[]
}

export default function ChatPanel({
  messages,
  onSend,
  isStreaming,
  disabled,
  suggestedQuestions = [],
}: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest message smoothly
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const q = input.trim()
    if (!q || isStreaming || disabled) return
    onSend(q)
    setInput('')
  }

  function handleSuggestion(q: string) {
    if (isStreaming || disabled) return
    onSend(q)
  }

  const showEmpty = messages.length === 0 && !disabled

  return (
    <div className="glass-panel rounded-2xl flex flex-col h-full overflow-hidden shadow-2xl shadow-black/40 animate-fade-in relative">
      {/* Subtle top ambient gradient line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-blue-500/50 to-transparent" />

      {/* Panel header */}
      <div className="px-5 py-3.5 border-b border-white/[0.08] shrink-0 flex items-center justify-between gap-2 bg-gray-950/60 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-blue-400">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <p className="text-xs font-semibold text-gray-200 uppercase tracking-wider">
            Ask the Repository
          </p>
          {messages.length > 0 && (
            <span className="text-[11px] text-gray-400 font-mono bg-gray-900 px-2 py-0.5 rounded-full border border-white/[0.06]">
              {Math.floor(messages.length / 2)} question{messages.length / 2 !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {isStreaming && (
          <span className="flex items-center gap-2 text-xs text-blue-300 font-medium px-2.5 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/30">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-400" />
            </span>
            Thinking…
          </span>
        )}
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {/* Empty state */}
        {showEmpty && (
          <EmptyState
            suggestedQuestions={suggestedQuestions}
            onSelect={handleSuggestion}
          />
        )}

        {/* Locked state */}
        {disabled && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12 animate-fade-in">
            <div className="w-14 h-14 rounded-2xl bg-gray-900/80 border border-white/[0.08] flex items-center justify-center mb-3 text-gray-500 shadow-inner">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="1.8" />
                <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </div>
            <p className="text-sm text-gray-400 italic">
              Analyze a repository to enable the chat.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessageComponent
            key={msg.id}
            role={msg.role}
            content={msg.content}
            sources={msg.sources}
            isStreaming={msg.isStreaming}
          />
        ))}

        {/* Suggested chips below messages once conversation started */}
        {!showEmpty && !disabled && suggestedQuestions.length > 0 && (
          <div className="pt-2 animate-fade-in-fast">
            <SuggestedChips
              questions={suggestedQuestions}
              onSelect={handleSuggestion}
              disabled={isStreaming}
              compact
            />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-white/[0.08] px-4 py-3 flex gap-3 shrink-0 bg-gray-950/70 backdrop-blur-md"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={disabled || isStreaming}
          placeholder={disabled ? 'Analyze a repository first…' : 'Ask a question about this repository…'}
          className={[
            'flex-1 rounded-xl border border-white/[0.08] bg-gray-900/90 px-4 py-2.5 text-sm',
            'text-gray-100 placeholder-gray-500 outline-none transition-all duration-200',
            'focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:bg-gray-900',
            'hover:border-white/[0.15]',
            disabled || isStreaming ? 'opacity-50 cursor-not-allowed' : '',
          ].join(' ')}
        />
        <button
          type="submit"
          disabled={disabled || isStreaming || !input.trim()}
          className={[
            'shrink-0 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all duration-200',
            'flex items-center gap-2 shadow-lg select-none',
            'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500',
            'active:scale-[0.98] hover:-translate-y-0.5 hover:shadow-blue-500/30',
            'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none',
          ].join(' ')}
        >
          {isStreaming ? (
            <>
              <svg className="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              <span className="hidden sm:inline">Thinking</span>
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="transition-transform group-hover:translate-x-0.5">
                <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="hidden sm:inline">Send</span>
            </>
          )}
        </button>
      </form>
    </div>
  )
}

// ── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({
  suggestedQuestions,
  onSelect,
}: {
  suggestedQuestions: string[]
  onSelect: (q: string) => void
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-8 px-4 animate-fade-in">
      <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-4 text-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.15)]">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"
            stroke="currentColor" strokeWidth="1.8" />
          <path d="M8 10h8M8 13h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </div>
      <p className="text-base font-semibold text-white mb-1">Ask anything about this repository</p>
      <p className="text-xs text-gray-400 mb-6 max-w-xs leading-relaxed">
        Questions are answered with citations to specific files and line numbers.
      </p>
      {suggestedQuestions.length > 0 && (
        <SuggestedChips questions={suggestedQuestions} onSelect={onSelect} disabled={false} />
      )}
    </div>
  )
}

// ── Suggested question chips ─────────────────────────────────────────────────

function SuggestedChips({
  questions,
  onSelect,
  disabled,
  compact = false,
}: {
  questions: string[]
  onSelect: (q: string) => void
  disabled: boolean
  compact?: boolean
}) {
  const visible = compact ? questions.slice(0, 3) : questions

  return (
    <div className={`flex flex-wrap gap-2 ${compact ? 'justify-start' : 'justify-center'}`}>
      {visible.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          disabled={disabled}
          className={[
            'text-xs rounded-xl border px-3.5 py-2 text-left transition-all duration-200',
            'border-white/[0.08] bg-gray-900/80 text-gray-300 shadow-xs backdrop-blur-sm',
            'hover:border-blue-500/50 hover:bg-blue-500/10 hover:text-blue-200 hover:-translate-y-0.5 hover:shadow-[0_0_12px_rgba(59,130,246,0.15)]',
            'active:scale-95 active:translate-y-0',
            'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0',
            compact ? '' : 'max-w-[280px]',
          ].join(' ')}
        >
          {q}
        </button>
      ))}
    </div>
  )
}
