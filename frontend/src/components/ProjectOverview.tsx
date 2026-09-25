import type { RepoSummary } from '../types'

interface Props {
  summary: RepoSummary
}

const LANG_COLORS: Record<string, string> = {
  Python:     'bg-blue-900/50 text-blue-300 border-blue-700/60',
  TypeScript: 'bg-sky-900/50 text-sky-300 border-sky-700/60',
  JavaScript: 'bg-yellow-900/50 text-yellow-300 border-yellow-700/60',
  Rust:       'bg-orange-900/50 text-orange-300 border-orange-700/60',
  Go:         'bg-cyan-900/50 text-cyan-300 border-cyan-700/60',
  Java:       'bg-red-900/50 text-red-300 border-red-700/60',
  Markdown:   'bg-gray-800 text-gray-400 border-gray-700',
  Shell:      'bg-gray-800 text-gray-400 border-gray-700',
}

function langBadgeClass(lang: string) {
  return LANG_COLORS[lang] ?? 'bg-gray-800 text-gray-400 border-gray-600'
}

export default function ProjectOverview({ summary }: Props) {
  const ownerRepo = summary.repo_url.replace('https://github.com/', '')

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      {/* Repo name + link */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <a
            href={summary.repo_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-lg font-semibold text-white hover:text-blue-400 transition font-mono"
          >
            {ownerRepo}
          </a>
          <p className="text-sm text-gray-400 mt-1 leading-relaxed max-w-xl">
            {summary.description}
          </p>
        </div>
        <a
          href={summary.repo_url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-gray-500 hover:text-gray-300 transition mt-0.5"
          title="Open on GitHub"
        >
          <GitHubIcon />
        </a>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <StatCard label="Primary Language" value={summary.primary_language} />
        <StatCard label="Frameworks" value={summary.frameworks.join(', ') || '—'} />
        <StatCard label="Files Scanned" value={summary.file_count.toLocaleString()} />
        <StatCard label="Config Files" value={summary.config_files.length.toString()} />
      </div>

      {/* Language badges */}
      <div className="mb-4">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Languages detected</p>
        <div className="flex flex-wrap gap-2">
          {summary.languages.map((lang) => (
            <span
              key={lang}
              className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${langBadgeClass(lang)}`}
            >
              {lang}
            </span>
          ))}
        </div>
      </div>

      {/* Important files */}
      {summary.important_files.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Key files</p>
          <div className="flex flex-wrap gap-2">
            {summary.important_files.map((f) => (
              <span key={f} className="text-xs font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800/60 border border-gray-700/50 rounded-lg px-4 py-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-sm font-semibold text-white truncate" title={value}>{value}</p>
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
