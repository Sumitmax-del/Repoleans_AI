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
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <SectionHeader totalCount={0} search={search} onSearch={setSearch} />
        <p className="text-sm text-gray-500 italic mt-4">No dependency manifests detected.</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <SectionHeader totalCount={totalCount} search={search} onSearch={setSearch} />
      <div className="space-y-5 mt-4">
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
        <mark className="bg-yellow-500/30 text-yellow-200 rounded px-0.5 not-italic">
          {text.slice(idx, idx + q.length)}
        </mark>
        {text.slice(idx + q.length)}
      </>
    )
  }

  // When searching, force expand
  const isOpen = expanded || !!search.trim()

  return (
    <div>
      {/* Manifest header */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-2 w-full text-left mb-2 group"
      >
        <svg
          width="10" height="10" viewBox="0 0 10 10" fill="currentColor"
          className={`text-gray-500 shrink-0 transition-transform ${isOpen ? 'rotate-90' : ''}`}
        >
          <path d="M3 2l4 3-4 3V2z" />
        </svg>
        <span className="text-xs font-mono font-semibold text-gray-300 group-hover:text-white transition">
          {manifest}
        </span>
        <span className="text-xs text-gray-600 ml-1">
          {search.trim() ? `${filtered.length} / ${deps.length}` : `(${deps.length})`}
        </span>
      </button>

      {isOpen && (
        <>
          {filtered.length === 0 ? (
            <p className="pl-4 text-xs text-gray-600 italic">No matches in this manifest.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5 pl-4">
              {preview.map((dep) => (
                <span
                  key={dep}
                  className="text-xs font-mono px-2 py-0.5 rounded bg-gray-800 border border-gray-700 text-gray-300"
                >
                  <Highlight text={dep} />
                </span>
              ))}
              {!showAll && overflow > 0 && (
                <button
                  onClick={() => setShowAll(true)}
                  className="text-xs px-2 py-0.5 rounded bg-gray-800 border border-gray-700
                             text-blue-400 hover:text-blue-300 hover:border-blue-700/60 transition"
                >
                  +{overflow} more
                </button>
              )}
              {showAll && overflow > 0 && (
                <button
                  onClick={() => setShowAll(false)}
                  className="text-xs px-2 py-0.5 rounded bg-gray-800 border border-gray-700
                             text-gray-500 hover:text-gray-300 transition"
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
      <div className="flex items-center gap-2 mr-auto">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-gray-400 shrink-0">
          <path
            d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"
            stroke="currentColor" strokeWidth="1.5"
          />
        </svg>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Dependencies</p>
        {totalCount > 0 && (
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-gray-800 border border-gray-700 text-gray-500 font-mono">
            {totalCount}
          </span>
        )}
      </div>

      {/* Search input */}
      <div className="relative">
        <svg
          width="13" height="13" viewBox="0 0 24 24" fill="none"
          className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none"
        >
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Filter packages…"
          className="pl-7 pr-3 py-1 text-xs rounded-lg border border-gray-700 bg-gray-800
                     text-gray-200 placeholder-gray-600 outline-none transition
                     focus:border-blue-500 focus:ring-1 focus:ring-blue-500/40 w-36"
        />
        {search && (
          <button
            onClick={() => onSearch('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
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
