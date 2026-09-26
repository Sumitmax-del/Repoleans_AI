import { useState, useMemo } from 'react'
import type { RepoSummary } from '../types'

interface Props {
  dependencies: RepoSummary['dependencies']
}

const PREVIEW_COUNT = 8

export default function DependenciesPanel({ dependencies }: Props) {
  const [search, setSearch] = useState('')
  const manifests = Object.keys(dependencies)

  // Total dep count across all manifests
  const totalCount = useMemo(
    () => manifests.reduce((s, m) => s + dependencies[m].length, 0),
    [manifests, dependencies]
  )

  if (manifests.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-6 shadow-xl shadow-black/30 animate-fade-in">
        <SectionHeader totalCount={0} search={search} onSearch={setSearch} />
        <p className="text-sm text-gray-500 italic mt-4">No dependency manifests detected.</p>
      </div>
    )
  }

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl shadow-black/30 animate-fade-in relative overflow-hidden">
      {/* Subtle top ambient gradient line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent" />

      <SectionHeader totalCount={totalCount} search={search} onSearch={setSearch} />
      <div className="space-y-4 mt-5">
        {manifests.map((manifest) => (
          <ManifestGroup
            key={manifest}
            manifest={manifest}
            deps={dependencies[manifest]}
            search={search}
          />
        ))}
      </div>
    </div>
  )
}

// ── Manifest group ───────────────────────────────────────────────────────────

function ManifestGroup({
  manifest,
  deps,
  search,
}: {
  manifest: string
  deps: string[]
  search: string
}) {
  const [expanded, setExpanded] = useState(true)
  const [showAll, setShowAll] = useState(false)
  const [copiedDep, setCopiedDep] = useState<string | null>(null)

  function handleCopyDep(dep: string) {
    navigator.clipboard.writeText(dep).then(() => {
      setCopiedDep(dep)
      setTimeout(() => setCopiedDep(null), 1500)
    }).catch(() => {})
  }

  // Filter by search
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? deps.filter((d) => d.toLowerCase().includes(q)) : deps
  }, [deps, search])

  const preview = showAll ? filtered : filtered.slice(0, PREVIEW_COUNT)
  const overflow = filtered.length - PREVIEW_COUNT

  // Highlight matching substring
  function Highlight({ text }: { text: string }) {
    const q = search.trim()
    if (!q) return <>{text}</>
    const idx = text.toLowerCase().indexOf(q.toLowerCase())
    if (idx === -1) return <>{text}</>
    return (
      <>
        {text.slice(0, idx)}
        <mark className="bg-blue-500/40 text-blue-200 rounded px-1 not-italic font-semibold">
          {text.slice(idx, idx + q.length)}
        </mark>
        {text.slice(idx + q.length)}
      </>
    )
  }

  // When searching, force expand
  const isOpen = expanded || !!search.trim()

  return (
    <div className="border border-white/[0.06] bg-gray-950/40 rounded-xl p-4 transition-all duration-200 hover:border-white/[0.12]">
      {/* Manifest header */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-2.5 w-full text-left mb-3 group select-none"
      >
        <svg
          width="10" height="10" viewBox="0 0 10 10" fill="currentColor"
          className={`text-gray-500 shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-90 text-emerald-400' : ''}`}
        >
          <path d="M3 2l4 3-4 3V2z" />
        </svg>
        <span className="text-xs font-mono font-semibold text-gray-200 group-hover:text-white transition-colors">
          {manifest}
        </span>
        <span className="text-xs text-gray-500 ml-1 font-mono">
          {search.trim() ? `${filtered.length} / ${deps.length}` : `(${deps.length})`}
        </span>
      </button>

      {isOpen && (
        <>
          {filtered.length === 0 ? (
            <p className="pl-4 text-xs text-gray-500 italic">No matches in this manifest.</p>
          ) : (
            <div className="flex flex-wrap gap-2 pl-4">
              {preview.map((dep) => {
                const isCopied = copiedDep === dep
                return (
                  <button
                    key={dep}
                    onClick={() => handleCopyDep(dep)}
                    title="Click to copy package name"
                    className={[
                      'text-xs font-mono px-3 py-1 rounded-lg border transition-all duration-150',
                      'active:scale-95 flex items-center gap-1.5 shadow-xs',
                      isCopied
                        ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.2)]'
                        : 'bg-gray-900/80 hover:bg-gray-800 text-gray-300 hover:text-white border-white/[0.08] hover:border-blue-500/40 hover:shadow-[0_0_10px_rgba(59,130,246,0.12)]',
                    ].join(' ')}
                  >
                    <span>
                      <Highlight text={dep} />
                    </span>
                    {isCopied && (
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" className="text-emerald-400">
                        <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </button>
                )
              })}
              {!showAll && overflow > 0 && (
                <button
                  onClick={() => setShowAll(true)}
                  className="text-xs px-3 py-1 rounded-lg bg-blue-500/10 border border-blue-500/30
                             text-blue-300 hover:bg-blue-500/20 hover:text-blue-200 hover:border-blue-400 transition-all duration-150 font-medium active:scale-95 shadow-xs"
                >
                  +{overflow} more
                </button>
              )}
              {showAll && overflow > 0 && (
                <button
                  onClick={() => setShowAll(false)}
                  className="text-xs px-3 py-1 rounded-lg bg-gray-900/60 border border-white/[0.08]
                             text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-all duration-150 font-medium active:scale-95 shadow-xs"
                >
                  Show less
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ── Section header ───────────────────────────────────────────────────────────

function SectionHeader({
  totalCount,
  search,
  onSearch,
}: {
  totalCount: number
  search: string
  onSearch: (v: string) => void
}) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Title */}
      <div className="flex items-center gap-2.5 mr-auto">
        <div className="w-6 h-6 rounded-lg bg-emerald-500/10 flex items-center justify-center">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-emerald-400">
            <path
              d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"
              stroke="currentColor" strokeWidth="1.8"
            />
          </svg>
        </div>
        <p className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Dependencies</p>
        {totalCount > 0 && (
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-gray-900 border border-white/[0.08] text-emerald-400 font-mono font-semibold">
            {totalCount}
          </span>
        )}
      </div>

      {/* Search input */}
      <div className="relative">
        <svg
          width="13" height="13" viewBox="0 0 24 24" fill="none"
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
        >
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Filter packages…"
          className="pl-8 pr-7 py-1.5 text-xs rounded-xl border border-white/[0.08] bg-gray-900/90
                     text-gray-200 placeholder-gray-500 outline-none transition-all duration-150
                     focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/30 w-44 focus:bg-gray-900"
        />
        {search && (
          <button
            onClick={() => onSearch('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 transition-colors"
            title="Clear filter"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}
