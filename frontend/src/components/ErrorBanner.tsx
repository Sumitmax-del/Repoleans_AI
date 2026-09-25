interface Props {
  title?: string
  message: string
  onRetry?: () => void
}

export default function ErrorBanner({ title = 'Something went wrong', message, onRetry }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center py-16 px-6">
      <div className="max-w-md w-full bg-red-950/40 border border-red-800/60 rounded-xl p-6 text-center">
        <div className="flex justify-center mb-3">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" className="text-red-500">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" />
            <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
        <h3 className="text-base font-semibold text-red-300 mb-1">{title}</h3>
        <p className="text-sm text-red-400/80">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-4 px-5 py-2 rounded-lg bg-red-900/60 border border-red-700/60
                       text-sm text-red-300 hover:bg-red-900 transition"
          >
            Try again
          </button>
        )}
      </div>
    </div>
  )
}
