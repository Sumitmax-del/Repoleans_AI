interface Props {
  title?: string
  message: string
  onRetry?: () => void
}

export default function ErrorBanner({ title = 'Something went wrong', message, onRetry }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center py-16 px-6 animate-fade-in relative z-10">
      <div className="max-w-md w-full bg-red-950/40 border border-red-500/30 rounded-2xl p-7 text-center shadow-2xl shadow-red-950/40 backdrop-blur-xl relative overflow-hidden">
        {/* Subtle top ambient red line */}
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-red-500/50 to-transparent" />

        <div className="flex justify-center mb-4">
          <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400 shadow-[0_0_20px_rgba(239,68,68,0.2)]">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
              <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
        </div>
        <h3 className="text-base font-bold text-red-200 mb-1.5">{title}</h3>
        <p className="text-sm text-red-300/80 leading-relaxed">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-6 px-6 py-2.5 rounded-xl bg-red-600/80 border border-red-500/50
                       text-sm font-semibold text-white hover:bg-red-500
                       transition-all duration-200 active:scale-95 shadow-lg shadow-red-950/60 hover:-translate-y-0.5"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  )
}
