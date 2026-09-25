interface Props {
  message?: string
}

export default function LoadingOverlay({ message = 'Analyzing repository…' }: Props) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-5 py-24">
      {/* Animated ring */}
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-4 border-gray-800" />
        <div className="absolute inset-0 rounded-full border-4 border-transparent
                        border-t-blue-500 animate-spin" />
        <div className="absolute inset-2 rounded-full border-4 border-transparent
                        border-t-blue-400/50 animate-spin [animation-duration:1.4s]" />
      </div>
      <div className="text-center">
        <p className="text-base font-medium text-gray-300">{message}</p>
        <p className="text-sm text-gray-500 mt-1">
          Cloning repository, scanning files, building embeddings…
        </p>
      </div>
      {/* Progress hints */}
      <div className="flex flex-col gap-2 mt-2">
        {['Cloning repository', 'Scanning files', 'Detecting languages & frameworks', 'Building search index'].map((step) => (
          <div key={step} className="flex items-center gap-2 text-xs text-gray-500">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            {step}
          </div>
        ))}
      </div>
    </div>
  )
}
