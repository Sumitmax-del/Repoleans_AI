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
    <section className="border-b border-gray-800 bg-gray-950 px-6 py-5 shrink-0">
      <h1 className="text-xl font-semibold text-white mb-1">Analyze a Repository</h1>
      <p className="text-sm text-gray-400 mb-4">
        Paste a public GitHub URL to explore its architecture, dependencies, and code structure.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <input
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); setValidationError('') }}
            disabled={isLoading}
            placeholder={PLACEHOLDER}
            className={[
              'w-full rounded-lg border px-4 py-2.5 text-sm font-mono bg-gray-900',
              'text-gray-100 placeholder-gray-600 outline-none transition',
              'focus:border-blue-500 focus:ring-1 focus:ring-blue-500/40',
              isLoading ? 'opacity-50 cursor-not-allowed' : '',
              validationError ? 'border-red-500' : 'border-gray-700',
            ].join(' ')}
          />
          {validationError && (
            <p className="mt-1.5 text-xs text-red-400">{validationError}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading || !url.trim()}
          className={[
            'shrink-0 rounded-lg px-6 py-2.5 text-sm font-semibold transition',
            'bg-blue-600 text-white hover:bg-blue-500 active:bg-blue-700',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            'flex items-center gap-2',
          ].join(' ')}
        >
          {isLoading ? (
            <>
              <Spinner />
              Analyzing…
            </>
          ) : (
            'Analyze Repository'
          )}
        </button>
      </form>
    </section>
  )
}

function Spinner() {
  return (
    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  )
}
