import { useState, type FormEvent } from 'react'

interface Props {
  onAnalyze: (url: string) => void
  isLoading: boolean
}

const PLACEHOLDER = 'https://github.com/owner/repository'

export default function RepoInput({ onAnalyze, isLoading }: Props) {
  const [url, setUrl] = useState('')
  const [validationError, setValidationError] = useState('')

  function validate(value: string): string {
    if (!value.trim()) return 'Please enter a GitHub URL.'
    try {
      const parsed = new URL(value.trim())
      if (parsed.hostname !== 'github.com') return 'Only public github.com repositories are supported.'
      const parts = parsed.pathname.replace(/^\//, '').split('/').filter(Boolean)
      if (parts.length < 2) return 'URL must point to a repository, e.g. github.com/owner/repo'
    } catch {
      return 'Enter a valid URL.'
    }
    return ''
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const err = validate(url)
    if (err) { setValidationError(err); return }
    setValidationError('')
    onAnalyze(url.trim())
  }

  return (
    <section className="border-b border-white/[0.08] bg-gray-950/60 backdrop-blur-md px-6 py-5 shrink-0 transition-colors relative z-10">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-xl font-semibold text-white mb-1 tracking-tight flex items-center gap-2">
          <span>Analyze a Repository</span>
          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
            Live RAG
          </span>
        </h1>
        <p className="text-sm text-gray-400 mb-4">
          Paste a public GitHub URL to explore its architecture, dependencies, and code structure.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative group">
            <input
              type="url"
              value={url}
              onChange={(e) => { setUrl(e.target.value); setValidationError('') }}
              disabled={isLoading}
              placeholder={PLACEHOLDER}
              className={[
                'w-full rounded-xl border px-4 py-2.5 text-sm font-mono bg-gray-900/80',
                'text-gray-100 placeholder-gray-500 outline-none transition-all duration-200',
                'focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:bg-gray-900',
                'hover:border-gray-700/80 shadow-inner',
                isLoading ? 'opacity-50 cursor-not-allowed' : '',
                validationError ? 'border-red-500/80 focus:border-red-500 focus:ring-red-500/25' : 'border-white/[0.08]',
              ].join(' ')}
            />
            {url && !isLoading && (
              <button
                type="button"
                onClick={() => { setUrl(''); setValidationError('') }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white p-1 rounded-md hover:bg-gray-800 transition-colors"
                title="Clear input"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </button>
            )}
            {validationError && (
              <p className="mt-1.5 text-xs text-red-400 flex items-center gap-1.5 animate-fade-in-fast">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" className="shrink-0">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                  <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                {validationError}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className={[
              'shrink-0 rounded-xl px-6 py-2.5 text-sm font-semibold transition-all duration-200',
              'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-500 hover:to-indigo-500',
              'active:scale-[0.98] hover:-translate-y-0.5 shadow-lg shadow-blue-600/25 hover:shadow-blue-500/40',
              'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none',
              'flex items-center justify-center gap-2 select-none',
            ].join(' ')}
          >
            {isLoading ? (
              <>
                <Spinner />
                Analyzing…
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="transition-transform group-hover:scale-110">
                  <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
                  <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                Analyze Repository
              </>
            )}
          </button>
        </form>
      </div>
    </section>
  )
}

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4 text-white" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  )
}
