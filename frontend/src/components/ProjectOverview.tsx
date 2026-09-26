import { useState } from 'react'
import type { RepoSummary } from '../types'

interface Props {
  summary: RepoSummary
}

const LANG_COLORS: Record<string, string> = {
  Python:     'bg-blue-500/10 text-blue-300 border-blue-500/30 hover:border-blue-400 hover:bg-blue-500/20 hover:shadow-blue-500/10',
  TypeScript: 'bg-sky-500/10 text-sky-300 border-sky-500/30 hover:border-sky-400 hover:bg-sky-500/20 hover:shadow-sky-500/10',
  JavaScript: 'bg-yellow-500/10 text-yellow-300 border-yellow-500/30 hover:border-yellow-400 hover:bg-yellow-500/20 hover:shadow-yellow-500/10',
  Rust:       'bg-orange-500/10 text-orange-300 border-orange-500/30 hover:border-orange-400 hover:bg-orange-500/20 hover:shadow-orange-500/10',
  Go:         'bg-cyan-500/10 text-cyan-300 border-cyan-500/30 hover:border-cyan-400 hover:bg-cyan-500/20 hover:shadow-cyan-500/10',
  Java:       'bg-red-500/10 text-red-300 border-red-500/30 hover:border-red-400 hover:bg-red-500/20 hover:shadow-red-500/10',
  Markdown:   'bg-gray-800/80 text-gray-300 border-gray-700 hover:border-gray-500 hover:bg-gray-700/80',
  Shell:      'bg-gray-800/80 text-gray-300 border-gray-700 hover:border-gray-500 hover:bg-gray-700/80',
}

function langBadgeClass(lang: string) {
  return LANG_COLORS[lang] ?? 'bg-gray-800/80 text-gray-300 border-gray-700 hover:border-gray-500 hover:bg-gray-700/80'
}

export default function ProjectOverview({ summary }: Props) {
  const ownerRepo = summary.repo_url.replace('https://github.com/', '')
  const [copiedFile, setCopiedFile] = useState<string | null>(null)

  function handleCopyFile(file: string) {
    navigator.clipboard.writeText(file).then(() => {
      setCopiedFile(file)
      setTimeout(() => setCopiedFile(null), 1600)
    }).catch(() => {})
  }

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl shadow-black/30 animate-fade-in relative overflow-hidden group/panel">
      {/* Subtle top ambient gradient line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-blue-500/40 to-transparent" />

      {/* Repo name + link */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <a
            href={summary.repo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xl font-bold text-white hover:text-blue-300 transition-colors font-mono inline-flex items-center gap-2 group/link"
          >
            <span className="group-hover/link:underline decoration-blue-500/50 underline-offset-4">{ownerRepo}</span>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="text-gray-500 group-hover/link:text-blue-300 group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform duration-200">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
          <p className="text-sm text-gray-300/90 mt-1.5 leading-relaxed max-w-2xl">
            {summary.description}
          </p>
        </div>
        <a
          href={summary.repo_url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-gray-400 hover:text-white p-2.5 rounded-xl bg-gray-900/60 border border-white/[0.08] hover:border-white/20 hover:bg-gray-800/80 transition-all duration-200 hover:scale-110 active:scale-95 shadow-sm"
          title="Open on GitHub"
        >
          <GitHubIcon />
        </a>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5 mb-5">
        <StatCard label="Primary Language" value={summary.primary_language} icon="lang" accent="blue" />
        <StatCard label="Frameworks" value={summary.frameworks.join(', ') || '—'} icon="fw" accent="purple" />
        <StatCard label="Files Scanned" value={summary.file_count.toLocaleString()} icon="files" accent="emerald" />
        <StatCard label="Config Files" value={summary.config_files.length.toString()} icon="config" accent="amber" />
      </div>

      {/* Language badges */}
      <div className="mb-5">
        <p className="text-xs text-gray-400 uppercase tracking-wider mb-2.5 font-semibold flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
          Languages detected
        </p>
        <div className="flex flex-wrap gap-2">
          {summary.languages.map((lang) => (
            <span
              key={lang}
              className={`text-xs px-3 py-1 rounded-full border font-medium cursor-default transition-all duration-200 hover:scale-105 hover:shadow-md shadow-xs ${langBadgeClass(lang)}`}
            >
              {lang}
            </span>
          ))}
        </div>
      </div>

      {/* Important files */}
      {summary.important_files.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wider mb-2.5 font-semibold flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
            Key files
          </p>
          <div className="flex flex-wrap gap-2">
            {summary.important_files.map((f) => (
              <button
                key={f}
                onClick={() => handleCopyFile(f)}
                title="Click to copy path"
                className="text-xs font-mono px-3 py-1 rounded-lg bg-gray-900/80 hover:bg-gray-800 text-gray-300 hover:text-white border border-white/[0.08] hover:border-blue-500/40 transition-all duration-200 active:scale-95 flex items-center gap-2 shadow-xs group/btn hover:shadow-[0_0_12px_rgba(59,130,246,0.15)]"
              >
                <span>{f}</span>
                {copiedFile === f ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-emerald-400">
                    <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" className="text-gray-500 opacity-60 group-hover/btn:opacity-100 group-hover/btn:text-blue-300 transition-opacity">
                    <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="2" />
                    <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke="currentColor" strokeWidth="2" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, icon, accent }: { label: string; value: string; icon: string; accent: string }) {
  const accentBorder = {
    blue: 'group-hover:border-blue-500/40',
    purple: 'group-hover:border-purple-500/40',
    emerald: 'group-hover:border-emerald-500/40',
    amber: 'group-hover:border-amber-500/40',
  }[accent] ?? 'group-hover:border-blue-500/40'

  return (
    <div className={`glass-card rounded-xl p-4 cursor-default group transition-all duration-200 ${accentBorder} relative overflow-hidden`}>
      <div className="flex items-center justify-between gap-1 mb-1.5">
        <p className="text-xs text-gray-400 font-medium group-hover:text-gray-300 transition-colors">{label}</p>
        <StatIcon type={icon} />
      </div>
      <p className="text-sm font-semibold text-white truncate group-hover:text-blue-200 transition-colors" title={value}>{value}</p>
    </div>
  )
}

function StatIcon({ type }: { type: string }) {
  if (type === 'lang') {
    return (
      <div className="w-5 h-5 rounded-md bg-blue-500/10 flex items-center justify-center">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-blue-400">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    )
  }
  if (type === 'fw') {
    return (
      <div className="w-5 h-5 rounded-md bg-purple-500/10 flex items-center justify-center">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-purple-400">
          <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2" />
          <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2" />
          <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2" />
          <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2" />
        </svg>
      </div>
    )
  }
  if (type === 'files') {
    return (
      <div className="w-5 h-5 rounded-md bg-emerald-500/10 flex items-center justify-center">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-emerald-400">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    )
  }
  return (
    <div className="w-5 h-5 rounded-md bg-amber-500/10 flex items-center justify-center">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="text-amber-400">
        <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" stroke="currentColor" strokeWidth="2" />
      </svg>
    </div>
  )
}

function GitHubIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483
               0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608
               1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338
               -2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65
               0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337
               1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688
               0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747
               0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}
