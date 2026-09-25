type BackendStatus = 'checking' | 'ok' | 'error'

interface Props {
  backendStatus: BackendStatus
  backendVersion?: string
}

export default function Header({ backendStatus, backendVersion }: Props) {
  return (
    <header className="border-b border-gray-800 bg-gray-950 px-6 py-3 flex items-center justify-between shrink-0 z-10">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          {/* Simple SVG lens icon */}
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-blue-400">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <circle cx="11" cy="11" r="3" fill="currentColor" opacity="0.3" />
          </svg>
          <span className="text-lg font-bold tracking-tight text-white">RepoLens</span>
        </div>
        <span className="hidden sm:inline text-xs text-gray-500 border-l border-gray-700 pl-3">
          AI Repository Understanding
        </span>
      </div>

      {/* Backend status badge */}
      <div className="flex items-center gap-4">
        <BackendBadge status={backendStatus} version={backendVersion} />
      </div>
    </header>
  )
}

function BackendBadge({ status, version }: { status: BackendStatus; version?: string }) {
  if (status === 'checking') {
    return (
      <span className="flex items-center gap-1.5 text-xs text-gray-500 font-mono">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-gray-500 animate-pulse" />
        Connecting…
      </span>
    )
  }
  if (status === 'error') {
    return (
      <span className="flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-full
                       bg-red-950 text-red-400 border border-red-800/60">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500" />
        Backend offline
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-full
                     bg-green-950 text-green-400 border border-green-800/60">
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500" />
      API v{version}
    </span>
  )
}
