import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import type { CitationSource } from '../types'

interface Props {
  role: 'user' | 'assistant'
  content: string
  sources?: CitationSource[]
  isStreaming?: boolean
}

// Language → file extension colour
const EXT_COLORS: Record<string, string> = {
  py:   'text-blue-400',
  ts:   'text-sky-400',
  tsx:  'text-sky-400',
  js:   'text-yellow-400',
  jsx:  'text-yellow-400',
  md:   'text-gray-400',
  rs:   'text-orange-400',
  go:   'text-cyan-400',
  java: 'text-red-400',
  toml: 'text-green-400',
  yaml: 'text-green-400',
  yml:  'text-green-400',
}

function fileColor(path: string) {
  const ext = path.split('.').pop() ?? ''
  return EXT_COLORS[ext] ?? 'text-gray-500'
}

export default function ChatMessage({ role, content, sources = [], isStreaming }: Props) {
  // Auto-expand sources when there are citations (first message only auto-expands)
  const [showSources, setShowSources] = useState(sources.length > 0)
  const [copied, setCopied] = useState(false)
  const isUser = role === 'user'

  function handleCopy() {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    }).catch(() => {/* clipboard not available */})
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={[
        'shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold',
        isUser ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300',
      ].join(' ')}>
        {isUser ? 'U' : 'AI'}
      </div>

      {/* Bubble + citations */}
      <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div className={[
          'rounded-2xl px-4 py-3 text-sm leading-relaxed relative group',
          isUser
            ? 'bg-blue-600 text-white rounded-tr-sm'
            : 'bg-gray-800 text-gray-100 rounded-tl-sm',
        ].join(' ')}>
          {isUser ? (
            <p>{content}</p>
          ) : (
            <>
              <div className="prose prose-sm prose-invert max-w-none
                              prose-code:bg-gray-900 prose-code:px-1.5 prose-code:py-0.5
                              prose-code:rounded prose-code:text-xs prose-pre:bg-gray-900
                              prose-pre:rounded-lg prose-pre:text-xs">
                <ReactMarkdown>{content}</ReactMarkdown>
                {isStreaming && (
                  <span className="inline-block w-1.5 h-4 bg-blue-400 ml-0.5 animate-pulse rounded-sm align-middle" />
                )}
              </div>

              {/* Copy button — visible on hover */}
              {!isStreaming && content && (
                <button
                  onClick={handleCopy}
                  title="Copy response"
                  className={[
                    'absolute top-2.5 right-2.5 p-1 rounded transition',
                    'opacity-0 group-hover:opacity-100',
                    'text-gray-500 hover:text-gray-200 hover:bg-gray-700/60',
                  ].join(' ')}
                >
                  {copied ? (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="text-green-400">
                      <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5"
                        strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                      <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.8" />
                      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"
                        stroke="currentColor" strokeWidth="1.8" />
                    </svg>
                  )}
                </button>
              )}
            </>
          )}
        </div>

        {/* Citations */}
        {!isUser && sources.length > 0 && (
          <div className="w-full">
            <button
              onClick={() => setShowSources((s) => !s)}
              className="text-xs text-gray-500 hover:text-gray-300 transition flex items-center gap-1.5 px-1 py-0.5"
            >
              <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"
                className={`transition-transform ${showSources ? 'rotate-90' : ''}`}>
                <path d="M3 2l4 3-4 3V2z" />
              </svg>
              <span>
                {sources.length} source{sources.length !== 1 ? 's' : ''}
              </span>
              <span className="text-gray-600">· click to {showSources ? 'hide' : 'view'}</span>
            </button>

            {showSources && (
              <div className="mt-1.5 space-y-1 pl-1">
                {sources.map((src, i) => (
                  <CitationCard key={i} source={src} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Citation card ─────────────────────────────────────────────────────────────

function CitationCard({ source }: { source: CitationSource }) {
  const fileName = source.file_path.split('/').pop() ?? source.file_path
  const dirName = source.file_path.includes('/')
    ? source.file_path.slice(0, source.file_path.lastIndexOf('/'))
    : ''
  const color = fileColor(source.file_path)
  const lineRange = source.start_line === source.end_line
    ? `L${source.start_line}`
    : `L${source.start_line}–${source.end_line}`

  return (
    <div className="flex items-center gap-2 text-xs font-mono bg-gray-900
                    border border-gray-700 hover:border-gray-600 rounded-lg px-3 py-2
                    transition cursor-default group/card">
      {/* File icon */}
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className={`${color} shrink-0`}>
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>

      {/* Path */}
      <span className="flex-1 min-w-0">
        {dirName && (
          <span className="text-gray-600">{dirName}/</span>
        )}
        <span className={`font-semibold ${color}`}>{fileName}</span>
      </span>

      {/* Line badge */}
      <span className="shrink-0 px-1.5 py-0.5 rounded bg-gray-800 border border-gray-700
                       text-gray-400 font-mono text-xs">
        {lineRange}
      </span>
    </div>
  )
}
