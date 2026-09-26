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
  toml: 'text-emerald-400',
  yaml: 'text-emerald-400',
  yml:  'text-emerald-400',
}

function fileColor(path: string) {
  const ext = path.split('.').pop() ?? ''
  return EXT_COLORS[ext] ?? 'text-gray-400'
}

export default function ChatMessage({ role, content, sources = [], isStreaming }: Props) {
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
    <div className={`flex gap-3.5 animate-fade-in ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={[
        'shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shadow-md transition-transform duration-200 hover:scale-105 select-none',
        isUser
          ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-blue-500/25'
          : 'bg-gradient-to-br from-gray-800 to-gray-900 text-blue-300 border border-blue-500/20 shadow-[0_0_12px_rgba(59,130,246,0.15)]',
      ].join(' ')}>
        {isUser ? 'U' : 'AI'}
      </div>

      {/* Bubble + citations */}
      <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1.5`}>
        <div className={[
          'rounded-2xl px-4.5 py-3 text-sm leading-relaxed relative group shadow-md transition-all duration-200',
          isUser
            ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-sm shadow-blue-600/20'
            : 'bg-gray-900/90 text-gray-100 rounded-tl-sm border border-white/[0.08] shadow-black/30 backdrop-blur-md',
        ].join(' ')}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <>
              {content ? (
                <div className="prose prose-sm prose-invert max-w-none
                                prose-p:leading-relaxed prose-pre:my-2.5
                                prose-code:bg-gray-950/90 prose-code:px-2 prose-code:py-0.5
                                prose-code:rounded-md prose-code:text-xs prose-code:font-mono prose-code:border prose-code:border-white/[0.06]
                                prose-pre:bg-gray-950/95 prose-pre:border prose-pre:border-white/[0.08]
                                prose-pre:rounded-xl prose-pre:text-xs prose-pre:shadow-inner">
                  <ReactMarkdown>{content}</ReactMarkdown>
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-blue-400 ml-1 animate-pulse rounded-xs align-middle" />
                  )}
                </div>
              ) : isStreaming ? (
                <div className="flex items-center gap-1.5 py-1 text-gray-400">
                  <span className="w-2 h-2 rounded-full bg-blue-400 typing-dot-1" />
                  <span className="w-2 h-2 rounded-full bg-blue-400 typing-dot-2" />
                  <span className="w-2 h-2 rounded-full bg-blue-400 typing-dot-3" />
                </div>
              ) : null}

              {/* Copy button — visible on hover */}
              {!isStreaming && content && (
                <button
                  onClick={handleCopy}
                  title="Copy response"
                  className={[
                    'absolute top-2.5 right-2.5 p-1.5 rounded-lg transition-all duration-150',
                    'opacity-0 group-hover:opacity-100 active:scale-90',
                    'text-gray-400 hover:text-white hover:bg-gray-800/90 border border-transparent hover:border-white/[0.08]',
                    copied ? 'opacity-100 text-emerald-400 bg-gray-800/90 border-emerald-500/30' : '',
                  ].join(' ')}
                >
                  {copied ? (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="text-emerald-400">
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
          <div className="w-full animate-fade-in-fast">
            <button
              onClick={() => setShowSources((s) => !s)}
              className="text-xs text-gray-400 hover:text-gray-200 transition-colors flex items-center gap-1.5 px-1 py-0.5 group"
            >
              <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"
                className={`text-gray-500 group-hover:text-blue-400 transition-transform duration-200 ${showSources ? 'rotate-90 text-blue-400' : ''}`}>
                <path d="M3 2l4 3-4 3V2z" />
              </svg>
              <span className="font-semibold text-gray-300 group-hover:text-white transition-colors">
                {sources.length} source{sources.length !== 1 ? 's' : ''}
              </span>
              <span className="text-gray-500">· click to {showSources ? 'hide' : 'view'}</span>
            </button>

            {showSources && (
              <div className="mt-2 space-y-1.5 pl-1">
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
  const [copied, setCopied] = useState(false)
  const fileName = source.file_path.split('/').pop() ?? source.file_path
  const dirName = source.file_path.includes('/')
    ? source.file_path.slice(0, source.file_path.lastIndexOf('/'))
    : ''
  const color = fileColor(source.file_path)
  const lineRange = source.start_line === source.end_line
    ? `L${source.start_line}`
    : `L${source.start_line}–${source.end_line}`

  const citationText = `${source.file_path}:${source.start_line}-${source.end_line}`

  function handleCopyCitation(e: React.MouseEvent) {
    e.stopPropagation()
    navigator.clipboard.writeText(citationText).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }).catch(() => {})
  }

  return (
    <div
      onClick={handleCopyCitation}
      title="Click to copy citation reference"
      className="flex items-center gap-2.5 text-xs font-mono bg-gray-900/80
                 border border-white/[0.08] hover:border-blue-500/40 rounded-xl px-3.5 py-2
                 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg cursor-pointer group/card shadow-xs"
    >
      {/* File icon */}
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className={`${color} shrink-0`}>
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>

      {/* Path */}
      <span className="flex-1 min-w-0 truncate">
        {dirName && (
          <span className="text-gray-500">{dirName}/</span>
        )}
        <span className={`font-semibold ${color}`}>{fileName}</span>
      </span>

      {/* Line badge */}
      <span className="shrink-0 px-2 py-0.5 rounded-md bg-gray-950/80 border border-white/[0.06]
                       text-gray-400 font-mono text-xs group-hover/card:text-gray-300">
        {lineRange}
      </span>

      {/* Copy icon indicator */}
      <div className="shrink-0 text-gray-500 group-hover/card:text-gray-300 transition-colors">
        {copied ? (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="text-emerald-400">
            <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="opacity-60 group-hover/card:opacity-100">
            <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="2" />
            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="currentColor" strokeWidth="2" />
          </svg>
        )}
      </div>
    </div>
  )
}
