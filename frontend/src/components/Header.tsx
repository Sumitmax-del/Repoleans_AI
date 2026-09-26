type BackendStatus = 'checking' | 'ok' | 'error'

interface Props {
  backendStatus: BackendStatus
  backendVersion?: string
}

export default function Header({ backendStatus, backendVersion }: Props) {
  return (
    <header className="border-b border-white/[0.08] bg-gray-950/80 backdrop-blur-xl px-6 py-3.5 flex items-center justify-between shrink-0 z-20 sticky top-0 transition-all duration-200">
      {/* Brand with animated gradient */}
      <div className="flex items-center gap-3.5 group cursor-default">
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 shadow-inner group-hover:scale-105 group-hover:border-blue-400/40 group-hover:bg-blue-500/20 transition-all duration-300">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-blue-400 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)] transition-transform duration-300 group-hover:rotate-6">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
              <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <circle cx="11" cy="11" r="3" fill="currentColor" opacity="0.35" />
            </svg>
          </div>
          <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-blue-100 to-blue-400 bg-clip-text text-transparent transition-all">
            RepoLens
          </span>
        </div>
        <span className="hidden sm:inline text-xs text-gray-500 border-l border-white/[0.08] pl-3.5 select-none font-medium">
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
      <span className="flex items-center gap-2 text-xs text-gray-400 font-mono bg-gray-900/90 border border-white/[0.08] px-3 py-1 rounded-full shadow-sm">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
        Connecting…
      </span>
    )
  }
  if (status === 'error') {
    return (
      <span className="flex items-center gap-2 text-xs font-mono px-3 py-1 rounded-full
                       bg-red-950/60 text-red-300 border border-red-500/30 shadow-sm
                       transition-all duration-200 hover:border-red-500/60 hover:bg-red-950/80">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.8)] animate-pulse" />
        Backend offline
      </span>
    )
  }
  return (
    <span className="flex items-center gap-2 text-xs font-mono px-3 py-1 rounded-full
                     bg-emerald-950/50 text-emerald-300 border border-emerald-500/30 shadow-sm
                     transition-all duration-200 hover:border-emerald-500/60 hover:bg-emerald-950/70 hover:shadow-[0_0_12px_rgba(16,185,129,0.15)]">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
      </span>
      API v{version}
    </span>
  )
}
