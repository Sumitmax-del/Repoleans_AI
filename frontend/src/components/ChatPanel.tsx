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

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
    <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col h-full overflow-hidden">
      {/* Panel header */}
      <div className="px-4 py-3 border-b border-gray-800 shrink-0 flex items-center gap-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-blue-400 shrink-0">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Ask the Repository
        </p>
        {messages.length > 0 && (
          <span className="ml-1 text-xs text-gray-600">
            {Math.floor(messages.length / 2)} question{messages.length / 2 !== 1 ? 's' : ''}
          </span>
        )}
        {isStreaming && (
          <span className="ml-auto flex items-center gap-1.5 text-xs text-blue-400">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            Thinking…
          </span>
        )}
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Empty state — shown before any messages */}
        {showEmpty && (
          <EmptyState
            suggestedQuestions={suggestedQuestions}
            onSelect={handleSuggestion}
          />
        )}

        {/* Locked state */}
        {disabled && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" className="text-gray-700 mb-3">
              <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="1.5" />
              <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <p className="text-sm text-gray-600 italic">
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
          <SuggestedChips
            questions={suggestedQuestions}
            onSelect={handleSuggestion}
            disabled={isStreaming}
            compact
          />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-gray-800 px-4 py-3 flex gap-3 shrink-0"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={disabled || isStreaming}
          placeholder={disabled ? 'Analyze a repository first…' : 'Ask a question about this repository…'}
          className={[
            'flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2 text-sm',
            'text-gray-100 placeholder-gray-600 outline-none transition',
            'focus:border-blue-500 focus:ring-1 focus:ring-blue-500/40',
            disabled || isStreaming ? 'opacity-50 cursor-not-allowed' : '',
          ].join(' ')}
        />
        <button
          type="submit"
          disabled={disabled || isStreaming || !input.trim()}
          className={[
            'shrink-0 rounded-lg px-4 py-2 text-sm font-semibold transition',
            'flex items-center gap-2',
            'bg-blue-600 text-white hover:bg-blue-500 active:bg-blue-700',
            'disabled:opacity-40 disabled:cursor-not-allowed',
          ].join(' ')}
        >
          {isStreaming ? (
            <>
              <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              <span className="hidden sm:inline">Thinking</span>
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
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
    <div className="flex flex-col items-center justify-center h-full text-center py-8 px-4">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" className="text-gray-700 mb-4">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"
          stroke="currentColor" strokeWidth="1.5" />
        <path d="M8 10h8M8 13h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <p className="text-sm font-medium text-gray-400 mb-1">Ask anything about this repository</p>
      <p className="text-xs text-gray-600 mb-6 max-w-xs">
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
  // In compact mode show only 3 chips
  const visible = compact ? questions.slice(0, 3) : questions

  return (
    <div className={`flex flex-wrap gap-2 ${compact ? 'justify-start' : 'justify-center'}`}>
      {visible.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          disabled={disabled}
          className={[
            'text-xs rounded-full border px-3 py-1.5 text-left transition',
            'border-gray-700 bg-gray-800/60 text-gray-400',
            'hover:border-blue-600/60 hover:bg-blue-950/30 hover:text-blue-300',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            compact ? '' : 'max-w-[260px]',
          ].join(' ')}
        >
          {q}
        </button>
      ))}
    </div>
  )
}
